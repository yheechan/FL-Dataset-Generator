#!/usr/bin/python3

import subprocess as sp
import argparse

initial_configure_and_build = '01_initial_configure_and_build.py'
test_mutants = '02_test_mutants.py'

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.worker)


def start_process(subject_name, worker_name):
    
    # 1. Initial configure and build
    cmd = ['python3', initial_configure_and_build, '--subject', subject_name, '--worker', worker_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute initial configure and build script')
    
    # 2. Test mutants
    cmd = ['python3', test_mutants, '--subject', subject_name, '--worker', worker_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute test mutants script')


def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    parser.add_argument('--worker', type=str, help='Worker name (e.g., <machine-name>/<core-id>)', required=True)
    return parser


if __name__ == "__main__":
    main()