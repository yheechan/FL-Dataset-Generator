#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp

script_path = Path(__file__).resolve()
bin_dir = script_path.parent
action_dir = bin_dir.parent
src_dir = action_dir.parent

root_dir = src_dir.parent
working_dir = root_dir / 'working_directory'
working_dir.mkdir(exist_ok=True)
user_configs_dir = root_dir / 'user_configs'
subjects_dir = root_dir / 'subjects'

config_sh_wd = 'configure_script_working_directory'
build_sh_wd = 'build_script_working_directory'
configure_script = 'configure_no_cov_script.sh'
build_script = 'build_script.sh'



def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    return parser


def read_configs(subject_name):
    config_json = user_configs_dir / subject_name / 'configurations.json'
    
    configs = None
    with config_json.open() as f:
        configs = json.load(f)
    
    if configs is None:
        raise Exception('Configurations are not loaded')
    
    return configs


def execute_configure_script(config_sh_wd):
    config_sh_wd = working_dir / config_sh_wd
    cmd = ['bash', configure_script]
    res = sp.run(cmd, cwd=config_sh_wd)
    if res.returncode != 0:
        raise Exception('Failed to execute configure script')
    
    print('Executed configure script')

def execute_build_script(build_sh_wd):
    build_sh_wd = working_dir / build_sh_wd
    cmd = ['bash', build_script]
    res = sp.run(cmd, cwd=build_sh_wd)
    if res.returncode != 0:
        raise Exception('Failed to execute build script')
    
    print('Executed build script')

def start_build_process(subject_name):
    # 1. Read configurations
    configs = read_configs(subject_name)

    # 2. Execute configure script
    execute_configure_script(configs[config_sh_wd])

    # 3. Execute build script
    execute_build_script(configs[build_sh_wd])
    


if __name__ == "__main__":
    parser = make_parser()
    args = parser.parse_args()
    

    start_build_process(args.subject)