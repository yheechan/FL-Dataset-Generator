#!/usr/bin/python3

import subprocess as sp
import argparse

distribute_buggy_versions = '01_distribute_buggy_versions.py'
distribute_repo = '02_distribute_repo.py'
distribute_config = '03_distribute_config.py'
distribute_test_buggy_versions_cmd = '04_distribute_test_buggy_versions_cmd.py'

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject)

def start_process(subject_name):
    # 1. Distribute mutants
    cmd = ['python3', distribute_buggy_versions, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute distribute buggy versions script')
    
    # 2. Distribute repository
    cmd = ['python3', distribute_repo, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute distribute repository script')
    
    # 3. Distribute configurations
    cmd = ['python3', distribute_config, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute distribute configurations script')
    
    # 4. Distribute test mutants command
    cmd = ['python3', distribute_test_buggy_versions_cmd, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute distribute test mutants command script')

    print("\n Buggy versions distributed successfully \n")


def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    return parser


if __name__ == "__main__":
    main()