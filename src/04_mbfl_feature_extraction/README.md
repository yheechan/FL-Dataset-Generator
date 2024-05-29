# 04 MBFL feature extraction stage
This stage extracts MBFL features for each buggy versions (specifically buggy versions in ``03_prepare_prerequisites/<subject-name>-working_directory/prerequisite_data/`` directory).
Specific steps:
1. Apply buggy version code to the subject repository.
2. Build the project
3. Generate mutants
4. Select mutants to utilize (the amount given by user in configure)
5. Apply each mutant and run the test suite (passing and failing TCs)
    * Take into account of mutants that are not compilable
    * Take into account of the outcome of each test case (p2p, f2f, p2f, f2p)
6. Measure the mbfl features.

