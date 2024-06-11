#!/usr/bin/python3

from pathlib import Path
import argparse
import json
import subprocess as sp

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


def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.worker, args.use_excluded_failing_tcs)


def start_process(subject_name, worker_name, use_excluded_failing_tcs):
    subject_working_dir = prepare_prerequisites_dir / f"{subject_name}-working_directory"
    assert subject_working_dir.exists(), f"Working directory {subject_working_dir} does not exist"

    core_working_dir = subject_working_dir / 'workers_preparing_prerequisites' / worker_name
    assert core_working_dir.exists(), f"Core working directory {core_working_dir} does not exist"

    # 1. Read configurations
    configs = read_configs(subject_name, subject_working_dir)

    # 2. get list assigned buggy versions (is a path to the buggy versions directory)
    assigned_versions_list = get_assigned_buggy_versions(configs, core_working_dir)

    # 3. conduct mutation testing
    prepare_prerequisites(configs, core_working_dir, worker_name, assigned_versions_list, use_excluded_failing_tcs)



def get_assigned_buggy_versions(configs, core_working_dir):
    assigned_buggy_versions = core_working_dir / 'assigned_buggy_versions'

    assigned_versions_list = []
    for target_version in assigned_buggy_versions.iterdir():
        assigned_versions_list.append(target_version)
    
    print(f"Total assigned buggy versions: {len(assigned_versions_list)}")

    return assigned_versions_list


def prepare_prerequisites(configs, core_working_dir, worker_name, assigned_versions_list, use_excluded_failing_tcs):
    global prepare_prerequisites_cmd_dir

    # --subject libxml2 --worker gaster23.swtv/core0 --version <assigned-version>
    line2function = prepare_prerequisites_cmd_dir / '02-2_extract_line2function.py'
    measure_coverage = prepare_prerequisites_cmd_dir / '02-3_measure_coverage.py'
    postprocess_coverage = prepare_prerequisites_cmd_dir / '02-4_postprocess_coverage.py'


    for target_version in assigned_versions_list:
        version_name = target_version.name

        # 1. Extract line2function
        cmd = [
            'python3', line2function,
            '--subject', configs['subject_name'],
            '--worker', worker_name,
            '--version', version_name
        ]
        res = sp.run(cmd)
        if res.returncode != 0:
            raise Exception('Failed to execute buggy version prerequisites script')


        # 2. Measure coverage
        cmd = [
            'python3', measure_coverage,
            '--subject', configs['subject_name'],
            '--worker', worker_name,
            '--version', version_name
        ]
        if use_excluded_failing_tcs:
            cmd.append('--use-excluded-failing-tcs')
        res = sp.run(cmd)
        if res.returncode != 0:
            raise Exception('Failed to execute buggy version prerequisites script')
        
        # 3. Postprocess coverage
        cmd = [
            'python3', postprocess_coverage,
            '--subject', configs['subject_name'],
            '--worker', worker_name,
            '--version', version_name
        ]
        res = sp.run(cmd)
        if res.returncode != 0:
            raise Exception('Failed to execute buggy version prerequisites script')
    
    print('Successfully executed the buggy version prerequisites script')
    



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
    parser.add_argument('--use-excluded-failing-tcs', action='store_true', help='Use excluded failing test cases')
    return parser

if __name__ == "__main__":
    main()