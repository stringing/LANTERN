#!/bin/bash

# Simple workflow script for 10 iterations
FOLDER="Results/1.2f/"
DATASET="defects4j-1.2-function"
TRANS_TEMPERATURE=0.3
NUM_PROC=17
NATTEMPT=20
TMP_PREFIX="tr"

# echo "Initial repair..."

python repair.py --folder $FOLDER --dataset $DATASET --num_proc $NUM_PROC --concurrent --nattempt $NATTEMPT --tmp_prefix $TMP_PREFIX

echo "Starting translation-based repair workflow (11 iterations)"

for iteration in {1..11}; do
    echo "=== Iteration $iteration ==="
    
    # Step 1: Translate
    echo "Translating..."
    python translate.py --folder $FOLDER --dataset $DATASET --TRANS_TEMPERATURE $TRANS_TEMPERATURE --num_proc $NUM_PROC --iteration $iteration --concurrent
    
    # Step 2: Repair
    echo "Repairing..."
    python repair_translated.py --folder $FOLDER --iteration $iteration --dataset $DATASET --num_proc $NUM_PROC --concurrent --nattempt $NATTEMPT
    
    # Step 3: Back-translate
    echo "Back-translating..."
    python back_translate.py --folder $FOLDER --iteration $iteration --TRANS_TEMPERATURE $TRANS_TEMPERATURE --tmp_prefix $TMP_PREFIX --num_proc $NUM_PROC --concurrent
    
    echo "Iteration $iteration completed"
done

echo "All 10 iterations completed!"