#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import os

# Current working directory
script_path = Path(__file__).resolve()
mbfl_feature_extraction_dir = script_path.parent
bin_dir = mbfl_feature_extraction_dir.parent
extract_mbfl_features_cmd_dir = bin_dir.parent

# General directories
src_dir = extract_mbfl_features_cmd_dir.parent
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
    start_process(args.subject, args.worker, args.version)


def start_process(subject_name, worker_name, version_name):
    subject_working_dir = extract_mbfl_features_cmd_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    core_working_dir = subject_working_dir / 'workers_extracting_mbfl_features' / worker_name
    assert core_working_dir.exists(), f"Core working directory {core_working_dir} does not exist"

    assigned_buggy_versions_dir = core_working_dir / 'assigned_buggy_versions'
    assert assigned_buggy_versions_dir.exists(), f"Assigned buggy versions directory {assigned_buggy_versions_dir} does not exist"

    version_dir = assigned_buggy_versions_dir / version_name
    assert version_dir.exists(), f"Version directory {version_dir} does not exist"

    print(f"<<<<<< MBFL on {subject_name} with {worker_name} for {version_name} >>>>>>")

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. get bug_info
    target_code_file_path, buggy_code_filename, buggy_lineno = get_bug_info(version_dir)
    # print(f"Target code file: {target_code_file_path}")
    # print(f"Buggy code filename: {buggy_code_filename}")
    # print(f"Buggy line number: {buggy_lineno}")
    assert version_name == buggy_code_filename, f"Version name {version_name} does not match with buggy code filename {buggy_code_filename}"


    # 3. read the selected mutants
    # selected_mutants
    # key: target_filename (ex. parser.c)
    # value: lineno (dict) -> list of mutants (ex. 123)
    # list of mutants: mutant_id, mutant_name (ex. mutant_12, parser.MUT123.c)
    selected_mutants = get_selected_mutants(version_dir)
    for target_file, lineno_mutants in selected_mutants.items():
        mutant_cnt = 0
        for lineno, mutants in lineno_mutants.items():
            mutant_cnt += len(mutants)
        print(f"Selected mutants for {target_file}: {mutant_cnt}")

    # 4. get passing and failing test cases (ex. TC1.sh, TC2.sh ...)
    failing_tc_list = get_tcs(version_dir, 'failing_tcs.txt')
    passing_tc_list = get_tcs(version_dir, 'passing_tcs.txt')
    testsuite = {
        'failing': failing_tc_list,
        'passing': passing_tc_list
    }
    for key, tcs in testsuite.items():
        print(f"{key} test cases: {len(tcs)}")

    # 5. Initiate version results csv file
    # result_csv = core_working_dir / 'mutant_data' / version_name / 'mutation_testing_results.csv'
    # result_csv_file = result_csv.open('w')
    # result_csv_file.write("target_file,mutant_id,lineno,build_result,p2f,p2p,f2p,f2f\n")
    result_csv = version_dir / 'mutation_testing_results.csv'
    result_csv_file = result_csv.open('w')
    result_csv_file.write("target_file,mutant_id,lineno,build_result,p2f,p2p,f2p,f2f\n")


    # 6. apply buggy version code
    buggy_code_file = get_buggy_code_file(version_dir, buggy_code_filename)
    buggy_patch = make_patch_file(target_code_file_path, buggy_code_file, core_working_dir, 'buggy.patch')
    apply_patch(target_code_file_path, buggy_code_file, buggy_patch, core_working_dir, revert=False)


    # 7. Conduct mutation testing
    conduct_mutation_testing(
        configs, core_working_dir, subject_name,
        version_name, selected_mutants, testsuite,
        result_csv_file
    )

    # 8. Revert the buggy version code
    apply_patch(target_code_file_path, buggy_code_file, buggy_patch, core_working_dir, revert=True)

    # 9. Close the result csv file
    result_csv_file.close()

def get_buggy_code_file(version_dir, buggy_code_filename):
    buggy_code_file_dir = version_dir / 'buggy_code_file'
    assert buggy_code_file_dir.exists(), f"Buggy code file directory {buggy_code_file_dir} does not exist"

    buggy_code_file = buggy_code_file_dir / buggy_code_filename
    assert buggy_code_file.exists(), f"Buggy code file {buggy_code_file} does not exist"

    return buggy_code_file

def conduct_mutation_testing(
    configs, core_working_dir, subject_name,
    version_name, selected_mutants, testsuite,
    result_csv_file
):
    # --- prepare needs
    global my_env
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
    
    version_gen_mutants_dir = core_working_dir / 'generated_mutants' / version_name

    tc_dir = core_working_dir / configs['test_case_directory']
    assert tc_dir.exists(), f"Test case directory {tc_dir} does not exist"
    
    # --- start testing
    # FOR A TARGET FILE...
    for target_file, lineno_mutants in selected_mutants.items():
        target_file_path = get_target_file_path(configs['target_files'], target_file)
        assert target_file_path is not None, f"Target file {target_file} does not exist in target files"

        # FOR A LINE OF TARGET FILE...
        for lineno, mutants in lineno_mutants.items():

            # TEST EACH MUTANT
            for mutant in mutants:
                mutant_id = mutant['mutant_id']
                mutant_name = mutant['mutant_name']

                mutant_file = version_gen_mutants_dir / f"{subject_name}-{target_file}" / mutant_name
                assert mutant_file.exists(), f"Mutant file {mutant_file} does not exist"

                # print(f"Testing mutant {mutant_id} ({mutant_name}) in {target_file} at line {lineno}")
                start_test(
                    configs, core_working_dir, subject_name,
                    version_name, target_file_path, target_file, mutant_file,
                    lineno, mutant_id, mutant_name,
                    testsuite, result_csv_file, tc_dir
                )


def start_test(
    configs, core_working_dir, subject_name,
    version_name, target_file_path, target_file, mutant_file,
    lineno, mutant_id, mutant_name,
    testsuite, result_csv_file, tc_dir
):
    tc_outcome = {'p2f': -1, 'p2p': -1, 'f2p': -1, 'f2f': -1}
    build_result = False
    # 1. Make patch file of the mutant
    mutant_patch = make_patch_file(target_file_path, mutant_file, core_working_dir, 'mutant.patch')

    # 2. Apply patch to the target file
    apply_patch(target_file_path, mutant_file, mutant_patch, core_working_dir)

    # 3. Build the subject, if build fails, skip the mutant
    build_res = execute_build_script(configs[build_sh_wd_key], core_working_dir)
    if build_res != 0:
        print(f"Failed to build the subject with mutant {mutant_id} ({mutant_name})")
        apply_patch(target_file_path, mutant_file, mutant_patch, core_working_dir, revert=True)
        write_results(result_csv_file, target_file, mutant_id, lineno, build_result, tc_outcome)
        return
    
    # --> build is successful
    build_result = True
    tc_outcome = {'p2f': 0, 'p2p': 0, 'f2p': 0, 'f2f': 0}

    # 4. Run the test suite
    print(f"running test suite for mutant {mutant_id} ({mutant_name})")
    run_test_suite(testsuite, core_working_dir, mutant_id, tc_outcome, tc_dir)

    # 5. Apply path to the target file (revert)
    apply_patch(target_file_path, mutant_file, mutant_patch, core_working_dir, revert=True)
    
    # 6. Write the results to the csv file
    write_results(result_csv_file, target_file, mutant_id, lineno, build_result, tc_outcome)

def run_test_suite(testsuite, core_working_dir, mutant_id, tc_outcome, tc_dir):
    mutant_passing_tcs = []
    mutant_failing_tcs = []

    for tc_type in testsuite:
        # tc_type: 'failing' or 'passing'
        for tc_script_name in testsuite[tc_type]:
            res = run_tc(tc_script_name, tc_dir)
            if res == 0:
                mutant_passing_tcs.append(tc_script_name)
                if tc_type == 'failing':
                    tc_outcome['f2p'] += 1
                elif tc_type == 'passing':
                    tc_outcome['p2p'] += 1
            else:
                mutant_failing_tcs.append(tc_script_name)
                if tc_type == 'failing':
                    tc_outcome['f2f'] += 1
                elif tc_type == 'passing':
                    tc_outcome['p2f'] += 1
    
    # print("Passing test cases:")
    # for tc in mutant_passing_tcs:
    #     print(f"{tc}")
    # print("Failing test cases:")
    # for tc in mutant_failing_tcs:
    #     print(f"{tc}")
            

def run_tc(tc_script_name, tc_dir):
    global my_env
    
    cmd = f"./{tc_script_name}"
    res = sp.run(cmd, shell=True, cwd=tc_dir, env=my_env, stdout=sp.PIPE, stderr=sp.PIPE)
    return res.returncode


def write_results(result_csv_file, target_file, mutant_id, lineno, build_result, tc_outcome):
    build_str = 'PASS' if build_result else 'FAIL'
    # tc_outcome: {'p2f': 2, 'p2p': 3, 'f2p': 0, 'f2f': 1}
    full_tc_outcome = f"{tc_outcome['p2f']},{tc_outcome['p2p']},{tc_outcome['f2p']},{tc_outcome['f2f']}"

    result_csv_file.write(f"{target_file},{mutant_id},{lineno},{build_str},{full_tc_outcome}\n")
        

def get_target_file_path(target_files, target_file):
    for file in target_files:
        if file.split('/')[-1] == target_file:
            return file
    return None


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


def get_selected_mutants(version_dir):
    get_selected_mutants = version_dir / 'selected_mutants.csv'
    assert get_selected_mutants.exists(), f"Selected mutants file {get_selected_mutants} does not exist"

    selected_mutants = {}
    with open(get_selected_mutants, 'r') as f:
        lines = f.readlines()
        mutants = lines[2:]

        for mutant_line in mutants:
            mutant_line = mutant_line.strip()
            info = mutant_line.split(',')

            target_filename = info[0]
            mutant_id = info[1]
            lineno = info[2]
            mutant_name = info[3]

            if target_filename not in selected_mutants:
                selected_mutants[target_filename] = {}
            
            if lineno not in selected_mutants[target_filename]:
                selected_mutants[target_filename][lineno] = []
            
            selected_mutants[target_filename][lineno].append({
                'mutant_id': mutant_id,
                'mutant_name': mutant_name
            })

    return selected_mutants


def get_lines_executed_by_failing_tcs(version_dir, target_code_file_path, buggy_lineno, target_files):
    lines_executed_by_failing_tc_file = version_dir / 'coverage_info/lines_executed_by_failing_tc.json'
    assert lines_executed_by_failing_tc_file.exists(), f"Lines executed by failing test cases file {lines_executed_by_failing_tc_file} does not exist"

    lines_executed_by_failing_tc_json = json.loads(lines_executed_by_failing_tc_file.read_text())

    execed_lines = {}
    for target_file in target_files:
        filename = target_file.split('/')[-1]
        execed_lines[filename] = []

    # TODO: read the file and return the content
    buggy_filename = target_code_file_path.split('/')[-1]
    executed_buggy_line = False
    for key, tcs in lines_executed_by_failing_tc_json.items():
        info = key.split('#')
        filename = info[0].split('/')[-1]
        function_name = info[1]
        lineno = info[2]

        if filename not in execed_lines:
            execed_lines[filename] = []
        execed_lines[filename].append(lineno)

        if filename == buggy_filename and lineno == buggy_lineno:
            executed_buggy_line = True

    assert executed_buggy_line, f"Buggy line {buggy_lineno} is not executed by any failing test cases"

    return execed_lines


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



def intitiate_mutants_dir(core_working_dir, version_name, target_files):
    mutants_dir = core_working_dir / 'generated_mutants'
    mutants_dir.mkdir(exist_ok=True, parents=True)

    version_mutants_dir = mutants_dir / version_name
    version_mutants_dir.mkdir(exist_ok=True)

    target_file_pair = []

    for target_file in target_files:
        target_file_path = core_working_dir / Path(target_file)
        assert target_file_path.exists(), f'{target_file_path} does not exist'

        target_file_name = target_file.replace('/', '-')
        single_file_mutant_dir = version_mutants_dir / f"{target_file_name}"
        single_file_mutant_dir.mkdir(exist_ok=True, parents=True)

        target_file_pair.append((target_file_path, single_file_mutant_dir))
    
    return target_file_pair

def make_patch_file(target_code_file_path, buggy_code_file, core_working_dir, patchname):
    patch_file = core_working_dir / patchname

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
        raise Exception(f'Failed to apply patch to {target_file.name} with buggy_version {buggy_code_file.name}')
    
    print(f'Applied patch to {target_file.name} with buggy_version {buggy_code_file.name} : revert={revert}')


def execute_clean_script(clean_sh_wd, core_working_dir):
    global clean_script

    clean_sh_wd = core_working_dir / clean_sh_wd
    clean_sh = clean_sh_wd / clean_script
    assert clean_sh.exists(), f"Clean script {clean_sh} does not exist"

    cmd = ['bash', clean_sh]
    res = sp.run(cmd, cwd=clean_sh_wd, stdout=sp.PIPE, stderr=sp.PIPE)
    
    print('Executed clean script')

    return res.returncode


def execute_configure_script(config_sh_wd, core_working_dir):
    global configure_no_cov_script

    config_sh_wd = core_working_dir / config_sh_wd
    config_sh = config_sh_wd / configure_no_cov_script
    assert config_sh.exists(), f"Configure script {config_sh} does not exist"

    cmd = ['bash', config_sh]
    res = sp.run(cmd, cwd=config_sh_wd, stdout=sp.PIPE, stderr=sp.PIPE)
    
    print('Executed configure script')

    return res.returncode

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
    return parser

if __name__ == "__main__":
    main()
    exit(0)
