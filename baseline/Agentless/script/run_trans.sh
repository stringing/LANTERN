set -x

# api_key.sh
# export OPENAI_API_KEY=
# export OPENAI_BASE_URL=
# export OPENAI_MODEL=
# export OPENAI_EMBED_URL=
source script/api_key.sh

export NJ=50
export NUM_SETS=4
export NUM_SAMPLES_PER_SET=10
export NUM_REPRODUCTION=0
export FOLDER_NAME=swe-bench-lite
export SPLIT=test
export DATASET=princeton-nlp/SWE-bench_Lite



for i in {1..11}; do
    ./script/select_lang.sh $i
    ./script/translate.sh $i
    ./script/gen_patch_only.sh $i
    ./script/back_trans.sh $i
    ./script/patch_apply.sh $i
    ./script/rerank.sh $i
    cd ../SWE-bench
    ./eval.sh $i
    cd ../Agentless
done