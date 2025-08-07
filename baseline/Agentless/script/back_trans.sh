date "+%Y-%m-%d %H:%M:%S"

it=$1

for i in `seq 1 ${NUM_SETS}`; do
    python agentless/translator/back_translate.py \
    --patch_file results/$FOLDER_NAME/iter_${it}/generated_patches_${i}/extracted_patches.jsonl \
    --original_context_file results/$FOLDER_NAME/extracted_context_${i}/contexts.jsonl \
    --output_folder results/$FOLDER_NAME/iter_${it}/back_translated_patches_${i} \
    ${TARGET_ID:+--target_id $TARGET_ID} \
    --num_threads $NJ 
done

