#!/usr/bin/python3

import subprocess as sp
import argparse


initialize_working_directory = '01_initialize_working_directory.py'
distribute_buggy_versions = '02_distribute_buggy_versions.py'
distribute_config = '03_distribute_config.py'
distribute_sbfl_extraction_cmd = '04_distribute_sbfl_extraction_cmd.py'

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
    
    # 3. distribute config directory
    cmd = ['python3', distribute_config, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute distribute config directory script')
    
    # 4. distribute sbfl extraction command
    cmd = ['python3', distribute_sbfl_extraction_cmd, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute distribute sbfl extraction command script')
    print('>> Distributed sbfl extraction command')
    

    


def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    return parser


if __name__ == "__main__":
    main()