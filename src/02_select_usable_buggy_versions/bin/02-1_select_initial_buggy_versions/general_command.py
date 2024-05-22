#!/usr/bin/python3

import subprocess as sp
import argparse

initialize_working_directory = '01_initialize_working_directory.py'
initial_select_buggy_versions = '02_select_initial_buggy_versions.py'

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.num_versions)

def start_process(subject_name, num_versions):

    # 1. Initialize working directory
    cmd = ['python3', initialize_working_directory, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute initialize working directory script')
    
    # 2. Select initial buggy versions
    cmd = ['python3', initial_select_buggy_versions, '--subject', subject_name, '--num-versions', str(num_versions)]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute select initial buggy versions script')
    
    print("\n Initial buggy versions selected successfully \n")


def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    parser.add_argument('--num-versions', type=int, help='Number of buggy versions to select', required=True)
    return parser


if __name__ == "__main__":
    main()