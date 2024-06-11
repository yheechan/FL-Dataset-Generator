# 01 Collect Buggy Mutants of target subject

## 01-1 Generate mutants
### What it does
1. Initialize working directory for target subject ``<subject-name>-working_directory/``
    * Copies subject source repository
    * Copies user configurations of target subject
    * Copies configure and build script to indicated paths
    * Copies MUSICUP executable to ``external_tools/`` directory in working directory
2. Executes configure and build script in indicated paths
3. Generates mutants using MUSICUP and saves to ``generated_mutants/`` directory in working directory

### Usage:
```
$ ./general_command.py --subject libxml2
```


## 01-2 Prepare for testing mutants to collect buggy mutants
### What it does
1. Assign/distribute mutants to each cores of each machines (or each cores of a machine)
2. Distribute subject directory to each cores of each machines (or each cores of a machine)
3. Distribute mutation testing bin
4. Distribute commands for testing mutants (to collect buggy mutant versions)

### Usage:
* When using single machine
```
$ ./general_command.py --subject libxml2
```

* When using multiple distributed machines
```
$ ./general_command.py --subject libxml2
$ ./01-1_initiate_directory.sh
$ ./01-2_distribute_mutants.sh
$ ./02-1_distribute_repo.sh
$ ./03-1_distribute_config.sh
$ ./04-1_distribute_test_mutants_cmd.sh
```



## 01-3 Test mutants & collect buggy mutants
### What it does
1. Initial configure and build
2. test mutants
    * patch mutant code
    * execute test cases
    * save mutants those are classified as buggy (where atleast 1 failing TC exists)

### Usage:
* When using single machine (execution on all cores)
```
$ ./general_command_all_local_cores.py --subject libxml2
```

* When using single machine (execution on single core)
```
$ ./general_command.py --subject libxml2 --worker gaster23.swtv/core0
```


* When using multiple distributed machines (executes all cores of all machines)
```
$ ./03_test_mutants_on_distributed_machines.py --subject libxml2
$ ./03-1_test_mutants_on_distributed_machines.sh
```


## 01-4 Gather buggy mutants (only in use of multi-machines)
### What it does
1. Generates directory ``buggy_mutants/``
2. copies the buggy mutants collected from each core of machine(s)

### Usage:
* When using single machine
```
$ ./01_gather_buggy_mutants.py --subject libxml2
```

* When using multiple distributed machines
```
$ ./01_gather_buggy_mutants.py --subject libxml2
$ ./01-1_retrieve_buggy_mutants.sh
```
