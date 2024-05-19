# Collect Buggy Mutants of target subject

## 01-1 Generate mutants
1. Initialize working directory for target subject ``<subject-name>-working_directory/``
    2. Copies subject source repository
    3. Copies user configurations of target subject
    4. Copies configure and build script to indicated paths
    5. Copies MUSICUP executable to ``external_tools/`` directory in working directory
2. Executes configure and build script in indicated paths
3. Generates mutants using MUSICUP and saves to ``generated_mutants/`` directory in working directory

```
$ ./general_command.py --subject libxml2
```


## 01-2 Prepare for testing mutants to collect buggy mutants
1. Assign/distribute mutants to each cores of each machines (or each cores of a machine)
2. Distribute subject directory
3. Distribute mutation testing bin

### Usage:
* When using single machine
```
$ ./general_command.py --subject libxml2
```

* When using distributed machines
```
$ ./general_command.py --subject libxml2
$ ./01-1_initiate_directory.sh
$ ./01-2_distribute_mutants.sh
$ ./02-1_distribute_repo.sh
$ ./03-1_distribute_config.sh
$ ./04-1_distribute_test_mutants_cmd.sh
```



## 01-3 Test mutants & collect buggy mutants
* Command to run bug collection of one worker (core)
```
$ ./general_command.py --subject libxml2 --worker gaster23.swtv/core0
```
* When using multi-machines
```
$ ./03_test_mutants_on_distributed_machines.py --subject libxml2
$ ./03-1_test_mutants_on_distributed_machines.sh
```


## 01-4 Gather buggy mutants (only in use of multi-machines)

