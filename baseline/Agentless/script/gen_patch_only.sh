date "+%Y-%m-%d %H:%M:%S"

it=$1

for i in `seq 1 ${NUM_SETS}`; do
    python agentless/repair/generate_patch_only.py \
    --context_file results/$FOLDER_NAME/iter_${it}/translated_${i}/translated_contexts.jsonl \
    --output_folder results/$FOLDER_NAME/iter_${it}/generated_patches_${i} \
    --max_samples ${NUM_SAMPLES_PER_SET} \
    --cot \
    --diff_format \
    ${TARGET_ID:+--target_id $TARGET_ID} \
    --num_threads $NJ 
done


