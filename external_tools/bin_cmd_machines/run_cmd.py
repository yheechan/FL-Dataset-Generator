#!/usr/bin/python3
# import sys
import subprocess as sp
from pathlib import Path
import argparse

script_path = Path(__file__).resolve()
bin_dir = script_path.parent
root_dir = bin_dir.parent

def return_parser():
    parse = argparse.ArgumentParser(description="Run command on multiple machines")
    parse.add_argument("-l", "--list-host-files", help="list of host files", action="store_true", required=False)
    parse.add_argument("-s", "--show-machines", help="show list of machines", action="store_true", required=False)
    parse.add_argument("-th", "--target-host", help="host file", required=False, default=None)
    parse.add_argument("-c", "--cmd", help="command to run", required=False, default=None)
    return parse

def list_host_files():
    # list all host files
    cmd = f"ls -al ~/.hosts"
    sp.run(cmd, shell=True, check=True)

def show_host_machines(target_host):
    # show machines in target host file
    cmd = f"cat ~/.hosts/{target_host}"
    sp.run(cmd, shell=True, check=True)

    cmd = f"cat ~/.hosts/{target_host} | wc -l"
    res = sp.run(cmd, shell=True, check=True, stdout=sp.PIPE)
    num_machines = int(res.stdout.decode().strip())
    print(f"Number of machines in {target_host} file: {num_machines}")


def start_program(target_host, cmd):
    tot_cmd = f"stty -echo; printf 'Password: '; read PASS; stty echo; echo ${{PASS}} | parallel-ssh -h ~/.hosts/{target_host} -x -tt -t 0 -I \"{cmd}\""

    # check if user wants to run the command
    final_check = input(f"Are you sure you want to run the command \"{cmd}\" on {target_host}? (y/n): ")
    if final_check.lower() != "y":
        print("Exiting program")
        exit(1)

    try:
        sp.run(tot_cmd, shell=True, check=True)
    except sp.CalledProcessError as e:
        print(f"Error: {e}")
        exit(1)


# stty -echo; printf "Password: "; read PASS; stty echo; echo "${PASS}" |
# parallel-ssh -h ~/.hosts/fastera -x -tt -t 0 -I "sudo ls"
if __name__ == "__main__":
    parse = return_parser()
    args = parse.parse_args()

    list_hosts = args.list_host_files
    show_machines = args.show_machines
    target_host = args.target_host
    cmd = args.cmd

    # show list of host files
    if list_hosts:
        list_host_files()
        exit(0)
    
    # show machines in target host file
    if show_machines:
        if target_host is None:
            print("Please provide target host file")
            exit(1)
        
        show_host_machines(target_host)
        exit(0)
    
    # print error message if target_host and cmd are not provided
    if (not list_hosts) and (target_host is None or cmd is None):
        print("Please provide target host and command to run")
        parse.print_help()
        exit(1)

    # run command on target host
    if target_host is not None and cmd is not None:
        start_program(target_host, cmd)
    