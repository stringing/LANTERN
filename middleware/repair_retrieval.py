import os
import json
import random



def retrieve(base_dir, uid, it):
    hist_file = os.path.join(base_dir, "history/repair_history.json")
    repair_hist = ""
    with open(hist_file, "r") as f:
        hist = json.load(f)
    for i in range(it):
        if uid not in hist:
            return repair_hist
        lang = hist[uid][f"it_{i}"]["lang"]
        patterns = hist[uid][f"it_{i}"]["patterns"]
        max_data = patterns[list(patterns.keys())[0]]
        for pattern, data in patterns.items():
            if data["count"] > max_data["count"]:
                max_data = data
        code = max_data["bug_source_codes"][0]
        test_eg = max_data["test_details"][0][0]
        input = test_eg["input"]
        if len(test_eg["output"]) == 0:
            output = ""
        else:
            output = test_eg["output"][0]
        exec_outcome = test_eg["exec_outcome"]
        result = test_eg["result"]
        if i == 0:
            repair_hist = f"\nHere is the historical repair of the bug in {lang} programming language:\n"
        repair_hist += f"Iteration {i}:\n"
        repair_hist += f"- code:\n{code}\n"
        repair_hist += f"Here are the failed test:\n- Input:\n{input}- Expected output:\n{output}\n- Result:\n{result}\n- Execution outcome:\n{exec_outcome}"
        if i == it - 1:
            repair_hist += "\n"
        else:
            repair_hist += "\n\n"
    return repair_hist


def add_hist(base_dir, dt, it):
    dt["repair_hist"] = retrieve(base_dir, dt["bug_code_uid"], it)
    return dt

def construct_test(oai_id, last_tests, p=1.0):
    test_content = ""
    all_tests = []
    selected_tests = []
    for t in last_tests[oai_id]:
        if t['exec_outcome'] != 'PASSED':
            all_tests.append(t)
    num_samples = int(max(len(all_tests) * p, 1))
    selected_tests.append(all_tests[0])
    if num_samples > 1:
        selected_tests.extend(random.sample(all_tests[1:], num_samples - 1))
    for t in selected_tests:
        if t['exec_outcome'] != "COMPILATION_ERROR":
            test_content += f"Input: {t['input']}\n"
            test_content += f"Expected Output: {t['output'][0]}\n"
            test_content += f"Actual Output: {t['result']}\n"
            test_content += f"Execution Outcome: {t['exec_outcome']}\n\n"
        else:
            test_content += f"Execution Outcome: {t['exec_outcome']}\n"
            test_content += f"Actual Output: {t['result']}\n\n"
    return test_content

# def retrieve_current(base_dir, it, sample, last_tests):
#     oai_id = sample["oai_id"]
#     lang = sample["lang_cluster"]
#     transed_code = sample["bug_source_code"]
#     cur = "The fixed code is still not correct with the following failed tests.\n"
#     cur += construct_test(oai_id, last_tests, 1 / 11)
#     cur += f"Here is a translated version of the buggy code in {lang}:\n"
#     cur += f"{transed_code}\n"
#     cur += f"Please reflect on the failed tests step by step and provide the fixed {lang} code in json format.\n"
#     cur += "Response format:\n"
#     cur += "```json\n"
#     cur += "fixed code: [your fixed code]\n"
#     cur += "reflection: [your step-by-step reflection on the failed tests]\n"
#     cur += "```\n"
#     return cur

def retrieve_current(base_dir, it, sample, last_tests):
    oai_id = sample["oai_id"]
    lang = sample["lang_cluster"]
    transed_code = sample["bug_source_code"]
    cur = "The fixed code is still not correct with the following failed tests.\n"
    cur += construct_test(oai_id, last_tests, 1 / 11)
    cur += f"Provide the fixed {lang} code without any description or extra tokens.\n\nFixed source code:\n"
    return cur

def construct_conversation(base_dir, it, sample, last_repair, last_tests):
    oai_id = sample["oai_id"]
    if it == 1:
        msg = []
        msg_0 = {"role": "user", "content": last_repair[oai_id]["msg"]}
        res_0 = {"role": "assistant", "content": last_repair[oai_id]["res"]}
        msg_1 = {"role": "user", "content": retrieve_current(base_dir, it, sample, last_tests)}
        msg.append(msg_0)
        msg.append(res_0)
        msg.append(msg_1)
    else:
        msg = last_repair[oai_id]["msg"]
        res_1 = {"role": "assistant", "content": last_repair[oai_id]["res"]}
        msg_2 = {"role": "user", "content": retrieve_current(base_dir, it, sample, last_tests)}
        msg.append(res_1)
        msg.append(msg_2)
    return msg


if __name__ == "__main__":
    repair_hist = retrieve("/root/my/data/xCodeEval/evaluation/tr_random", "97b9842953105338f38a8aa4f7f0b7da", 2)
    print(repair_hist)