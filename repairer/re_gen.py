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
from middleware.repair_retrieval import add_hist, construct_conversation
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


def gen(prompt_text, temperature, nsample, mode, msg=None):
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
                temperature=temperature,
                top_p=1,
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

def gen_request(prompt_text, temperature, nsample, mode, msg=None):
    url = "<url>"
    messages = [
                {"role": "system", "content": f"{prompt.PROMPTS['system']}"},
                {"role": "user", "content": f"{prompt_text}"},
            ]

    payload = {
        "model": "<model_name>",
        "messages": messages,
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

    
    res["prompt"] = prompt_text

    return res




def process_prompt(dt, temperature, nsample, output_dir, index, attempt, mode, msg=None, dry_run=0):
    language = dt["lang_cluster"]
    if mode == "ultimate2":
        uid = dt["bug_code_uid"]
        file_path = os.path.join(output_dir, f"{index}_{uid}_{temperature}_{language}.json")
    else:
        file_path = os.path.join(output_dir, f"{index}_{attempt}_{temperature}_{language}.json")
    if mode == "ultimate":
        s_prompt = f"You are an expert program repair system. You should carefully analyze problem descriptions and input/output specifications. You should reflect on previous failed repair attempts (the input, expected output, actual result and execution outcome of the test). You should make the analysis step by step. The output should be in json format."
    elif mode == "ultimate2":
        s_prompt = "You are an expert program repair system. You should carefully analyze problem descriptions and input/output specifications. The buggy code that cannot be fixed will be translated to other programming languages for you to fix at each iteration. You should reflect on previous failed tests and provide the fixed code with the experience from historical failures."
        if msg[0]["role"] != "system":
            system_msg = {"role": "system", "content": s_prompt}
            msg.insert(0, system_msg)
    else:
        s_prompt = None
    if not os.path.exists(file_path):
        # dt["prob_desc_sample_inputs"] = json.loads(dt["prob_desc_sample_inputs"])
        # dt["prob_desc_sample_outputs"] = json.loads(dt["prob_desc_sample_outputs"])
        lm_io = prompt.apr(dt)
        assert len(lm_io) == 2, f"{json.dumps(lm_io, indent=4)}"
        if dry_run:
            open(file_path, "w").write(f"{json.dumps(lm_io[0], indent=4)}")
        else:
            out = gen(lm_io[0], temperature, nsample, mode, msg)
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


def run(base_dir, num_proc, dry_run, nsample, nattempt, it, mode, temperature, dataset_path):
    
    iter_dir = os.path.join(base_dir, f"iter_{it}")
    re_gen_dir = os.path.join(iter_dir, f"repair")
    if not os.path.exists(re_gen_dir):
        os.makedirs(re_gen_dir, exist_ok=True)

    unfixed_path = os.path.join(iter_dir, "unfixed.json")
    with open(unfixed_path, "r") as uf:
        unfixed_ids = json.load(uf).keys()

    if mode not in ["cmp"]:
        transed_dir = os.path.join(iter_dir, "trans")
        transed_dataset = load_json_files(transed_dir)
    elif mode == 'cmp':
        apr_dataset = datasets.load_from_disk(dataset_path)
        transed_dataset = apr_dataset.filter(lambda x: x["bug_code_uid"] in unfixed_ids)
    # elif mode == 'ultimate2':
    #     transed_dataset = get_last_incorrect_samples_cr(base_dir, it, unfixed_ids)

    if mode == "ultimate2":
        last_repair = load_last_repair(base_dir, it)
        last_tests = load_last_tests(base_dir, it)

    # temperature_list = np.linspace(0, 2, args.nsample)
    temperature_list = [temperature]
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=int(num_proc)
    ) as executor:
        futures = []
        for idx, dt in tqdm.tqdm(
            enumerate(transed_dataset),
            total=len(transed_dataset),
            desc=f"Preparing samples lang",
        ):
            if mode == "ultimate":
                dt = add_hist(base_dir, dt, it)
            msg = None
            if mode == "ultimate2":
                msg = construct_conversation(base_dir, it, dt, last_repair, last_tests)
                # with open("/root/TR/test/msg.txt", "a") as msg_file:
                #     msg_file.write(str(msg))
                nattempt = 1
            for attempt in range(nattempt):
                for temperature in temperature_list:
                    future = executor.submit(
                        process_prompt,
                        dt,
                        temperature,
                        nsample,
                        re_gen_dir,
                        idx,
                        attempt,
                        mode,
                        msg,
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
        "--it",
        default=1,
        type=int,
        help="Current iteration epoch of trans-repair.",
    )
    parser.add_argument(
        "--mode",
        default="vanilla",
        help="Repair mode.",
    )
    parser.add_argument(
    "--temperature",
    type=float,
    default=1.0,
    help="Set the temperature for the language model."
    )
    args = parser.parse_args()

    run(args.base_dir, args.num_proc, args.dry_run, args.nsample, args.attempt, args.it, args.mode, args.temperature)
