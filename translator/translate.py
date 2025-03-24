import os
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
from middleware.retrieval import build_target_db
from middleware.history import get_last_incorrect_samples, cp_last_incorrect_samples
from middleware import prompt
import shutil

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



def gen(prompt, temperature, nsample):
    cnt = 0
    while True:
        if cnt == 999:
            return None
        try:
            c = openai.ChatCompletion.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": f"{prompt}"},
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
    c["prompt"] = prompt
    return c

def gen_request(prompt, temperature, nsample):
    url = "<url>"

    payload = {
        "model": "<model_name>",
        "messages": [
            {
                "role": "user",
                "content": f"{prompt}"
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
            print(f"Gen Error:{e}")

    
    res['prompt'] = prompt

    return res



def process_prompt(dt, temperature, trans_dir, target_lang, index, r_mode, dry_run=0):
    dt["source_lang"] = dt["lang_cluster"]
    dt["target_lang"] = target_lang
    language = f"{dt['source_lang']}--{dt['target_lang']}"
    file_path = os.path.join(trans_dir, f"{index}_{temperature}_{language}.json")
    if not os.path.exists(file_path):
        if r_mode != "ultimate2":
            dt["prob_desc_sample_inputs"] = json.loads(dt["prob_desc_sample_inputs"])
            dt["prob_desc_sample_outputs"] = json.loads(dt["prob_desc_sample_outputs"])
        lm_io = prompt.trans(dt)
        assert len(lm_io) == 2, f"{json.dumps(lm_io, indent=4)}"
        if dry_run:
            open(file_path, "w").write(f"{json.dumps(lm_io[0], indent=4)}")
        else:
            out = gen(lm_io[0], temperature, 1)
            # out = gen_request(lm_io[0], temperature, 1)
            export_data = {"oai_response": out, "source_data": dt}
            open(file_path, "w").write(f"{json.dumps(export_data, indent=4)}")


def run(base_dir, num_proc, dry_run, it, mode, r_mode, dataset_path, config_path=""):
    iter_dir = os.path.join(base_dir, f"iter_{it}")
    unfixed_file = os.path.join(iter_dir, "unfixed.json")
    if os.path.exists(unfixed_file):
        with open(unfixed_file, 'r') as f:
            data = json.load(f)
            unfixed_ids = list(data.keys())
    else:
        raise Exception("The intermediate file unfixed.json does not exist!")
    
    trans_dir = os.path.join(iter_dir, f"trans")
    if not os.path.exists(trans_dir):
        os.makedirs(trans_dir, exist_ok=True)

    # for chatrepair
    if mode == "copy":
        print('copying...')
        cp_last_incorrect_samples(base_dir, it, unfixed_ids)
        return

    decision = TransDecision(base_dir, it, config_path)

    if mode in ["reasoning", "nohist", "nocot"]:
        build_target_db(base_dir, it)


    apr_dataset = datasets.load_from_disk(dataset_path)

    
    if r_mode == "ultimate2":
        unfixed_dataset = get_last_incorrect_samples(base_dir, it, unfixed_ids)
    else:
        unfixed_dataset = apr_dataset.filter(lambda x: x['bug_code_uid'] in unfixed_ids)
    # temperature_list = np.linspace(0, 2, args.nsample)
    temperature_list = [0.3157894736842105]
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=int(num_proc)
    ) as executor:
        futures = []
        for idx, dt in tqdm.tqdm(
            enumerate(unfixed_dataset),
            total=len(unfixed_dataset),
            desc=f"Preparing samples lang",
        ):
            target_lang = decision.decide_lang(dt, it, mode)
            for temperature in temperature_list:
                future = executor.submit(
                    process_prompt,
                    dt,
                    temperature,
                    trans_dir,
                    target_lang,
                    idx,
                    r_mode,
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
        "--r_mode",
        default="vanilla",
        help="Repair mode.",
    )
    args = parser.parse_args()
    run(args.base_dir, args.num_proc, args.dry_run, args.it, args.mode, args.r_mode)
