import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Adjust if needed
sys.path.append(os.path.dirname(project_root))
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
from middleware.repair_retrieval import add_hist, construct_conversation, add_hist_testfailure
from middleware.history import load_last_repair, load_last_tests, get_last_incorrect_samples_cr
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


def gen(prompt_text, nsample):
    cnt = 0
    messages = [
                    {"role": "system", "content": f"{prompt.PROMPTS['system']}"},
                    {"role": "user", "content": f"{prompt_text}"},
                ]
    while True:
        if cnt == 999:
            return None
        try:
            c = openai.ChatCompletion.create(
                model=model_name,
                messages=messages,
                temperature=0.8,
                top_p=0.95,
                n=nsample,
                do_sample=True,
                frequency_penalty=0.0,
                presence_penalty=0.0,
            )
            break
        except Exception as e:
            cnt += 1
            time.sleep(5)
            print(f"{e}")
    
    c["prompt"] = prompt_text
    return c




def process_prompt(dt, nsample, output_dir, index, attempt, dry_run=0):
    language = dt["lang_cluster"]
    uid = dt["bug_code_uid"]
    file_path = os.path.join(output_dir, f"{index}_{attempt}_{uid}_{language}.json")

    if not os.path.exists(file_path):
        lm_io = prompt.plan(dt)
        assert len(lm_io) == 2, f"{json.dumps(lm_io, indent=4)}"
        if dry_run:
            open(file_path, "w").write(f"{json.dumps(lm_io[0], indent=4)}")
        else:
            out = gen(lm_io[0], nsample)
            # out = gen_request(s_prompt, lm_io[0], temperature, nsample, mode, msg)
            export_data = {"oai_response": out, "source_data": dt}
            open(file_path, "w").write(f"{json.dumps(export_data, indent=4)}")

def sanitize_code(code):
    prefixes = ["csharp", "cpp", "go", "javascript", "kotlin", "php", "python", "ruby", "rust", "c", "java"]
    FLAG = True
    while FLAG == True:
        FLAG = False
        if code.startswith("```"):
            FLAG = True
            code = code.replace("```", "", 1)
        last_index = code.rfind("```")
        if last_index != -1:
            FLAG = True
            code = code[:last_index] + "" + code[last_index + len("```") :]
        for prefix in prefixes:
            if code.startswith(prefix):
                FLAG = True
                code = code.replace(prefix, "", 1)
                break
    return code

def load_json_files(dir):
    json_files = []
    files = os.listdir(dir)
    files.sort()
    for filename in files:
        if filename.endswith('.json'):
            file_path = os.path.join(dir, filename)
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    dt = data["source_data"]
                    code = data["oai_response"]["choices"][0]["message"]["content"]
                    code = sanitize_code(code)
                    dt["bug_source_code"] = code
                    dt["lang_cluster"] = dt["target_lang"]
                    json_files.append(dt)
            except Exception as e:
                print(f"Error reading {filename}: {str(e)}")
    return json_files


def run(base_dir, num_proc, dry_run, nsample, nattempt, dataset_path):
    
    plan_dir = os.path.join(base_dir, f"plans")
    if not os.path.exists(plan_dir):
        os.makedirs(plan_dir, exist_ok=True)


    apr_dataset = datasets.load_from_disk(dataset_path)

    with concurrent.futures.ProcessPoolExecutor(
        max_workers=int(num_proc)
    ) as executor:
        futures = []
        for idx, dt in tqdm.tqdm(
            enumerate(apr_dataset),
            total=len(apr_dataset),
            desc=f"Preparing samples lang",
        ):
            for attempt in range(nattempt):
                future = executor.submit(
                    process_prompt,
                    dt,
                    nsample,
                    plan_dir,
                    idx,
                    attempt,
                    dry_run
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
        "--nsample",
        default=1,
        type=int,
        help="Number of parallel API request.",
    )
    # deepseek only allows nsample=1 currently, use this as the number of repetitive generation for each problem
    parser.add_argument(
        "--nattempt",
        default=20,
        type=int,
        help="Number of attempts of generation for each problem.",
    )
    parser.add_argument(
        "--dataset-path",
        default="/root/my/data/xCodeEval/apr",
        help="APR dataset path.",
    )
    args = parser.parse_args()

    run(args.base_dir, args.num_proc, args.dry_run, args.nsample, args.nattempt, args.dataset_path)
