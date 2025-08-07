#!/bin/bash

# python main.py --dataset humaneval --signature --model gpt-3.5-turbo-0301 --output_path humaneval_output.jsonl

# python main.py --dataset xcodeeval --model deepseek-chat --output_path output --max_tokens 4096 --temperature 1.0

# python main_concurrent.py --dataset_path /root/apr --model deepseek-chat --output_path output --max_tokens 4096 --temperature 1.0 --num_proc 17

for i in {1..11}; do
    python main_concurrent.py --dataset_path /root/apr --model deepseek-chat --output_path output --max_tokens 4096 --temperature 1.0 --num_proc 17 --it $i
done