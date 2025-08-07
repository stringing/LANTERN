date "+%Y-%m-%d %H:%M:%S"

it=$1

folders=`ls results/$FOLDER_NAME/iter_${it}/applied_patches_* -d | paste -sd ','`
python agentless/repair/rerank.py \
    --patch_folder $folders \
    --num_samples $(($NUM_SETS * $NUM_SAMPLES_PER_SET)) \
    --deduplicate \
    --output_file results/$FOLDER_NAME/iter_${it}/all_preds.jsonl

