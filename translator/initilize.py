import os
import tqdm
import jsonlines
import json
import argparse


LANG_CLUSTER_TO_LANG_COMPILER = {
    "C": "GNU C11",
    "C#": "Mono C#",
    "C++": "GNU C++17",
    "Go": "Go",
    "Java": "Java 17",
    "Javascript": "Node.js",
    "Kotlin": "Kotlin 1.4",
    "PHP": "PHP",
    "Python": "PyPy 3",
    "Ruby": "Ruby 3",
    "Rust": "Rust 2018",
}

def initilize_iter(base_dir, iter_idx):
    iter_dir = os.path.join(base_dir, f"iter_{iter_idx}")
    os.makedirs(iter_dir, exist_ok=True)
    return iter_dir

def filter_unfixed(eval_dir, unfixed_k):
    results = dict()
    for lang, compiler in tqdm.tqdm(LANG_CLUSTER_TO_LANG_COMPILER.items()):
        eval_file = os.path.join(eval_dir, f"{compiler}.jsonl")
        with jsonlines.open(eval_file) as jrp:
            for sample in jrp:
                bug_code_uid = sample["source_data"]["bug_code_uid"]
                if bug_code_uid not in results:
                    results[bug_code_uid] = 0
                ut_res = sample["unit_test_results"][0]
                if all(x["exec_outcome"] == "PASSED" for x in ut_res):
                    results[bug_code_uid] += 1
    unfixed = {id: num for id, num in results.items() if num <= unfixed_k}
    return unfixed


def save_unfixed(unfixed, output_dir):
    output_file = os.path.join(output_dir, "unfixed.json")
    with open(output_file, 'w') as f:
        json.dump(unfixed, f)


def run(base_dir, it, unfixed_k):
    if it < 1:
        raise Exception("The iteration number cannot be less than 1!")

    iter_dir = initilize_iter(base_dir, it)
    if it == 1:
        eval_dir = os.path.join(base_dir, "eval_apr_val_execeval")
    else:
        eval_dir = os.path.join(base_dir, f"iter_{it - 1}/eval")
    unfixed = filter_unfixed(eval_dir, unfixed_k)
    save_unfixed(unfixed, iter_dir)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-dir",
        default="dumped/oai/apr_n_sample_20",
        help="Path to the trans-repair base directory.",
    )
    parser.add_argument(
    "--it",
    type=int,
    default=1,
    help="Current iteration epoch of trans-repair.",
    )
    parser.add_argument(
    "--unfixed_k",
    type=int,
    default=0,
    help="Maximal number of successful samples of an unfixed bug.",
    )
    args = parser.parse_args()

    run(args.base_dir, args.it, args.unfixed_k)
    