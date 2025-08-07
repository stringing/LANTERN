#!/bin/bash

# Check if language parameter is provided
if [ -z "$1" ]; then
    echo "Error: Language parameter is required."
    echo "Usage: $0 <lang> <iteration>"
    exit 1
fi

# Store the language parameter
lang="$1"
it=$2

# Execute the Python script with the appropriate paths
python ~/multi-swe-bench/scripts/reformat_pred.py \
    ~/MagentLess/data/${lang}_verified.jsonl \
    ~/MagentLess/results/${lang}_verified_claude/iter_${it}/all_preds.jsonl \
    ~/MagentLess/results/${lang}_verified_claude/iter_${it}/all_preds_reformat.jsonl

# Check if the command was successful
if [ $? -eq 0 ]; then
    echo "Successfully reformatted predictions for language: $lang and iteration: $it"
else
    echo "Error occurred while reformatting predictions for language: $lang and iteration: $it"
    exit 1
fi
