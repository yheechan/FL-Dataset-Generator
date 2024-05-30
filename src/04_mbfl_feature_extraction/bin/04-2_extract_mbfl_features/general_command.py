#!/usr/bin/python3

import subprocess as sp
import argparse

execute_worker = '01-1_execute_worker.py'

def main():
    parser = make_parser()
    args = parser.parse_args()
    start_process(args.subject, args.worker)


def start_process(subject_name, worker_name):

    # 1. Execute worker
    cmd = ['python3', execute_worker, '--subject', subject_name, '--worker', worker_name]
    res = sp.run(cmd)
    if res.returncode != 0:
        raise Exception('Failed to execute worker script')
    
    print('Successfully executed the worker script: extracting MBFL features')


def make_parser():
    parser = argparse.ArgumentParser(description='Copy subject to working directory')
    parser.add_argument('--subject', type=str, help='Subject name', required=True)
    parser.add_argument('--worker', type=str, help='Worker name (e.g., <machine-name>/<core-id>)', required=True)
    return parser


if __name__ == "__main__":
    main()