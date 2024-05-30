# 04 MBFL feature extraction stage
This stage extracts MBFL features for each buggy versions (specifically buggy versions in ``03_prepare_prerequisites/<subject-name>-working_directory/prerequisite_data/`` directory).
Specific steps:
1. Generate mutants
    1. Apply buggy version code to the subject repository.
    2. Configure & Build the project (do make clean)
    3. Execute music to generate mutants
4. Select mutants to utilize (the amount given by user in configure)
5. Apply each mutant and run the test suite (passing and failing TCs)
    * Take into account of mutants that are not compilable
    * Take into account of the outcome of each test case (p2p, f2f, p2f, f2p)
6. Measure the mbfl features.


## 04-1 Initialization stage for mbfl feature extraction
Initializes directories and distributed buggy versions (w/ prerequisite data)
1. Initialization of working directory: ``<subject-name>-working_directory/``
2. Assign/Distribute buggy versions (w/ prerequisite data)
3. Distribute subject repository
4. Distribute user configurations
5. Distribute command directory for preparing prerequisites
6. Distribute external tools specifically ``music`` to extract line2function information.

### Usage with single machine
* where:
    * ``<subject-name>``: is the name of the target subject
```
$ ./general_command --subject <subject-name>
```


### Usage with multiple distribute machines
```
$ ./general_command.py --subject libxml2
$ ./02-1_initiate_directory.sh
$ ./02-2_distribute_buggy_versions.sh
$ ./03-1_distribute_repo.sh
$ ./04-1_distribute_config.sh
$ ./05-1_distribute_prepare_prerequisites_cmd.sh
$ ./06-1_distribute_external_tools.sh
```


# 04-2 Extracting MBFL features from buggy versions
This stage runs the engine to extract mbfl features for each buggy versions in the set of ``03_prepare_prerequisites/<subject-name>-working_directory/prerequisite_data/``.
1. Generate mutants for the buggy versions
2. Select mutants (``max_mutants`` given by user)
3. Test the mutants (Execute each test cases and record the outcome, p2f, f2p, etc)
5. Measure mbfl features (MUSE and Metallaxis)

### Usage when executing MBFL feature extraction on single core of a machine
```
$ ./general_command.py --subject libxml2 --worker gaster23.swtv/core0
```

### Usage when executing MBFL feature extraction on single version of a single core
```
$ ./01-2_generate_mutants --subject libxml2 --worker gaster23.swtv/core0 --version HTMLparser.MUT123.c
$ ./01-3_select_mutants --subject libxml2 --worker gaster23.swtv/core0 --version HTMLparser.MUT123.c
$ ./01-4_test_mutants --subject libxml2 --worker gaster23.swtv/core0 --version HTMLparser.MUT123.c
$ ./01-5_measure_mbfl_features --subject libxml2 --worker gaster23.swtv/core0 --version HTMLparser.MUT123.c
```

### Usage when executing MBFL extraction on multiple distributed machines
```
$ ./02_extract_mbfl_features_on_distributed_machines.py --subject libxml2
$ ./02-1_extract_mbfl_features_on_distributed_machines.sh
```
