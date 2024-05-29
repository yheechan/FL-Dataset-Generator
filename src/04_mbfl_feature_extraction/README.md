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