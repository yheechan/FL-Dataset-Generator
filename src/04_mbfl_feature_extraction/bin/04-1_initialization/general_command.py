#!/usr/bin/python3

import subprocess as sp
import argparse


initialize_working_directory = '01_initialize_working_directory.py'
distribute_buggy_versions = '02_distribute_buggy_versions.py'
distribute_repo = '03_distribute_repo.py'
distribute_config = '04_distribute_config.py'
distribute_mbfl_extraction_cmd = '05_distribute_mbfl_extraction_cmd.py'
distribute_external_tools = '06_distribute_external_tools.py'

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject)

def start_process(subject_name):
    
    # 1. initialize working directory
    cmd = ['python3', initialize_working_directory, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute initialize working directory script')
    print('>> Initialized working directory')
    
    # 2. distribute buggy versions
    cmd = ['python3', distribute_buggy_versions, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute distribute buggy versions script')
    print('>> Distributed buggy versions')
    
    # 3. distribute subject repository
    cmd = ['python3', distribute_repo, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute distribute subject repository script')
    print('>> Distributed subject repository')
    
    # 4. distribute config directory
    cmd = ['python3', distribute_config, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute distribute config directory script')
    print('>> Distributed config directory')
    
    # 5. distribute prepare prerequisites command
    cmd = ['python3', distribute_mbfl_extraction_cmd, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute distribute prepare prerequisites command script')
    print('>> Distributed prepare prerequisites command')
    
    # 6. distribute external tools
    cmd = ['python3', distribute_external_tools, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute distribute external tools script')
    print('>> Distributed external tools')

    


def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    return parser


if __name__ == "__main__":
    main()