date "+%Y-%m-%d %H:%M:%S"

it=$1

python -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Lite \
    --predictions_path ../Agentless/results/swe-bench-lite/iter_${it}/all_preds.jsonl \
    --max_workers 50 \
    --run_id tr_${it}
    # use --predictions_path 'gold' to verify the gold patches
    # use --run_id to name the evaluation run
    # use --modal true to run on Modal
