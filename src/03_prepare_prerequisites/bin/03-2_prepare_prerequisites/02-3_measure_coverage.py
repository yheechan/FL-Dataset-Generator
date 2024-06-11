#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import os

# Current working directory
script_path = Path(__file__).resolve()
prepare_prerequisites_cmd_dir = script_path.parent
bin_dir = prepare_prerequisites_cmd_dir.parent
prepare_prerequisites_dir = bin_dir.parent

# General directories
src_dir = prepare_prerequisites_dir.parent
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

my_env = os.environ.copy()

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.worker, args.version, args.use_excluded_failing_tcs)


def start_process(subject_name, worker_name, version_name, use_excluded_failing_tcs):
    subject_working_dir = prepare_prerequisites_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    core_working_dir = subject_working_dir / 'workers_preparing_prerequisites' / worker_name
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

    if use_excluded_failing_tcs:
        print("Using excluded failing test cases")
        move_excluded_failing_tcs2_failing_tcs(version_dir)

    # 3. get failing tc list (ex, TC1.sh, TC2.sh, ...)
    failing_tc_list = get_tcs(version_dir, 'failing_tcs.txt')
    print(f"Total failing test cases: {len(failing_tc_list)}")
    passing_tc_list = get_tcs(version_dir, 'passing_tcs.txt')
    print(f"Total passing test cases: {len(passing_tc_list)}")

    # 4. get buggy code file
    buggy_code_file = get_buggy_code_file(version_dir, buggy_code_filename)
    # print(f"Buggy code file: {buggy_code_file.name}")


    # 5. conduct run tests on buggy version with failing test cases
    measure_coverage(
        configs, core_working_dir, version_name, 
        target_code_file_path, buggy_code_file, 
        buggy_lineno, failing_tc_list, passing_tc_list, version_dir
    )

def move_excluded_failing_tcs2_failing_tcs(version_dir):
    excluded_failing_tcs_file = version_dir / 'testsuite_info/excluded_failing_tcs.txt'
    assert excluded_failing_tcs_file.exists(), f"Excluded failing test cases file {excluded_failing_tcs_file} does not exist"

    failing_tcs_file = version_dir / 'testsuite_info/failing_tcs.txt'
    assert failing_tcs_file.exists(), f"Failing test cases file {failing_tcs_file} does not exist"

    with open(excluded_failing_tcs_file, 'r') as f:
        excluded_tcs = f.readlines()
        excluded_tcs = [tc.strip() for tc in excluded_tcs]

    with open(failing_tcs_file, 'r') as f:
        failing_tcs = f.readlines()
        failing_tcs = [tc.strip() for tc in failing_tcs]
    
    excluded_tcs_set = set(excluded_tcs)
    failing_tcs_set = set(failing_tcs)
    all_failing_tcs = excluded_tcs_set.union(failing_tcs_set)
    with open(failing_tcs_file, 'w') as f:
        content = '\n'.join(all_failing_tcs)
        f.write(content)
    
    with open(excluded_failing_tcs_file, 'w') as f:
        f.write('')

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

def get_tcs(version_dir, tc_file):
    testsuite_info_dir = version_dir / 'testsuite_info'
    assert testsuite_info_dir.exists(), f"Testsuite info directory {testsuite_info_dir} does not exist"

    tc_file_txt = testsuite_info_dir / tc_file
    assert tc_file_txt.exists(), f"Failing test cases file {tc_file_txt} does not exist"

    tcs_list = []

    with open(tc_file_txt, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            tcs_list.append(line)
        
    tcs_list = sorted(tcs_list, key=custome_sort)

    return tcs_list




def measure_coverage(
        configs, core_working_dir, version_name, 
        target_code_file_path, buggy_code_file, 
        buggy_lineno, failing_tc_list, passing_tc_list, version_dir):
    global my_env

    # --- prepare needed directories
    exclude_cct = configs['exclude_cct']

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

    # prepare filter files for coverage
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
    
    # my_env["PATH"] = f"/usr/sbin:/sbin:{my_env['PATH']}

    if configs['environment_setting']['needed'] == True:
        for key, value in configs['environment_setting']['variables'].items():
            path = core_working_dir / value
            assert path.exists(), f"Path {path} does not exist"
            path_str = path.__str__()

            if key not in my_env:
                my_env[key] = path_str
            else:
                my_env[key] = f"{path_str}:{my_env[key]}"
            # print(path_str)



    # --- test the buggy version
    # 1. Make patch file
    patch_file = make_patch_file(target_code_file_path, buggy_code_file, core_working_dir)

    # 2. Apply patch
    apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, False)

    # THIS STEP IS NEEDED OR ELSE COVERAGE IS NOT MEASURED PROPERLY... (I THINK)
    # remove_all_gcda_gcno(subject_dir)

    # 3. Build the subject, if build fails, skip the mutant
    res = execute_build_script(configs[build_sh_wd_key], core_working_dir)
    if res != 0:
        print('Failed to build on {}'.format(version_name))
        apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, True)
        exit(1)
    
    cct_list = []

    # 4. run the test suite
    for tc_name in failing_tc_list+passing_tc_list:

        # 4-1. remove past coverage
        remove_all_gcda(subject_dir)

        # 4-2. run the test case
        res = run_tc(tc_name, tc_dir)
        # if res == 0:
        #     print(f"Testcase {tc_name} passed print myenv")
        #     apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, True)
        #     exit(1)
        
        # 4-3. remove untargeted files for coverage
        remove_untargeted_files_for_coverage(target_gcno_gcda, subject_dir)

        # 4-4. generate coverage json
        raw_cov = generate_coverage_json(
            gcovr, version_cov_dir, tc_name,
            filtered_files, subject_dir
        )

        # 4-5. Check if the buggy line is covered & if exclude_cct is True, exclude cct from passing tcs
        if tc_name in failing_tc_list:
            buggy_line_cov = check_buggy_line_coverage(raw_cov, target_code_file_path, buggy_lineno)
            if buggy_line_cov == 1:
                print(f"Buggy line {buggy_lineno} is not covered by {tc_name}")
                # apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, True)
                # exit(1)
            if buggy_line_cov == -2:
                print(f"Failed to check coverage for {tc_name}")
                # apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, True)
                # exit(1)
            
            print(f"Testcase {tc_name} executed buggy line {buggy_lineno}")
        elif tc_name in passing_tc_list and exclude_cct == True:
            buggy_line_cov = check_buggy_line_coverage(raw_cov, target_code_file_path, buggy_lineno)
            # value of buggy_line_cov is 0 if the buggy line is covered
            # value of buggy_line_cov is 1 if the buggy line is not covered
            if buggy_line_cov == 0:
                cct_list.append(tc_name)
                # delete raw_cov file
                os.remove(raw_cov)
    
    # 5. Apply patch reverse
    apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, True)

    if len(cct_list) > 0:
        # remove cct test cases from passing test cases
        passing_tc_list = [tc for tc in passing_tc_list if tc not in cct_list]
        # update passing test cases
        passing_tc_list_file = version_dir / 'testsuite_info/passing_tcs.txt'
        with open(passing_tc_list_file, 'w') as f:
            content = '\n'.join(passing_tc_list)
            f.write(content)
        
    # update cct test cases
    cct_list_file = version_dir / 'testsuite_info/ccts.txt'
    with open(cct_list_file, 'w') as f:
        content = '\n'.join(cct_list)
        f.write(content)


# returns 0 if the buggy line is covered
# returns 1 if the buggy line is not covered
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
    global my_env

    cmd = f"./{tc_script}"
    res = sp.run(cmd, shell=True, cwd=tc_dir, stdout=sp.PIPE, stderr=sp.PIPE, env=my_env) #, timeout=1)
    # if res.returncode != 0:
    #     print(f"Testcase {tc_script} failed")
    #     print(f"cmd: {cmd}")
    #     print(f"stdout: {res.stdout}")
    #     print(f"stderr: {res.stderr}")
    #     print(f"returncode: {res.returncode}")

    # print(f"tc_script: {tc_script}, returncode: {res.returncode}")
    return res.returncode


def make_patch_file(target_code_file_path, buggy_code_file, core_working_dir):
    patch_file = core_working_dir / f"buggy_version.patch"

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
        raise Exception(f'Failed to apply patch to {target_file.name} with buggy version {buggy_code_file.name}')
    
    print(f'Applied patch to {target_file.name} with buggy version {buggy_code_file.name} : revert={revert}')



def execute_build_script(build_sh_wd, core_working_dir):
    global build_script

    build_sh_wd = core_working_dir / build_sh_wd
    build_sh = build_sh_wd / build_script
    assert build_sh.exists(), f"Build script {build_sh} does not exist"

    cmd = ['bash', build_script]
    res = sp.run(cmd, cwd=build_sh_wd, stdout=sp.PIPE, stderr=sp.PIPE)

    print(f"Build script executed: {res.returncode}")
    
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
    parser.add_argument('--use-excluded-failing-tcs', action='store_true', help='Use excluded failing test cases')
    return parser

if __name__ == "__main__":
    main()
    exit(0)
