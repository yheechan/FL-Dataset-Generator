# 02 Selecting usable buggy versions
"Usable" buggy versions refer to buggy versions of target subject where:
* all the failing test case executes its designated **buggy line number** (coverage measureable)


## 02-1 Selecting initial buggy version
This step specifically describes the selected buggy versions as **"initial"** because selected buggy versions at the step have a probablity of being excluded due it is checked to be not **"usable"**.

1. Initialize working directory for target subject ``<subject-name>-working_directory/``
    2. Copies subject source repository
    3. Copies user configurations of target subject
    4. Copies configure and build script to indicated paths
2. Randomly selected user given number of buggy versions (in which it includes the **real-world-buggy-versions** given by the user)

```
$ ./general_command.py --subject libxml2 --num-versions 300
```

## 02-2 Preparation stage for testing (finding "usable" buggy versions)
1. Assign/distribute buggy versions to each cores of each machines (or each cores of a machine)
2. Distribute subject directory
3. Distribute buggy version testing bin

### Usage:
* When using single machine
```
$ ./general_command.py --subject libxml2
```

* When using distributed machines
```
$ ./general_command.py --subject libxml2
$ ./01-1_initiate_directory.sh
$ ./01-2_distribute_buggy_versions.sh
$ ./02-1_distribute_repo.sh
$ ./03-1_distribute_config.sh
$ ./04-1_distribute_test_buggy_versions_cmd.sh
```


## 02-3 Testing buggy versions (for finding "usable" buggy versions)



## 01-3 Test mutants & collect buggy mutants
* Command to run bug collection of one worker (core)
```
$ ./general_command.py --subject libxml2 --worker gaster23.swtv/core0
```

* Command to run bug collection of one version assigned to a core
```
$ ./01_initial_configure_and_build.py --subject libxml2 --worker gaster23.swtv/core0
$ ./02-2_test_buggy_version.py --subject libxml2 --worker gaster23.swtv/core0 --version HTMLparser.MUT123.c
```

* When using multi-machines
```
$ ./03_test_buggy_versions_on_distributed_machines.py --subject libxml2
$ ./03-1_test_buggy_versions_on_distributed_machines.sh
```


## 01-4 Gather buggy mutants (only in use of multi-machines)
```
$ ./01_gather_buggy_mutants.py --subject libxml2
```

