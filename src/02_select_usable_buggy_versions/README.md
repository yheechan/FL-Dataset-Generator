# 02 Selecting usable buggy versions
* "Usable" buggy versions refer to buggy versions of target subject where:
    * all the failing test case executes its designated **buggy line number**
    * coverage of all test case is measurable (immeasurable when internal crash occurs)
    * atleast one failing and one passing TC exists.


## 02-1 Selecting initial buggy version
This step specifically describes the selected buggy versions as **"initial"** because selected buggy versions at this step have a probablity of being excluded when it doesn't satisfy the standard of being **"usable"**.

### What it does
1. Initialize working directory for target subject ``<subject-name>-working_directory/``
    * Copies subject source repository
    * Copies user configurations of target subject
    * Copies configure and build script to indicated paths
2. Randomly select N numbers of buggy version, where N is given by the user (option ``--num-versions <N>``)
    * Selected buggy versions include the **real-world-buggy-versions** given by the user in config directory

### Usage:
```
$ ./general_command.py --subject libxml2 --num-versions 300
```

## 02-2 Preparation stage for testing (finding "usable" buggy versions)

### What it does
1. Assign/distribute buggy versions to each cores of each machine(s)
2. Distribute subject directory to each cores of each machine(s)
3. Distribute commands for testing buggy versions (to collect "usable" buggy versions)

### Usage:
* When using single machine
```
$ ./general_command.py --subject libxml2
```

* When using multiple distributed machines
```
$ ./general_command.py --subject libxml2
$ ./01-1_initiate_directory.sh
$ ./01-2_distribute_buggy_versions.sh
$ ./02-1_distribute_repo.sh
$ ./03-1_distribute_config.sh
$ ./04-1_distribute_test_buggy_versions_cmd.sh
```


## 02-3 Testing buggy versions (for finding "usable" buggy versions)

### What it does
1. Initial configure and build
2. test mutants
    * ``02-1_execute_worker.py``: tests all assigned buggy versions
    * ``02-2_test_buggy_version.py``: test single buggy version of a core
        * patch file
        * build version (thrown away when failed)
        * iterate through executing a test case (only failing which was measured at step ``01_collect_buggy_mutants``)
        * measure coverage of iterated test case (validate failing TC executed buggy line)
        * unpatch file
    * save versions those are as usable

### Usage:
* When using single machine (execution on all cores)
```
$ ./general_command_all_local_cores.py --subject libxml2
```

* When using single machine (execution on single core)
```
$ ./general_command.py --subject libxml2 --worker gaster23.swtv/core0
```

* When using single machine (execution on single version of single core)
```
$ ./01_initial_configure_and_build.py --subject libxml2 --worker gaster23.swtv/core0
$ ./02-2_test_buggy_version.py --subject libxml2 --worker gaster23.swtv/core0 --version HTMLparser.MUT123.c
```

* When using multiple distributed machines (executes all cores of all machines)
```
$ ./03_test_buggy_versions_on_distributed_machines.py --subject libxml2
$ ./03-1_test_buggy_versions_on_distributed_machines.sh
```


## 02-4 Gather buggy versions

### What it does
1. Generate directory ``usable_buggy_versions/``
2. copies the buggy mutants collected from each core of machine(s)

### Usage:
* When using single machine
```
$ ./01_gather_buggy_versions.py --subject libxml2
```

* When using multiple distributed machines
```
$ ./01_gather_buggy_versions.py --subject libxml2
$ ./01-1_retrieve_usable_buggy_versions.sh
```


## 02-5 analyze_buggy_versions (each commands are optional)
This directory contains executable to analyze statistics of test cases & reduce # of TCs in the test suite.

### What it does and Usage:
1. ``01_testsuite_statistics.py``: Analyze TCs statistics of each version in buggy versions set
* where:
    * ``<subject-name>``: is the name of the target subject
    * ``<dir-name>``: is the directory name that contains the target buggy versions
    * ``<csv-filename>``: is the csv file to save statistics of TCs per buggy version
* generates a ``<csv-filename>`` within ``<subject-name>-working_directory/``
* this file contains TC statistics such as:
    * ``#_failing_TCs``, ``#_passing_TCs``, ``#_excluded_TCs``, ``#_total_TCs``
```
$ ./01_testsuite_statistics.py --subject <subject-name> --versions-set-name <dir-name> --output-csv <csv-filename>
```

2. ``02_form_reduced_testsuite``: form a file of ``reduced_test_stuite.txt`` and ``excluded_test_suite.txt`` within ``<subject-name>-working_directory/``
    * where:
        * ``<subject-name>``: is the name of the target subject
        * ``<dir-name>``: is the directory name that contains the target buggy versions
        * ``<num>``: is the target number in which the testsuite is reduced to
```
./02_form_reduced_testsuite --subject <subject-name> --versions-set-name <dir-name> --testsuite-size <num>
```



* This step saves the set of buggy versions with reduced test suite size within ``<dir-name>-reduced/`` directory.

3. ``03_apply_reduced_testsuite.py``: apply reduction of TCs to all buggy versions within ``usable_buggy_versions/`` according to the reduced file ``reduced_test_suite.txt``
    * This generates a new directory (set of buggy versions) which reduced TCs.
    * The excluded TCs are recorded in ``testsuite_info/excluded_tcs.txt`` file
    * files regarding test cases:
        * excluded_failing_tcs.txt
        * excluded_passing_tcs.txt
        * excluded_tcs.txt
        * passing_tcs.txt
```
./03_apply_reduced_testsuite --subject libxml2 <subject-name> --version-set-name <dir-name> --reduced-testsuite <reduced-testsuite-filename>
```


## dataset
* libxml2-working_directory-240524-v1.zip
    * with reduced
* libxml2-working_directory-240611-v2.zip
    * with reduced-appropriate
    * where appropriate are versions with failingTC + excludedfailingTC < 500
