./make_tc_scripts.py
./autogen.sh CFLAGS='-O0 -fprofile-arcs -ftest-coverage -g --save-temps' CC='clang-13' CXX_FLAGS='-O0 -fprofile-arcs -ftest-coverage -g --save-temps' CXX='clang++' --with-threads=no
