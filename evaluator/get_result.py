import os
from collections import defaultdict
import tqdm
import jsonlines
import json
from typing import List, Union
import itertools
import numpy as np
import argparse
import time

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


def estimate_pass_at_k(
    num_samples: Union[int, List[int], np.ndarray],
    num_correct: Union[List[int], np.ndarray],
    k: int,
) -> np.ndarray:
    """
    Estimates pass@k of each problem and returns them in an array.
    """

    def estimator(n: int, c: int, k: int):
        """
        Calculates 1 - comb(n - c, k) / comb(n, k).
        """
        if n - c < k:
            return 1.0
        return 1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1))

    if isinstance(num_samples, int):
        num_samples_it = itertools.repeat(num_samples, len(num_correct))
    else:
        assert len(num_samples) == len(num_correct)
        num_samples_it = iter(num_samples)

    return np.array(
        [estimator(int(n), int(c), k) for n, c in zip(num_samples_it, num_correct)]
    )

def get_execeval_out_file_name(output_path, compiler):
    return os.path.join(output_path, f"{compiler}.jsonl")

def get_iter_out_file_name(path, compiler, i):
    iter_dir = os.path.join(path, f"iter_{i + 1}")
    return os.path.join(iter_dir, f"eval/{compiler}.jsonl")


def group_results(results, k):
    '''
    This function is temporarily used to group every k elements in the "total" and "correct" arrays for pass@k calculation, 
    due to the reason that DeepSeekCoder 2.5 only allows for response of n=1 rather than n=k currently, which results in 
    only one choice element in the "oai_response".
    '''
    assert len(results) % k == 0, "Length error: the length of the array must be the multiple of k! Results may not be complete?"
    reshaped = results.reshape(-1, k)
    results = np.sum(reshaped, axis=1)
    return results

def estimate_top_at_K(results, k, tk):
    '''
    Calculates Top@k.
    '''
    assert len(results) % k == 0, "Length error: the length of the array must be the multiple of k! Results may not be complete?"
    num_sample = len(results) / k
    top_correct = 0
    for i in range(0, len(results), k):
        top_correct += any(results[i:i + tk])
    return top_correct / num_sample


def __run(base_dir, k, it, name, note):
    output_dir = os.path.join(base_dir, "cal_results")
    path = base_dir
    output_path = os.path.join(path, "eval_apr_val_execeval")
    unfixed_ids_list = []
    if it:
        for i in range(it):
            iter_dir = os.path.join(path, f"iter_{i + 1}")
            unfixed_file = os.path.join(iter_dir, "unfixed.json")
            if os.path.exists(unfixed_file):
                with open(unfixed_file, 'r') as f:
                    data = json.load(f)
                    unfixed_ids = data
                    unfixed_ids_list.append(unfixed_ids)
            else:
                raise Exception("The intermediate file unfixed.json does not exist!")
        

    ks = range(1, k + 1)
    # construct result as {[task_id]: [unit_test_results]}
    # task_id will be src_uid_lang

    pass_at_k = defaultdict(dict)
    # top_at_k = defaultdict(dict)

    sample_num_rec = dict()

    for lang, compiler in tqdm.tqdm(LANG_CLUSTER_TO_LANG_COMPILER.items()):
        execeval_out_file = get_execeval_out_file_name(output_path, compiler)
        results = defaultdict(list)
        with jsonlines.open(execeval_out_file) as jrp:
            for sample in jrp:
                if it and sample["source_data"]["bug_code_uid"] in unfixed_ids_list[0]:
                    continue
                src_uid = sample["source_data"]["src_uid"]
                task_id = f"{src_uid}|||{lang}"
                for ut_res in sample["unit_test_results"]:
                    if "error" in ut_res:
                        continue
                    results[task_id].append(ut_res)
        
        for i in range(it):
            iter_out_file = get_iter_out_file_name(path, compiler, i)
            with jsonlines.open(iter_out_file) as jrp:
                for sample in jrp:
                    bug_uid = sample["source_data"]["bug_code_uid"]
                    if bug_uid not in sample_num_rec:
                        sample_num_rec[bug_uid] = {"max_success": unfixed_ids_list[i][bug_uid], "results": sample["unit_test_results"]}
                    if i != it - 1: # if not the final iteration, wait and see
                        pass
                    else: # if it is the final iteration, must calculate anyway
                        src_uid = sample["source_data"]["src_uid"]
                        task_id = f"{src_uid}|||{lang}"
                        for ut_res in sample["unit_test_results"]:
                            if "error" in ut_res:
                                continue
                            results[task_id].append(ut_res)
                    # if i != it - 1 and bug_uid in unfixed_ids_list[i + 1]:
                    #     if unfixed_ids_list[i][bug_uid] > sample_num_rec[bug_uid]["max_success"]:
                    #         sample_num_rec[bug_uid]["max_success"] = unfixed_ids_list[i][bug_uid]
                    #         sample_num_rec[bug_uid]["results"] = sample["unit_test_results"]
                    #     continue
                    # src_uid = sample["source_data"]["src_uid"]
                    # task_id = f"{src_uid}|||{lang}"
                    # if i != it - 1:
                    #     for ut_res in sample["unit_test_results"]:
                    #         if "error" in ut_res:
                    #             continue
                    #         results[task_id].append(ut_res)
                    # else:
                    #     if unfixed_ids_list[i][bug_uid] > sample_num_rec[bug_uid]["max_success"]:
                    #         for ut_res in sample["unit_test_results"]:
                    #             if "error" in ut_res:
                    #                 continue
                    #             results[task_id].append(ut_res)
                    #     else:
                    #         for ut_res in sample_num_rec[bug_uid]["results"]:
                    #             if "error" in ut_res:
                    #                 continue
                    #             results[task_id].append(ut_res)
        
        total, correct = [], []
        for result in results.values():
            passed = [
                all(x["exec_outcome"] == "PASSED" for x in ut_res) for ut_res in result
            ]
            total.append(len(passed))
            correct.append(sum(passed))
        total = np.array(total)
        correct = np.array(correct)
        
        # top_ks = [1, 5, 10, 15]
        # top_at_k[lang] = {
        #     f"top@{tk}": estimate_top_at_K(correct, args.k, tk)
        #     for tk in top_ks
        # }

        # total = group_results(total, args.k)
        # correct = group_results(correct, args.k)

        pass_at_k[lang] = {
            f"pass@{k}": estimate_pass_at_k(total, correct, k).mean()
            for k in ks
            if (total >= k).all()
        }
    print(total.shape)


    langs = sorted(list(pass_at_k.keys()))
    # preview Pass@5
    for lang in langs:
        print(f" & {lang}", end="")
    print()
    avg = 0
    for lang in langs:
        print(f" & {round(pass_at_k[lang]['pass@5']*100, 2)}", end="")
        avg += pass_at_k[lang]["pass@10"] * 100
    avg /= len(langs)
    print(f" & {round(avg, 2)}")
    pass_at_k['avg'] = avg

    # preview Top@5
    # for lang in langs:
    #     print(f" & {lang}", end="")
    # print()
    # avg = 0
    # for lang in langs:
    #     print(f" & {round(top_at_k[lang]['top@5']*100, 2)}", end="")
    #     avg += top_at_k[lang]["top@5"] * 100
    # avg /= len(langs)
    # print(f" & {round(avg, 2)}")
    # top_at_k['avg'] = avg

    now = time.gmtime()
    os.makedirs(output_dir, exist_ok=True)
    if it:
        output_file = os.path.join(output_dir, f"results_{name}_iter_{it}_{now.tm_year}_{now.tm_mon}_{now.tm_mday}_{now.tm_hour+8}_{now.tm_min}.json")
    else:
        output_file = os.path.join(output_dir, f"results_{name}_{now.tm_year}_{now.tm_mon}_{now.tm_mday}_{now.tm_hour+8}_{now.tm_min}.json")

    pass_at_k['note'] = note

    with open(output_file, 'w') as final_results:
        json.dump(pass_at_k, final_results)
    print(f"Complete results are saved in {output_file}")

def run(base_dir, k, it, name, note):
    output_dir = os.path.join(base_dir, "cal_results")
    path = base_dir
    output_path = os.path.join(path, "eval_apr_val_execeval")

    eval_dict = dict()

    ks = range(1, k + 1)
    pass_at_k = defaultdict(dict)
    
    for lang, compiler in tqdm.tqdm(LANG_CLUSTER_TO_LANG_COMPILER.items()):
        results = defaultdict(list)
        for i in range(it + 1):
            if i == 0:
                eval_out_file = get_execeval_out_file_name(output_path, compiler)
            else:
                eval_out_file = get_iter_out_file_name(path, compiler, i - 1)
            tmp_dict = dict()
            with jsonlines.open(eval_out_file) as jrp:
                for sample in jrp:
                    uid = sample["source_data"]["bug_code_uid"]
                    if uid not in tmp_dict:
                        tmp_dict[uid] = {"correct": 0, "ut_reses": [], "src_uid": sample["source_data"]["src_uid"]}
                    ut_res = sample["unit_test_results"][0]
                    if all(x["exec_outcome"] == "PASSED" for x in ut_res):
                        tmp_dict[uid]["correct"] += 1
                    tmp_dict[uid]["ut_reses"].append(ut_res)
            if i == 0:
                eval_dict = tmp_dict.copy()
            else:
                for uid in tmp_dict.keys():
                    if tmp_dict[uid]["correct"] > eval_dict[uid]["correct"]:
                        eval_dict[uid]["correct"] = tmp_dict[uid]["correct"]
                        eval_dict[uid]["ut_reses"] = tmp_dict[uid]["ut_reses"]
        for uid in eval_dict.keys():
            task_id = f"{eval_dict[uid]['src_uid']}|||{lang}"
            results[task_id] += eval_dict[uid]["ut_reses"]
        
        total, correct = [], []
        for result in results.values():
            passed = [
                all(x["exec_outcome"] == "PASSED" for x in ut_res) for ut_res in result
            ]
            total.append(len(passed))
            correct.append(sum(passed))
        total = np.array(total)
        correct = np.array(correct)

        pass_at_k[lang] = {
            f"pass@{k}": estimate_pass_at_k(total, correct, k).mean()
            for k in ks
            if (total >= k).all()
        }
                    
    
    # construct result as {[task_id]: [unit_test_results]}
    # task_id will be src_uid_lang

    

    # sample_num_rec = dict()

    # for lang, compiler in tqdm.tqdm(LANG_CLUSTER_TO_LANG_COMPILER.items()):
    #     execeval_out_file = get_execeval_out_file_name(output_path, compiler)
    #     results = defaultdict(list)
    #     with jsonlines.open(execeval_out_file) as jrp:
    #         for sample in jrp:
    #             if it and sample["source_data"]["bug_code_uid"] in unfixed_ids_list[0]:
    #                 continue
    #             src_uid = sample["source_data"]["src_uid"]
    #             task_id = f"{src_uid}|||{lang}"
    #             for ut_res in sample["unit_test_results"]:
    #                 if "error" in ut_res:
    #                     continue
    #                 results[task_id].append(ut_res)
        
    #     for i in range(it):
    #         iter_out_file = get_iter_out_file_name(path, compiler, i)
    #         with jsonlines.open(iter_out_file) as jrp:
    #             for sample in jrp:
    #                 bug_uid = sample["source_data"]["bug_code_uid"]
    #                 if bug_uid not in sample_num_rec:
    #                     sample_num_rec[bug_uid] = {"max_success": unfixed_ids_list[i][bug_uid], "results": sample["unit_test_results"]}
    #                 if i != it - 1: # if not the final iteration, wait and see
    #                     pass
    #                 else: # if it is the final iteration, must calculate anyway
    #                     src_uid = sample["source_data"]["src_uid"]
    #                     task_id = f"{src_uid}|||{lang}"
    #                     for ut_res in sample["unit_test_results"]:
    #                         if "error" in ut_res:
    #                             continue
    #                         results[task_id].append(ut_res)
        
        


    langs = sorted(list(pass_at_k.keys()))
    # preview Pass@5
    for lang in langs:
        print(f" & {lang}", end="")
    print()
    avg = 0
    for lang in langs:
        print(f" & {round(pass_at_k[lang]['pass@5']*100, 2)}", end="")
        avg += pass_at_k[lang]["pass@5"] * 100
    avg /= len(langs)
    print(f" & {round(avg, 2)}")
    pass_at_k['avg'] = avg

    now = time.gmtime()
    os.makedirs(output_dir, exist_ok=True)
    if it:
        output_file = os.path.join(output_dir, f"results_{name}_iter_{it}_{now.tm_year}_{now.tm_mon}_{now.tm_mday}_{now.tm_hour+8}_{now.tm_min}.json")
    else:
        output_file = os.path.join(output_dir, f"results_{name}_{now.tm_year}_{now.tm_mon}_{now.tm_mday}_{now.tm_hour+8}_{now.tm_min}.json")

    pass_at_k['note'] = note

    with open(output_file, 'w') as final_results:
        json.dump(pass_at_k, final_results)
    print(f"Complete results are saved in {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-dir",
        default="dumped/oai/apr_n_sample_20",
        help="Path to the trans-repair base directory.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=20,
        help="The k as in Pass@k.",
    )
    parser.add_argument(
        "--it",
        default=0,
        type=int,
        help="Current iteration epoch of trans-repair.",
    )
    parser.add_argument(
        "--name",
        default="tr",
        help="Name of the session.",
    )
    parser.add_argument(
        "--note",
        default="",
        help="The note for the results.",
    )
    args = parser.parse_args()

    run(args.base_dir, args.k, args.it, args.name, args.note)