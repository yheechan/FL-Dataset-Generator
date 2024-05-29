# 02 Selecting usable buggy versions
"Usable" buggy versions refer to buggy versions of target subject where:
* all the failing test case executes its designated **buggy line number** (coverage measureable)
* atleast one failing and one passing TC exists.


## 02-1 Selecting initial buggy version
This step specifically describes the selected buggy versions as **"initial"** because selected buggy versions at this step have a probablity of being excluded when it doesn't satisfy the standard of being **"usable"**.

1. Initialize working directory for target subject ``<subject-name>-working_directory/``
    * Copies subject source repository
    * Copies user configurations of target subject
    * Copies configure and build script to indicated paths
2. Randomly selected user given number of buggy versions (in which it includes the **real-world-buggy-versions** given by the user in config directory)

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


## 02-4 Gather buggy versions
Command to run gathering buggy version to one directory

* Command to gather buggy version when using single machine
```
$ ./01_gather_buggy_versions.py --subject libxml2
```

* Command to gather buggy versions when using multiple distributed machines.
```
$ ./01_gather_buggy_versions.py --subject libxml2
$ ./01-1_retrieve_usable_buggy_versions.sh
```


## 02-5 analyze_buggy_versions (optional)
This directory contains executable to analyze statistics of test cases & reduce # of TCs in the test suite.

1. Analyze TCs statistics of each version in buggy versions set
    * where:
        * ``<subject-name>``: is the name of the target subject
        * ``<dir-name>``: is the directory name that contains the target buggy versions
        * ``<csv-filename>``: is the csv file to save statistics of TCs per buggy version
```
$ ./01_testsuite_statistics.py --subject <subject-name> --versions-set-name <dir-name> --output-csv <csv-filename>
```

2. form a file of reduced & excluded TCs in a text file
    * where:
        * ``<subject-name>``: is the name of the target subject
        * ``<dir-name>``: is the directory name that contains the target buggy versions
        * ``<num>``: is the target number in which the testsuite is reduced to
    * This step saves the set of buggy versions with reduced test suite size within ``<dir-name>-reduced/`` directory.
```
./02_form_reduced_testsuite --subject <subject-name> --versions-set-name <dir-name> --testsuite-size <num>
```

3. apply reduction of TCs according to the reduced file map
    * This generates a new directory (set of buggy versions) which has reduced TCs.
    * The excluded TCs are recorded in ``testsuite_info/excluded_tcs.txt`` file
```
./03_apply_reduced_testsuite --subject libxml2 <subject-name> --version-set-name <dir-name> --reduced-testsuite <reduced-testsuite-filename>
```