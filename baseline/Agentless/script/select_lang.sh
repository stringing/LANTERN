date "+%Y-%m-%d %H:%M:%S"

it=$1

for i in `seq 1 ${NUM_SETS}`; do
    python agentless/analyzer/select_languages.py \
        --context_file results/$FOLDER_NAME/extracted_context_${i}/contexts.jsonl \
        --output_file results/$FOLDER_NAME/iter_${it}/decision_${i}/languages.jsonl \
        --seed 66 \
        --it $it 
done