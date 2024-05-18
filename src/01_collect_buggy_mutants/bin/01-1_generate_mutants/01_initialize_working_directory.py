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



def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject)


def start_process(subject_name):
    # 1. Read configurations
    configs = read_configs(subject_name)

    # 2. Initialize working directory
    initialize_working_directory(configs, subject_name)

def read_configs(subject_name):
    global user_configs_dir

    config_json = user_configs_dir / subject_name / 'configurations.json'
    
    configs = None
    with config_json.open() as f:
        configs = json.load(f)
    
    if configs is None:
        raise Exception('Configurations are not loaded')
    
    return configs

def initialize_working_directory(configs, subject_name):
    global collect_buggy_mutants_dir, user_configs_dir, subjects_dir, external_tools_dir

    # Create working directory
    working_dir = collect_buggy_mutants_dir / f'{subject_name}-working_directory'
    working_dir.mkdir(exist_ok=True)

    # Copy subject to working directory
    target_subject = subjects_dir / subject_name
    cmd = ['cp', '-r', target_subject, working_dir]
    res = sp.call(cmd)
    if res != 0:
        raise Exception('Failed to copy subject to working directory')
    
    # Copy configure directory to working directory as <subject_name>-configures
    subject_config_dir = user_configs_dir / subject_name
    new_configure_dir = working_dir / f'{subject_name}-configures'
    cmd = ['cp', '-r', subject_config_dir, new_configure_dir]
    res = sp.call(cmd)
    if res != 0:
        raise Exception('Failed to copy configure directory to working directory')
    
    # Copy configure and build and clean_build script to working directory
    configure_file_position = working_dir / configs[config_sh_wd_key]
    build_file_position = working_dir / configs[build_sh_wd_key]
    clean_build_file_position = working_dir / configs[build_sh_wd_key]

    configure_file = new_configure_dir / configure_no_cov_script
    assert configure_file.exists(), 'Configure script does not exist'
    build_file = new_configure_dir / build_script
    assert build_file.exists(), 'Build script does not exist'
    clean_build_file = new_configure_dir / clean_build_script
    assert clean_build_file.exists(), 'Clean build script does not exist'

    cmd = ['cp', configure_file, configure_file_position]
    res = sp.call(cmd)
    if res != 0:
        raise Exception('Failed to copy configure script to working directory')
    
    cmd = ['cp', build_file, build_file_position]
    res = sp.call(cmd)
    if res != 0:
        raise Exception('Failed to copy build script to working directory')
    
    cmd = ['cp', clean_build_file, clean_build_file_position]
    res = sp.call(cmd)
    if res != 0:
        raise Exception('Failed to copy clean build script to working directory')
    
    # make external_tools directory in working directory
    ext_dir = working_dir / 'external_tools'
    ext_dir.mkdir(exist_ok=True)

    # copy musicup executable to external_tools directory
    musicup_exec = external_tools_dir / 'MUSICUP/music'
    assert musicup_exec.exists(), 'MUSICUP executable does not exist'

    cmd = ['cp', musicup_exec, ext_dir]
    res = sp.call(cmd)
    if res != 0:
        raise Exception('Failed to copy MUSICUP executable to working directory')
    
    print(f'Initialized working directory: {working_dir}')

    

    
    
    

def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    return parser
    


if __name__ == "__main__":
    main()