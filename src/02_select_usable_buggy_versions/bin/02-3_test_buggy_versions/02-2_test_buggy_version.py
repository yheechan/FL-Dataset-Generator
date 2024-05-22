#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp

# Current working directory
script_path = Path(__file__).resolve()
test_buggy_versions_dir = script_path.parent
bin_dir = test_buggy_versions_dir.parent
select_usable_buggy_versions = bin_dir.parent

# General directories
src_dir = select_usable_buggy_versions.parent
root_dir = src_dir.parent
user_configs_dir = root_dir / 'user_configs'
subjects_dir = root_dir / 'subjects'
external_tools_dir = root_dir / 'external_tools'

# keywords in configurations.json
config_sh_wd_key = 'configure_script_working_directory'
build_sh_wd_key = 'build_script_working_directory'

# files in user_configs_dir
configure_no_cov_script = 'configure_no_cov_script.sh'
configure_yes_cov_script = 'configure_yes_cov_script.sh'
build_script = 'build_script.sh'
clean_script = 'clean_script.sh'
machines_json_file = 'machines.json'
configure_json_file = 'configurations.json'
real_world_buggy_versions = 'real_world_buggy_versions'


crash_codes = [
    132,  # SIGILL
    133,  # SIGTRAP
    134,  # SIGABRT
    135,  # SIGBUS
    136,  # SIGFPE
    137,  # SIGKILL
    138,  # SIGBUS
    139,  # segfault
    140,  # SIGPIPE
    141,  # SIGALRM
    124,  # timeout
    143,  # SIGTERM
    129,  # SIGHUP
]


def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.worker, args.version)


def start_process(subject_name, worker_name, version_name):
    subject_working_dir = select_usable_buggy_versions / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    core_working_dir = subject_working_dir / 'workers_selecting_buggy_versions' / worker_name
    assert core_working_dir.exists(), f"Core working directory {core_working_dir} does not exist"

    assigned_buggy_versions_dir = core_working_dir / 'assigned_buggy_versions'
    assert assigned_buggy_versions_dir.exists(), f"Assigned buggy versions directory {assigned_buggy_versions_dir} does not exist"

    version_dir = assigned_buggy_versions_dir / version_name
    assert version_dir.exists(), f"Version directory {version_dir} does not exist"


    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)


    # 2. get bug_info
    target_code_file_path, buggy_code_filename, buggy_lineno = get_bug_info(version_dir)
    # print(f"Target code file: {target_code_file_path}")
    # print(f"Buggy code filename: {buggy_code_filename}")
    # print(f"Buggy line number: {buggy_lineno}")
    assert version_name == buggy_code_filename, f"Version name {version_name} does not match with buggy code filename {buggy_code_filename}"

    # 3. get failing tc list (ex, TC1, TC2, ...)
    failing_tc_list = get_failing_suite(version_dir)
    print(f"Total failing test cases: {len(failing_tc_list)}")

    # 4. get buggy code file
    buggy_code_file = get_buggy_code_file(version_dir, buggy_code_filename)
    # print(f"Buggy code file: {buggy_code_file.name}")


    # 5. conduct run tests on buggy version with failing test cases
    test_buggy_version(
        configs, core_working_dir, version_name, 
        target_code_file_path, buggy_code_file, 
        buggy_lineno, failing_tc_list, version_dir
    )

def get_bug_info(version_dir):
    bug_info_csv = version_dir / 'bug_info.csv'
    assert bug_info_csv.exists(), f"Bug info csv file {bug_info_csv} does not exist"

    with open(bug_info_csv, 'r') as f:
        lines = f.readlines()
        target_code_file, buggy_code_filename, buggy_lineno = lines[1].strip().split(',')
        return target_code_file, buggy_code_filename, buggy_lineno


def get_buggy_code_file(version_dir, buggy_code_filename):
    buggy_code_file_dir = version_dir / 'buggy_code_file'
    assert buggy_code_file_dir.exists(), f"Buggy code file directory {buggy_code_file_dir} does not exist"

    buggy_code_file = buggy_code_file_dir / buggy_code_filename
    assert buggy_code_file.exists(), f"Buggy code file {buggy_code_file} does not exist"

    return buggy_code_file


def custome_sort(tc_script):
    tc_filename = tc_script.split('.')[0]
    return int(tc_filename[2:])

def get_failing_suite(version_dir):
    testsuite_info_dir = version_dir / 'testsuite_info'
    assert testsuite_info_dir.exists(), f"Testsuite info directory {testsuite_info_dir} does not exist"

    failing_tcs_file = testsuite_info_dir / 'failing_tcs.txt'
    assert failing_tcs_file.exists(), f"Failing test cases file {failing_tcs_file} does not exist"

    failing_tcs_list = []

    with open(failing_tcs_file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            failing_tcs_list.append(line)
        
    failing_tcs_list = sorted(failing_tcs_list, key=custome_sort)

    return failing_tcs_list




def test_buggy_version(
        configs, core_working_dir, version_name, 
        target_code_file_path, buggy_code_file, 
        buggy_lineno, failing_tc_list, version_dir):
    
    # --- prepare needed directories
    # gcov executable
    home_directory = configs['home_directory']
    gcovr = Path(home_directory) / '.local/bin/gcovr'
    

    # path to the test case directory
    tc_dir_pathname = configs['test_case_directory']
    tc_dir = core_working_dir / tc_dir_pathname
    assert tc_dir.exists(), f"Test case directory {tc_dir} does not exist"

    # path to the subject directory
    subject_dir = core_working_dir / configs['subject_name']
    assert subject_dir.exists(), f"Subject directory {subject_dir} does not exist"

    # path to coverage directory
    cov_dir = core_working_dir / 'coverage'
    if not cov_dir.exists():
        cov_dir.mkdir()
    
    # version_cov_dir
    version_cov_dir = cov_dir / version_name
    if not version_cov_dir.exists():
        version_cov_dir.mkdir()

    # filter files for coverage
    targeted_files = configs['target_files']
    targeted_files = [file.split('/')[-1] for file in targeted_files]
    filtered_files = '|'.join(targeted_files)

    target_gcno_gcda = []
    for target_file in targeted_files:
        filename = target_file.split('.')[0]
        gcno_file = '*'+filename+'.gcno'
        gcda_file = '*'+filename+'.gcda'
        target_gcno_gcda.append(gcno_file)
        target_gcno_gcda.append(gcda_file)

    # --- test the buggy version
    # 1. Make patch file
    patch_file = make_patch_file(target_code_file_path, buggy_code_file, core_working_dir)

    # 2. Apply patch
    apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, False)

    # 3. Build the subject, if build fails, skip the mutant
    res = execute_build_script(configs[build_sh_wd_key], core_working_dir)
    if res != 0:
        print('Failed to build on {}'.format(version_name))
        apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, True)
        exit(1)

    # 4. run the test suite
    for tc_name in failing_tc_list:

        # 4-1. remove past coverage
        remove_all_gcda(subject_dir)

        # 4-2. run the test case
        res = run_tc(tc_name, tc_dir)
        if res == 0:
            print(f"Testcase {tc_name} passed")
            apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, True)
            exit(1)
        
        # 4-3. remove untargeted files for coverage
        remove_untargeted_files_for_coverage(target_gcno_gcda, subject_dir)

        # 4-4. generate coverage json
        raw_cov = generate_coverage_json(
            gcovr, version_cov_dir, tc_name,
            filtered_files, subject_dir
        )

        # 4-5. Check if the buggy line is covered
        buggy_line_cov = check_buggy_line_coverage(raw_cov, target_code_file_path, buggy_lineno)
        if buggy_line_cov == 1:
            print(f"Buggy line {buggy_lineno} is not covered by {tc_name}")
            apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, True)
            exit(1)
        if buggy_line_cov == -2:
            print(f"Failed to check coverage for {tc_name}")
            apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, True)
            exit(1)
        
        print(f"Testcase {tc_name} executed buggy line {buggy_lineno}")
    
    # 5. Apply patch reverse
    apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, True)

    # 6. Save the buggy version
    save_buggy_version(version_dir, core_working_dir)

def save_buggy_version(version_dir, core_working_dir):
    usable_buggy_versions_dir = core_working_dir / 'usable_buggy_versions'
    assert usable_buggy_versions_dir.exists(), f"Usable buggy versions directory {usable_buggy_versions_dir} does not exist"

    # copy version directory to usable_buggy_versions
    cmd = ['cp', '-r', version_dir, usable_buggy_versions_dir]
    res = sp.run(cmd)
    if res.returncode != 0:
        print(f"Failed to save buggy version {version_dir}")
        exit(1)

    print(f"Saved buggy version {version_dir.name}")

def check_buggy_line_coverage(raw_cov, target_code_file, buggy_lineno):
    with open(raw_cov, 'r') as f:
        cov_data = json.load(f)

    target_file = target_code_file.split('/')[-1]
    # target_file = target_file.split('.')[0]

    filename_list = [file['file'] for file in cov_data['files']]

    # WARNING: THE FILENAME MAY BE DIFFERENT ON OTHER SUBJECTS
    if target_file not in filename_list:
        return -2


    for file in cov_data['files']:
        if file['file'] == target_file:
            lines = file['lines']
            for line in lines:
                if line['line_number'] == int(buggy_lineno):
                    print(f"Line: {line['line_number']}, count: {line['count']}")
                    if line['count'] > 0:
                        return 0
                    else:
                        return 1
            return 1
    return 1

def generate_coverage_json(gcovr, version_cov_dir, tc_id, filtered_files, subject_dir):

    tc_name = tc_id.split('.')[0]
    file_name = tc_name + '.raw.json'
    file_path = version_cov_dir / file_name
    file_path = file_path.resolve()
    cmd = [
        gcovr,
        '--filter', filtered_files,
        '--gcov-executable', 'llvm-cov gcov',
        '--json',
        # '--json-pretty',
        '-o', file_path
    ]
    # print(cmd)
    res = sp.call(cmd, cwd=subject_dir)
    return file_path


def remove_untargeted_files_for_coverage(target_gcno_gcda, subject_dir):
    # remove all files that are *.gcno and *.gcda
    # except <target_files>.gcno <target_files>.gcda files
    cmd = ['find', '.', '-type', 'f', '(', '-name', '*.gcno', '-o', '-name', '*.gcda', ')']
             
    for target_file in target_gcno_gcda:
        cmd.extend(['!', '-name', target_file])
    cmd.extend(['-delete'])

    # print(cmd)
    res = sp.call(cmd, cwd=subject_dir)

def remove_all_gcda(subject_dir):
    cmd = [
        'find', '.', '-type',
        'f', '-name', '*.gcda',
        '-delete'
    ]
    res = sp.call(cmd, cwd=subject_dir)


def run_tc(tc_script, tc_dir):
    cmd = f"./{tc_script}"

    res = sp.run(cmd, shell=True, cwd=tc_dir, stdout=sp.PIPE, stderr=sp.PIPE) #, timeout=1)

    # if res.returncode != 0:
    #     print(f"Testcase {tc_script} failed")
    #     print(f"cmd: {cmd}")
    #     print(f"stdout: {res.stdout}")
    #     print(f"stderr: {res.stderr}")
    #     print(f"returncode: {res.returncode}")

    # print(f"tc_script: {tc_script}, returncode: {res.returncode}")
    return res.returncode


def test_mutants(configs, core_working_dir, test_suite, tc_dir, mutants_list):

    for target_file, mutant in mutants_list:
        
        # 1. Make patch file
        patch_file = make_patch_file(target_file, mutant, core_working_dir)

        # 2. Apply patch
        apply_patch(target_file, mutant, patch_file, core_working_dir, False)

        # 3. Build the subject, if build fails, skip the mutant
        res = execute_build_script(configs[build_sh_wd_key], core_working_dir)
        if res != 0:
            print('Failed to build on {}'.format(mutant.name))
            apply_patch(target_file, mutant, patch_file, core_working_dir, True)
            continue

        # 4. run the test suite
        passing_tcs, failing_tcs = run_test_suite(test_suite, tc_dir)
        if passing_tcs == [-1] and failing_tcs == [-1]:
            print('Crash detected on {}'.format(mutant.name))
            apply_patch(target_file, mutant, patch_file, core_working_dir, True)
            continue

        # 5. Don't save the mutant if all test cases pass
        if len(failing_tcs) == 0:
            print(f"Mutant {mutant.name} is not killed")
            apply_patch(target_file, mutant, patch_file, core_working_dir, True)
            continue

        # 6. Save the mutant if any test case fails
        save_buggy_mutant(target_file, mutant, passing_tcs, failing_tcs, core_working_dir)

        # X. Apply patch reverse
        apply_patch(target_file, mutant, patch_file, core_working_dir, True)


def make_patch_file(target_code_file_path, buggy_code_file, core_working_dir):
    patch_file = core_working_dir / f"mutant.patch"

    target_file = core_working_dir / target_code_file_path
    assert target_file.exists(), f"Target file {target_file} does not exist"

    cmd = ['diff', target_file.__str__(), buggy_code_file.__str__()]
    sp.run(cmd, stdout=patch_file.open('w'))
    
    return patch_file

def apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, revert=False):
    target_file = core_working_dir / target_code_file_path
    assert target_file.exists(), f"Target file {target_file} does not exist"

    cmd = ['patch']
    if revert:
        cmd.append('-R')
    cmd.extend(['-i', patch_file.__str__(), target_file.__str__()])

    res = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    if res.returncode != 0:
        raise Exception(f'Failed to apply patch to {target_file.name} with mutant {buggy_code_file.name}')
    
    print(f'Applied patch to {target_file.name} with mutant {buggy_code_file.name} : revert={revert}')


def run_test_suite(test_suite, tc_dir):
    passing_tcs = []
    failing_tcs = []

    for tc_script in test_suite:
        res = run_tc(tc_script, tc_dir)
        if res in crash_codes:
            return [-1], [-1]
        elif res == 0:
            passing_tcs.append(tc_script)
        else:
            failing_tcs.append(tc_script)
    
    print(f'Passing: {len(passing_tcs)}, Failing: {len(failing_tcs)}')
    return passing_tcs, failing_tcs

def run_tc(tc_script, tc_dir):
    cmd = f"./{tc_script}"

    res = sp.run(cmd, shell=True, cwd=tc_dir, stdout=sp.PIPE, stderr=sp.PIPE) #, timeout=1)

    # if res.returncode != 0:
    #     print(f"Testcase {tc_script} failed")
    #     print(f"cmd: {cmd}")
    #     print(f"stdout: {res.stdout}")
    #     print(f"stderr: {res.stderr}")
    #     print(f"returncode: {res.returncode}")

    # print(f"tc_script: {tc_script}, returncode: {res.returncode}")
    return res.returncode

def save_buggy_mutant(target_file, mutant, passing_tcs, failing_tcs, core_working_dir):
    buggy_mutant_dir = core_working_dir / 'buggy_mutants'
    assert buggy_mutant_dir.exists(), f"Buggy mutants directory {buggy_mutant_dir} does not exist"

    # save the mutant
    mutant_dir = buggy_mutant_dir / mutant.name
    assert not mutant_dir.exists(), f"Mutant directory {mutant_dir} already exists"
    mutant_dir.mkdir(exist_ok=True)

    # save the failing tcs
    failing_tcs_file = mutant_dir / 'failing_tcs.txt'
    failing_tcs_file.write_text('\n'.join(failing_tcs))

    # save the passing tcs
    passing_tcs_file = mutant_dir / 'passing_tcs.txt'
    passing_tcs_file.write_text('\n'.join(passing_tcs))

    # save the string of targetfile and mutant name as csv
    csv_file = mutant_dir / 'bug_info.csv'
    csv_file.write_text(f"target_code_file,mutant_code_file\n{target_file},{mutant.name}")

    print(f"Mutant {mutant.name} is saved")


def execute_build_script(build_sh_wd, core_working_dir):
    global build_script

    build_sh_wd = core_working_dir / build_sh_wd
    build_sh = build_sh_wd / build_script
    assert build_sh.exists(), f"Build script {build_sh} does not exist"

    cmd = ['bash', build_script]
    res = sp.run(cmd, cwd=build_sh_wd, stdout=sp.PIPE, stderr=sp.PIPE)
    
    return res.returncode



def read_configs(subject_name, subject_working_dir):
    global configure_json_file

    subject_config_dir = subject_working_dir / f"{subject_name}-configures"
    assert subject_config_dir.exists(), f"Subject configurations directory {subject_config_dir} does not exist"

    config_json = subject_config_dir / configure_json_file
    assert config_json.exists(), f"Configurations file {config_json} does not exist"
    
    configs = None
    with config_json.open() as f:
        configs = json.load(f)
    
    if configs is None:
        raise Exception('Configurations are not loaded')
    
    return configs

def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    parser.add_argument('--worker', type=str, help='Worker name (e.g., <machine-name>/<core-id>)', required=True)
    parser.add_argument('--version', type=str, help='Version name', required=True)
    return parser

if __name__ == "__main__":
    main()
    exit(0)
