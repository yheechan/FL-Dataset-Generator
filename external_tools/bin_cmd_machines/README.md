# bin_cmd_machines
This bin directory is to contain python scripts to run commands on distributed machines (machines referred at ``~/.hosts/*``).


## Commands

### ``run_cmd.py``
* operation: executes commands in CLI of distributed machines.
* purpose: to simplify executing commands to handle moving, deleting, or backup files within the distributed machines.
```
usage: run_cmd.py [-h] [-l] [-s] [-th TARGET_HOST] [-c CMD]

Run command on multiple machines

optional arguments:
  -h, --help            show this help message and exit
  -l, --list-host-files
                        list of host files
  -s, --show-machines   show list of machines
  -th TARGET_HOST, --target-host TARGET_HOST
                        host file
  -c CMD, --cmd CMD     command to run
```

last updated on April 3, 2024
