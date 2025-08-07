date "+%Y-%m-%d %H:%M:%S"

it=$1

for i in `seq 1 ${NUM_SETS}`; do
    python agentless/translator/translate.py \
    --context_file results/$FOLDER_NAME/extracted_context_${i}/contexts.jsonl \
    --language_file results/$FOLDER_NAME/iter_${it}/decision_${i}/languages.jsonl \
    --output_folder results/$FOLDER_NAME/iter_${it}/translated_${i} \
    --num_threads $NJ \
    --it $it 
done

