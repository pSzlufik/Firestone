#!/bin/bash

chmod +x DFSD.sh
sed -i 's/\r//' DFSD.sh

. ./DFSD.sh
#. ./debug.sh

run 200 1 200 3 "1;0;0" "4;15;16" 2 200 3 "1;0;0" "5;14;15"