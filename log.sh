#!/bin/bash

LOG_FILE="logs/rlb_$(date +%Y_%m_%d_%H%M%S).log"

exec 3>&1 1>>${LOG_FILE} 2>&1
./build/rlb | tee /dev/fd/3
