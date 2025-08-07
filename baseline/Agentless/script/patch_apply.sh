date "+%Y-%m-%d %H:%M:%S"

it=$1

for i in `seq 1 ${NUM_SETS}`; do
    python agentless/repair/apply_patch.py \
    --patch_file results/$FOLDER_NAME/iter_${it}/back_translated_patches_${i}/translated_patches.jsonl \
    --original_context_file results/$FOLDER_NAME/extracted_context_${i}/contexts.jsonl \
    --output_folder results/$FOLDER_NAME/iter_${it}/applied_patches_${i} \
    --diff_format \
    --max_samples ${NUM_SAMPLES_PER_SET} \
    ${TARGET_ID:+--target_id $TARGET_ID} 
done

