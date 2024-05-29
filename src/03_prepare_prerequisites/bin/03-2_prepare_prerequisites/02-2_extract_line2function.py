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
    start_process(args.subject, args.worker, args.version)


def start_process(subject_name, worker_name, version_name):
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

    # 4. get buggy code file
    buggy_code_file = get_buggy_code_file(version_dir, buggy_code_filename)
    # print(f"Buggy code file: {buggy_code_file.name}")

    # 5. get extractor
    extractor = subject_working_dir / 'external_tools/extractor'


    # 6. conduct run tests on buggy version with failing test cases
    extract_line2function(
        configs, core_working_dir, version_name, 
        target_code_file_path, buggy_code_file, 
        extractor, version_dir
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




def extract_line2function(
        configs, core_working_dir, version_name, 
        target_code_file_path, buggy_code_file, 
        extractor, version_dir):
    global my_env

    # --- prepare needed directories

    # --- first patch the code and build
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

    # --- extract line2function data
    target_preprocessed_files = configs['target_preprocessed_files']

    perfile_line2function_data = {}
    for pp_file_str in target_preprocessed_files:
        pp_file = core_working_dir / pp_file_str
        assert pp_file.exists(), f"Preprocessed file {pp_file} does not exist"

        cmd = [extractor, pp_file.__str__()]
        process = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE, encoding='utf-8')

        while True:
            line = process.stdout.readline()
            if line == '' and process.poll() != None:
                break
            line = line.strip()
            if line == '':
                continue

            # ex) one##htmlReadDoc(const xmlChar * cur, const char * URL, const char * encoding, int options)##6590##6603##HTMLparser.c:6590:1##HTMLparser.c
            data = line.split('##')
            class_name = data[0]
            function_name = data[1]
            start_line = data[2]
            end_line = data[3]
            originated_file = data[4]
            file_data = originated_file.split(':')[0]
            filename = data[5]

            if file_data not in perfile_line2function_data:
                perfile_line2function_data[file_data] = []
            
            full_function_name = f"{class_name}::{function_name}" if class_name != 'None' else function_name
            data = (full_function_name, start_line, end_line)
            if data not in perfile_line2function_data[file_data]:
                perfile_line2function_data[file_data].append(data)
        
        print('> Extracted line2function data from {}'.format(pp_file.name))
    
    # 4. Apply patch reverse
    apply_patch(target_code_file_path, buggy_code_file, patch_file, core_working_dir, True)

    # 5. Save the buggy version
    line2function_file = save_line2function(version_dir, perfile_line2function_data)

    print(f"Extracted line2function data from {version_name} and saved to {line2function_file.name}")

def save_line2function(version_dir, perfile_line2function_data):
    line2function_dir = version_dir / 'line2function_info'
    line2function_dir.mkdir(exist_ok=True)

    line2function_file = line2function_dir / 'line2function.json'
    with line2function_file.open('w') as f:
        json.dump(perfile_line2function_data, f, ensure_ascii=False, indent=2)
    
    return line2function_file


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
        raise Exception(f'Failed to apply patch to {target_file.name} with buggy_version {buggy_code_file.name}')
    
    print(f'Applied patch to {target_file.name} with buggy_version {buggy_code_file.name} : revert={revert}')



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
