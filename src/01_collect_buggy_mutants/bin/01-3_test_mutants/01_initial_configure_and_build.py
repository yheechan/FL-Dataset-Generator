#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp
import time

# Current working directory
script_path = Path(__file__).resolve()
test_mutants_dir = script_path.parent
bin_dir = test_mutants_dir.parent
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
clean_script = 'clean_script.sh'
machines_json_file = 'machines.json'
configure_json_file = 'configurations.json'


def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.worker)


def start_process(subject_name, worker_name):
    subject_working_dir = collect_buggy_mutants_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    core_working_dir = subject_working_dir / 'workers_testing_mutants' / worker_name
    assert core_working_dir.exists(), f"Core working directory {core_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. Execute configure and build scripts
    configure_and_build(configs, core_working_dir)


def configure_and_build(configs, core_working_dir):
    # Execute configure script
    execute_configure_script(configs[config_sh_wd_key], core_working_dir)

    # Execute build script
    execute_build_script(configs[build_sh_wd_key], core_working_dir)



def execute_configure_script(config_sh_wd, core_working_dir):
    global configure_no_cov_script

    config_sh_wd = core_working_dir / config_sh_wd
    config_sh = config_sh_wd / configure_no_cov_script
    assert config_sh.exists(), f"Configure script {config_sh} does not exist"

    cmd = ['bash', config_sh]
    res = sp.run(cmd, cwd=config_sh_wd)
    if res.returncode != 0:
        raise Exception('Failed to execute configure script')
    
    print('Executed configure script')

def execute_build_script(build_sh_wd, core_working_dir):
    global build_script

    build_sh_wd = core_working_dir / build_sh_wd
    build_sh = build_sh_wd / build_script
    assert build_sh.exists(), f"Build script {build_sh} does not exist"

    cmd = ['bash', build_script]
    res = sp.run(cmd, cwd=build_sh_wd)
    if res.returncode != 0:
        raise Exception('Failed to execute build script')
    
    print('Executed build script')



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