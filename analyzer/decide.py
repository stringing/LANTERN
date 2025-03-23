import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Adjust if needed
sys.path.append(project_root)
import time
import tqdm
import json
import openai
import requests
# from openai import OpenAI
import argparse
import datasets
import concurrent
import numpy as np
from promptsource.templates import Template
from analyzer.decision import TransDecision
from middleware import retrieval
from middleware import prompt

SHORT_LANG_MAP = {
    "GNU C++": "C++",
    "GNU C++17": "C++",
    "MS C++ 2017": "C++",
    "MS C++": "C++",
    "Java 8": "Java",
    "Java 6": "Java",
    "GNU C++11": "C++",
    "Java 11": "Java",
    "GNU C++14": "C++",
    "Mono C#": "C#",
    "GNU C": "C",
    "Python 3": "Python",
    "PyPy 3": "Python",
    "GNU C11": "C",
    "Go": "Go",
    "Rust": "Rust",
    "PyPy 2": "Python",
    "Python 2": "Python",
    "MS C#": "C#",
    "Kotlin": "Kotlin",
    "GNU C++0x": "C++",
    "Java 7": "Java",
    "Node.js": "Javascript",
    ".NET Core C#": "C#",
    "PHP": "PHP",
    "GNU C++17 Diagnostics": "C++",
    "Clang++17 Diagnostics": "C++",
    "JavaScript": "Javascript",
    "Ruby": "Ruby",
    "C# 10": "C#",
    "C# 8": "C#",
    "Clang++20 Diagnostics": "C++",
    "GNU C++17 (64)": "C++",
    "GNU C++20 (64)": "C++",
    "Java 17": "Java",
    "Kotlin 1.4": "Kotlin",
    "Kotlin 1.5": "Kotlin",
    "Kotlin 1.6": "Kotlin",
    "Kotlin 1.7": "Kotlin",
    "PyPy 3-64": "Python",
    "Python 3 + libs": "Python",
    "Ruby 3": "Ruby",
    "Rust 2021": "Rust",
}

LANGS = sorted(set([v for k, v in SHORT_LANG_MAP.items()]))


openai.api_key = os.environ["API_KEY"]
openai.api_base = os.environ["API_BASE"]
model_name = os.environ["MODEL_NAME"]



def gen(prompt_text, temperature, nsample):
    cnt = 0
    while True:
        if cnt == 999:
            return None
        try:
            c = openai.ChatCompletion.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": f"{prompt.PROMPTS['system']}"},
                    {"role": "user", "content": f"{prompt_text}"},
                ],
                temperature=temperature,
                top_p=1,
                n=nsample,
                do_sample=True,
                frequency_penalty=0.0,
                presence_penalty=0.0,
            )
            print('get openai response......')
            break
        except Exception as e:
            cnt += 1
            time.sleep(5)
            print(f"{e}")
    c["prompt"] = prompt_text
    return c

def gen_request(prompt_text, temperature, nsample):
    url = "<url>"

    payload = {
        "model": "<model_name>",
        "messages": [
            {"role": "system", "content": f"{prompt.PROMPTS['system']}"},
            {
                "role": "user",
                "content": f"{prompt_text}"
            }
        ],
        "max_tokens": 4096,
        "stop": ["null"],
        "temperature": temperature,
        "top_p": 1,
        "do_sample": True,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "n": nsample,
        "response_format": {"type": "text"},
    }
    headers = {
        "Authorization": "Bearer <header key>",
        "Content-Type": "application/json"
    }

    cnt = 0

    while True:
        if cnt == 999:
            return None
        try:
            response = requests.request("POST", url, json=payload, headers=headers)
            res = json.loads(response.text)
            if 'data' in res.keys() and res['data'] is None:
                print(res['message'])
                time.sleep(5)
            else:
                print('get request response......')
                break
        except Exception as e:
            cnt += 1
            time.sleep(5)
            print(f"{e}")

    
    res['prompt'] = prompt_text

    return res



def process_prompt(dt, bug_retrieval, temperature, mode, dec_dir, index, dry_run=0):
    file_path = os.path.join(dec_dir, f"{index}_{temperature}_{dt['lang_cluster']}.json")
    if not os.path.exists(file_path):
        dt["prob_desc_sample_inputs"] = json.loads(dt["prob_desc_sample_inputs"])
        dt["prob_desc_sample_outputs"] = json.loads(dt["prob_desc_sample_outputs"])
        if mode == 'nohist':
            lm_io = prompt.nohist(bug_retrieval)
        else:
            lm_io = prompt.decision(bug_retrieval)
        assert len(lm_io) == 2, f"{json.dumps(lm_io, indent=4)}"
        if dry_run:
            open(file_path, "w").write(f"{json.dumps(lm_io[0], indent=4)}")
        else:
            out = gen(lm_io[0], temperature, 1)
            # out = gen_request(lm_io[0], temperature, 1)
            export_data = {"oai_response": out, "source_data": dt}
            open(file_path, "w").write(f"{json.dumps(export_data, indent=4)}")


def run(base_dir, num_proc, dry_run, it, mode, hist_top_k, dataset_path):
    iter_dir = os.path.join(base_dir, f"iter_{it}")
    dec_dir = os.path.join(iter_dir, f"decide")
    if not os.path.exists(dec_dir):
        os.makedirs(dec_dir, exist_ok=True)

    apr_dataset = datasets.load_from_disk(dataset_path)

    unfixed_file = os.path.join(iter_dir, "unfixed.json")
    if os.path.exists(unfixed_file):
        with open(unfixed_file, 'r') as f:
            data = json.load(f)
            unfixed_ids = list(data.keys())
    else:
        raise Exception("The intermediate file unfixed.json does not exist!")

    unfixed_dataset = apr_dataset.filter(lambda x: x['bug_code_uid'] in unfixed_ids)
    # temperature_list = np.linspace(0, 2, args.nsample)
    temperature_list = [0.3157894736842105]

    retrieval.init_vec_db(base_dir, dataset_path)
    retrieval.init_cos_similarity(base_dir)
    bug_properties, cos = retrieval.prepare_db(base_dir, apr_dataset)
    retrieval.update_pass_10(base_dir, it)
    
    decision_path = os.path.join(base_dir, f"iter_{it}/decision.json")
    decision_exist = os.path.exists(decision_path)
    if decision_exist:
        with open(decision_path, "r") as decision_file:
            decision_data = json.load(decision_file)
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=int(num_proc)
    ) as executor:
        futures = []
        for idx, dt in tqdm.tqdm(
            enumerate(unfixed_dataset),
            total=len(unfixed_dataset),
            desc=f"Preparing samples lang",
        ):
            for temperature in temperature_list:
                if decision_exist:
                    uid = dt["bug_code_uid"]
                    if uid in decision_data:
                        continue
                if mode == 'nohist':
                    bug_retrieval = retrieval.retrieve(base_dir, it, dt["bug_code_uid"], hist_top_k, bug_properties, cos, nohist=True)
                else:
                    bug_retrieval = retrieval.retrieve(base_dir, it, dt["bug_code_uid"], hist_top_k, bug_properties, cos)
                future = executor.submit(
                    process_prompt,
                    dt,
                    bug_retrieval,
                    temperature,
                    mode,
                    dec_dir,
                    idx,
                    dry_run,
                )
                futures.append(future)

        for future in tqdm.tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc=f"Calling OpenAI API",
        ):
            try:
                future.result()
            except Exception as e:
                print(f"Error occurred: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-dir",
        default="dumped/oai/apr_n_sample_20",
        help="Path to the trans-repair base directory.",
    )
    parser.add_argument(
        "--num-proc",
        default=1,
        help="Number of parallel API request.",
    )
    parser.add_argument(
        "--dry-run",
        default=0,
        help="Number of parallel API request.",
    )
    parser.add_argument(
        "--it",
        default=1,
        type=int,
        help="Current iteration epoch of trans-repair.",
    )
    parser.add_argument(
        "--mode",
        default="vanilla",
        help="Translation mode.",
    )
    parser.add_argument(
        "--hist_top_k",
        default=15,
        type=int,
        help="Top K historical data.",
    )
    parser.add_argument(
        "--dataset_path",
        default="/root/my/data/xCodeEval/apr",
        help="APR dataset path.",
    )
    args = parser.parse_args()
    run(args.base_dir, args.num_proc, args.dry_run, args.it, args.hist_top_k, args.dataset_path)
