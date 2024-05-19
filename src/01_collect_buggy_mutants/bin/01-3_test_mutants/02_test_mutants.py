#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp

# Current working directory
script_path = Path(__file__).resolve()
gen_mutants_dir = script_path.parent
bin_dir = gen_mutants_dir.parent
collect_buggy_mutants_dir = bin_dir.parent

# General directories
src_dir = collect_buggy_mutants_dir.parent
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
clean_build_script = 'clean_build_script.sh'
machines_json_file = 'machines.json'
configure_json_file = 'configurations.json'


crash_codes = [
    132,  # SIGILL
    133,  # SIGTRAP
    134,  # SIGABRT
    136,  # SIGFPE
    137,  # SIGKILL
    138,  # SIGBUS
    139,  # segfault
]


def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.worker)


def start_process(subject_name, worker_name):
    subject_working_dir = collect_buggy_mutants_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    core_working_dir = subject_working_dir / 'workers' / worker_name
    assert core_working_dir.exists(), f"Core working directory {core_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. get test suite: which is a list of tc scripts
    test_suite, tc_dir = get_tc_suite(configs, core_working_dir)

    # 3. get list of mutants
    # mutant_list (tuple): (target_file, mutant_file)
    mutants_list = get_mutants_list(configs, core_working_dir)

    # 4. conduct mutation testing
    test_mutants(configs, core_working_dir, test_suite, tc_dir, mutants_list)

def custome_sort(tc_script):
    tc_filename = tc_script.split('.')[0]
    return int(tc_filename[2:])

def get_tc_suite(configs, core_working_dir):
    tc_dir = core_working_dir / configs['test_case_directory']
    assert tc_dir.exists(), f"Test case directory {tc_dir} does not exist"

    test_suite = []
    for tc_script in tc_dir.iterdir():
        test_suite.append(tc_script.name)
    
    test_suite = sorted(test_suite, key=custome_sort)
    
    return test_suite, tc_dir


def get_mutants_list(configs, core_working_dir):
    generated_mutants_dir = core_working_dir / 'assigned_mutants'

    subj_lang = None
    if configs["subject_language"] == "C":
        subj_lang = "*.c"
    elif configs["subject_language"] == "CPP":
        subj_lang = "*.cpp"
    else:
        raise Exception("Subject language is not supported")

    mutants_list = []
    for target_mutants_dir in generated_mutants_dir.iterdir():
        target_file = target_mutants_dir.name.replace('-', '/')

        target_mutants = list(target_mutants_dir.glob(subj_lang))
        for mutant in target_mutants:
            mutants_list.append((target_file, mutant))

        # print(f"Target file: {target_file}, Mutants: {len(target_mutants)}")
    
    print(f"Total mutants: {len(mutants_list)}")

    return mutants_list


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


def make_patch_file(target_file, mutant, core_working_dir):
    patch_file = core_working_dir / f"mutant.patch"

    target_file = core_working_dir / target_file
    assert target_file.exists(), f"Target file {target_file} does not exist"

    cmd = ['diff', target_file.__str__(), mutant.__str__()]
    sp.run(cmd, stdout=patch_file.open('w'))
    
    return patch_file

def apply_patch(target_file, mutant, patch_file, core_working_dir, revert=False):
    target_file = core_working_dir / target_file
    assert target_file.exists(), f"Target file {target_file} does not exist"

    cmd = ['patch']
    if revert:
        cmd.append('-R')
    cmd.extend(['-i', patch_file.__str__(), target_file.__str__()])

    res = sp.run(cmd, stdout=sp.PIPE, stderr=sp.PIPE)
    if res.returncode != 0:
        raise Exception(f'Failed to apply patch to {target_file.name} with mutant {mutant.name}')
    
    print(f'Applied patch to {target_file.name} with mutant {mutant.name} : revert={revert}')


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

    try:
        res = sp.run(cmd, shell=True, cwd=tc_dir, stdout=sp.PIPE, stderr=sp.PIPE, timeout=1)
    except sp.TimeoutExpired:
        print(f"Testcase {tc_script} timeout")
        return -1

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
    return parser

if __name__ == "__main__":
    main()