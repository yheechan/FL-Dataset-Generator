#!/usr/bin/python3

import subprocess as sp
import argparse

initialize_working_directory = '01_initialize_working_directory.py'
configure_and_build = '02_configure_and_build.py'
gen_mutants = '03_gen_mutants.py'

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject)

def start_process(subject_name):
    # 1. Initialize working directory
    cmd = ['python3', initialize_working_directory, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute initialize working directory script')
    
    # 2. Configure and build
    cmd = ['python3', configure_and_build, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute configure and build script')
    
    # 3. Generate mutants
    cmd = ['python3', gen_mutants, '--subject', subject_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute generate mutants script')
    
    print('Finished generating mutants')


def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    return parser


if __name__ == "__main__":
    main()