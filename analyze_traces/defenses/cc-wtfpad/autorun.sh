#!/bin/bash

DATASET="../../txt_datasets/andana/nodef/"
ADAPTIVE_FILE="adaptive.py"

# Define parameter sets
declare -a PARAMS=(
    "1,1,1"
    "1,5,1"
    "1,5,2"
    "2,5,2"
)

for param in "${PARAMS[@]}"; do
    # Match exactly 20 spaces before 'for i in range(...)'
    sed -i '' -E "s/^( {20})for i in range\(sample_discrete_triangular\([^)]*\)\):/\1for i in range(sample_discrete_triangular(${param})):/g" "$ADAPTIVE_FILE"

    echo "Updated line:"
    grep "sample_discrete_triangular" "$ADAPTIVE_FILE"

    # Run your script
    python main.py "$DATASET" -c normal_rcv --log log
done