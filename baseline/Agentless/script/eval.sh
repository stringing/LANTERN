#!/bin/bash

# Check if language parameter is provided
if [ -z "$1" ]; then
    echo "Error: Language parameter is required."
    echo "Usage: $0 <lang> <iteration>"
    exit 1
fi

create_dir_if_not_exists() {
    local path="$1"
    
    if [ ! -d "$path" ]; then
        mkdir -p "$path"
        echo "Directory created: $path"
    else
        echo "Directory already exists: $path"
    fi
}

# Store the language parameter
lang="$1"
it=$2

create_dir_if_not_exists "./eval_results/${lang}/iter_${it}"
create_dir_if_not_exists "./logs/${lang}/iter_${it}"

cd ~/multi-swe-bench
# Execute the evaluation command
python -m multi_swe_bench.harness.run_evaluation \
    --mode evaluation \
    --workdir ./workdir \
    --patch_files /root/MagentLess/results/${lang}_verified_claude/iter_${it}/all_preds_reformat.jsonl \
    --dataset_files /root/MagentLess/data/${lang}_verified.jsonl \
    --force_build false \
    --output_dir ./eval_results/${lang}/iter_${it} \
    --repo_dir /root/MagentLess/repo \
    --need_clone false \
    --clear_env true \
    --stop_on_error true \
    --max_workers 8 \
    --max_workers_build_image 8 \
    --max_workers_run_instance 8 \
    --log_dir ./logs/${lang}/iter_${it} \
    --log_level DEBUG \

# Check if the command was successful
if [ $? -eq 0 ]; then
    echo "Successfully ran evaluation for language: $lang and iteration: $it"
else
    echo "Error occurred while running evaluation for language: $lang and iteration: $it"
    exit 1
fi
