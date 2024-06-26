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
    start_process(args.subject, args.worker)


def start_process(subject_name, worker_name):
    subject_working_dir = select_usable_buggy_versions / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    core_working_dir = subject_working_dir / 'workers_selecting_buggy_versions' / worker_name
    assert core_working_dir.exists(), f"Core working directory {core_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. get list assigned buggy versions (is a path to the buggy versions directory)
    assigned_versions_list = get_assigned_buggy_versions(configs, core_working_dir)

    # 3. conduct mutation testing
    test_buggy_versions(configs, core_working_dir, worker_name, assigned_versions_list)



def get_assigned_buggy_versions(configs, core_working_dir):
    assigned_buggy_versions = core_working_dir / 'assigned_buggy_versions'

    assigned_versions_list = []
    for target_version in assigned_buggy_versions.iterdir():
        assigned_versions_list.append(target_version)
    
    print(f"Total assigned buggy versions: {len(assigned_versions_list)}")

    return assigned_versions_list


def test_buggy_versions(configs, core_working_dir, worker_name, assigned_versions_list):
    global test_buggy_versions_dir

    unusable_versions = []

    # --subject libxml2 --worker gaster23.swtv/core0 --version <assigned-version>
    test_buggy_version = test_buggy_versions_dir / '02-2_test_buggy_version.py'

    for target_version in assigned_versions_list:
        version_name = target_version.name
        cmd = [
            'python3', test_buggy_version,
            '--subject', configs['subject_name'],
            '--worker', worker_name,
            '--version', version_name
        ]
        res = sp.run(cmd)
        if res.returncode != 0:
            unusable_versions.append(version_name)

    unusable_list_file = core_working_dir / 'unusable_buggy_versions.txt'
    with unusable_list_file.open('w') as f:
        for unusable_version in unusable_versions:
            f.write(f"{unusable_version}\n")



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