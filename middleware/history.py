import os
import json
import argparse
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import jsonlines

'''
record the history of the current iteration after it is done.
'''
TRANS_PROPERTIES = ["target_lang"]

def sanitize_code(code):
    prefixes = ["csharp", "cpp", "go", "javascript", "kotlin", "php", "python", "ruby", "rust", "c", "java", "json"]
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

def init_history(data, id, it):
    if id not in data:
        data[id] = dict()
    new_iter = f"iter_{it}"
    if new_iter not in data[id]:
        data[id][new_iter] = dict()
    return data

def new_history(data, id, it, sample, properties):
    for p in properties:
        data[id][f"iter_{it}"][p] = sample["source_data"][p]
    return data

def extract_history(dir, it, data, properties):
    for filename in os.listdir(dir):
        if filename.endswith('.json'):
            file_path = os.path.join(dir, filename)
            try:
                with open(file_path, 'r') as f:
                    sample = json.load(f)
                    id = sample["source_data"]["bug_code_uid"]
                    data = init_history(data, id, it)
                    data = new_history(data, id, it, sample, properties)
            except Exception as e:
                print(f"Error reading {filename}: {str(e)}")
    return data

def get_historical_chain(base_dir, id, it, property):
    history_path = os.path.join(base_dir, "history/history.json")
    if not os.path.exists(history_path):
        return []
    with open(history_path, "r") as file:
        data = json.load(file)
    historical_chain = []
    for i in range(1, it):
        if f"iter_{i}" not in data[id]:
            break
        historical_chain.append(data[id][f"iter_{i}"][property])
    return historical_chain

def analyze_unit_test_distribution(base_dir: str, it: int) -> Dict[str, Dict[str, dict]]:
    if it == 0:
        directory_path = os.path.join(base_dir, "eval_apr_val_execeval")
    else:
        directory_path = os.path.join(base_dir, f"iter_{it}", "eval")
    distributions = defaultdict(lambda: {"it": it, "patterns": defaultdict(dict)})
    
    for filename in os.listdir(directory_path):
        if filename.endswith('.jsonl'):
            filepath = os.path.join(directory_path, filename)
            
            with open(filepath, 'r', encoding='utf-8') as file:
                for line in file:
                    try:
                        data = json.loads(line.strip())
                        bug_code_uid = data['source_data']['bug_code_uid']
                        bug_source_code = data['oai_response']['choices'][0]["message"]["content"]
                        unit_tests = data['unit_test_results'][0]
                        
                        # Filter out PASSED tests
                        failed_tests = [
                            test for test in unit_tests 
                            if test['exec_outcome'] != "PASSED"
                        ]
                        
                        # Skip if no failed tests
                        if not failed_tests:
                            continue
                            
                        # Create signature only for failed tests
                        test_signature = []
                        test_details = []
                        for test in failed_tests:
                            exec_outcome = test['exec_outcome']
                            has_result = test['result'] is not None
                            has_memory = test['peak_memory_consumed'] is not None
                            has_time = test['time_consumed'] is not None
                            
                            signature = (
                                str(exec_outcome),
                                str(has_result),
                                str(has_memory),
                                str(has_time)
                            )
                            test_signature.append(signature)
                            
                            # Store detailed test information only for non-null exec_outcome
                            if test['exec_outcome'] is not None:
                                test_detail = {
                                    'exec_outcome': test['exec_outcome'],
                                    'input': test['input'],
                                    'output': test['output'],
                                    'result': test['result']
                                }
                                test_details.append(test_detail)
                        
                        test_signature = tuple(test_signature)
                        
                        # If this signature pattern hasn't been seen before
                        if 'count' not in distributions[bug_code_uid]['patterns'][test_signature]:
                            distributions[bug_code_uid]['patterns'][test_signature] = {
                                'count': 0,
                                'bug_source_codes': [],
                                'test_details': []
                            }
                        
                        distributions[bug_code_uid]['patterns'][test_signature]['count'] += 1
                        if bug_source_code not in distributions[bug_code_uid]['patterns'][test_signature]['bug_source_codes']:
                            distributions[bug_code_uid]['patterns'][test_signature]['bug_source_codes'].append(bug_source_code)
                        if test_details:  # Only append if there are non-null test details
                            distributions[bug_code_uid]['patterns'][test_signature]['test_details'].append(test_details)
                        
                        if it == 0:
                            distributions[bug_code_uid]["lang"] = data['source_data']["lang_cluster"]
                        else:
                            distributions[bug_code_uid]["lang"] = data['source_data']["target_lang"]
                        
                    except json.JSONDecodeError:
                        print(f"Skipping invalid JSON line in {filename}")
                    except Exception as e:
                        print(f"Error processing line in {filename}: {str(e)}")
    
    return distributions

def save_distributions(distributions: Dict[str, Dict[str, dict]], output_file: str):
    # Load existing data if file exists
    existing_data = {}
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse existing file {output_file}. Starting fresh.")
    
    # Merge new data with existing data
    json_output = existing_data.copy()
    for bug_code_uid, data in distributions.items():
        if bug_code_uid not in json_output:
            json_output[bug_code_uid] = {}
        
        # Add new iteration data
        json_output[bug_code_uid][f'it_{data["it"]}'] = {
            'patterns': {
                str(pattern): {
                    'count': pattern_data['count'],
                    'bug_source_codes': pattern_data['bug_source_codes'],
                    'test_details': pattern_data['test_details']
                }
                for pattern, pattern_data in data['patterns'].items()
            },
            'lang': data["lang"]
        }
    
    # Save merged data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_output, f, indent=2)

def get_last_incorrect_samples(base_dir, it, unfixed_ids):
    unfixed_dataset = []
    if it == 1:
        last_repair_dir = os.path.join(base_dir, "repair")
    else:
        last_repair_dir = os.path.join(base_dir, f"iter_{it - 1}/back_trans")
    for filename in os.listdir(last_repair_dir):
        sample_path = os.path.join(last_repair_dir, filename)
        with open(sample_path, "r") as f:
            sample = json.load(f)
            if sample["source_data"]["bug_code_uid"] in unfixed_ids:
                unfixed_sample = sample["source_data"]
                unfixed_sample["bug_source_code"] = sanitize_code(sample["oai_response"]["choices"][0]["message"]["content"])
                if it == 1:
                    unfixed_sample["oai_id"] = sample["oai_response"]["id"]
                unfixed_dataset.append(unfixed_sample)
    return unfixed_dataset

def get_last_incorrect_samples_cr(base_dir, it, unfixed_ids):
    unfixed_dataset = []
    if it == 1:
        last_repair_dir = os.path.join(base_dir, "repair")
    else:
        last_repair_dir = os.path.join(base_dir, f"iter_{it - 1}/repair")
    for filename in os.listdir(last_repair_dir):
        sample_path = os.path.join(last_repair_dir, filename)
        with open(sample_path, "r") as f:
            sample = json.load(f)
            if sample["source_data"]["bug_code_uid"] in unfixed_ids:
                unfixed_sample = sample["source_data"]
                unfixed_sample["bug_source_code"] = sanitize_code(sample["oai_response"]["choices"][0]["message"]["content"])
                if it == 1:
                    unfixed_sample["oai_id"] = sample["oai_response"]["id"]
                unfixed_dataset.append(unfixed_sample)
    return unfixed_dataset

def cp_last_incorrect_samples(base_dir, it, unfixed_ids):
    # Source and destination directories
    if it == 1:
        source_dir = f"{base_dir}/repair"
    else:
        source_dir = f"{base_dir}/iter_{it - 1}/back_trans"

    destination_dir = f"{base_dir}/iter_{it}/trans"

    # Iterate over all files in the source directory
    for filename in os.listdir(source_dir):
        full_file_name = os.path.join(source_dir, filename)
        with open(full_file_name, "r") as f:
            sample = json.load(f)
            if sample["source_data"]["bug_code_uid"] in unfixed_ids:
                if os.path.isfile(full_file_name):
                    sample_path = os.path.join(destination_dir, filename)
                    if it == 1:
                        sample["source_data"]["oai_id"] = sample["oai_response"]["id"]
                        sample["source_data"]["source_lang"] = sample["source_data"]["lang_cluster"]
                        sample["source_data"]["target_lang"] = sample["source_data"]["lang_cluster"]
                    with open(sample_path, "w") as file:
                        json.dump(sample, file)

def load_last_repair(base_dir, it):
    last_repair = dict()
    if it == 1:
        last_repair_dir = os.path.join(base_dir, "repair")
    else:
        last_repair_dir = os.path.join(base_dir, f"iter_{it - 1}/repair")
    for filename in os.listdir(last_repair_dir):
        file_path = os.path.join(last_repair_dir, filename)
        with open(file_path, "r") as f:
            sample = json.load(f)
            if it == 1:
                last_repair[sample["oai_response"]["id"]] = {"msg": sample["oai_response"]["prompt"], "res": sample["oai_response"]["choices"][0]["message"]["content"]}
            else:
                last_repair[sample["source_data"]["oai_id"]] = {"msg": sample["oai_response"]["conversation"], "res": sample["oai_response"]["choices"][0]["message"]["content"]}
    return last_repair

def load_last_tests(base_dir, it):
    last_tests = dict()
    if it == 1:
        last_eval_dir = os.path.join(base_dir, "eval_apr_val_execeval")
    else:
        last_eval_dir = os.path.join(base_dir, f"iter_{it - 1}/eval")
    for filename in os.listdir(last_eval_dir):
        file_path = os.path.join(last_eval_dir, filename)
        with jsonlines.open(file_path) as jrp:
            for sample in jrp:
                if it == 1:
                    oai_id = sample["oai_response"]["id"]
                else:
                    oai_id = sample["source_data"]["oai_id"]
                last_tests[oai_id] = sample["unit_test_results"][0]
    return last_tests


def build_history(base_dir, it):
    history_dir = os.path.join(base_dir, "history")
    os.makedirs(history_dir, exist_ok=True)
    if it:
        history_path = os.path.join(history_dir, "history.json")
        if os.path.exists(history_path):
            with open(history_path, "r") as file:
                data = json.load(file)
        else:
            data = dict()
        
        # translation history
        iter_dir = os.path.join(base_dir, f"iter_{it}")
        trans_dir = os.path.join(iter_dir, "trans")
        data = extract_history(trans_dir, it, data, TRANS_PROPERTIES)

        with open(history_path, "w") as file:
            json.dump(data, file, indent=4)
    
    # repair history
    output_file = os.path.join(base_dir, "history/repair_history.json")
    distributions = analyze_unit_test_distribution(base_dir, it)
    save_distributions(distributions, output_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-dir",
        default="dumped/oai/apr_n_sample_20",
        help="Path to the trans-repair base directory.",
    )
    parser.add_argument(
        "--it",
        default=1,
        type=int,
        help="Current iteration epoch of trans-repair.",
    )
    args = parser.parse_args()

    build_history(args.base_dir, args.it)