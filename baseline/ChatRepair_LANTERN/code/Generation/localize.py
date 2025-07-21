import argparse
import json
import os

import openai

from Dataset.dataset import parse_python, parse_java
from Dataset.dataset import parse_defects4j_12
from prompt import CHATGPT_LOCALIZE_PROMPT
from Generation.util.util import get_initial_failing_tests, num_tokens_from_messages, complex_chatgpt_localize_parse
from Generation.util.api_request import create_chatgpt_config, request_chatgpt_engine


def chatgpt_localize(args, bugs):
    results = {}

    for bug, v in bugs.items():
        print("---- {} ----".format(bug))
        prompt = CHATGPT_LOCALIZE_PROMPT.format(buggy_code=v['buggy'],
                                                root_cause=get_initial_failing_tests(args, bug))
        print(prompt)
        config = create_chatgpt_config(prev={}, message=prompt, max_tokens=100, few_shot=args.few_shot,
                                       bug_id=bug, bugs=bugs, system_message="You are a Fault Localization tool.")
        if num_tokens_from_messages(config["messages"]) + 100 > 4096:
            continue
        results[bug] = []
        # first sampling with temperature = 0
        config = create_chatgpt_config(prev={}, message=prompt, max_tokens=100, few_shot=args.few_shot,
                                       bug_id=bug, bugs=bugs, system_message="You are a Fault Localization tool.",
                                       temperature=0, localize=True)
        for message in config['messages']:
            print("{} : {}".format(message['role'], message['content']))
        ret = request_chatgpt_engine(config)

        func, pre_history = complex_chatgpt_localize_parse(ret["choices"][0]['message']["content"])
        print("----------------\n{}\n---------------".format(func))
        results[bug].append(
            {"loc": func, "prompt": config, "usage": ret['usage'], 'output': ret}
        )
        tries = args.total_tries
        # then sample multiple times with majority voting (keeping)
        while tries > 0:
            # from BINDING LANGUAGE MODELS IN SYMBOLIC LANGUAGES paper
            config = create_chatgpt_config(prev={}, message=prompt, max_tokens=100, few_shot=args.few_shot,
                                           bug_id=bug, bugs=bugs, system_message="You are a Fault Localization tool.",
                                           temperature=0.6, localize=True)
            ret = request_chatgpt_engine(config)
            func, pre_history = complex_chatgpt_localize_parse(ret["choices"][0]['message']["content"])
            print("----------------\n{}\n---------------".format(func))
            results[bug].append(
                {"loc": func, "prompt": config, "usage": ret['usage'], 'output': ret}
            )
            tries -= 1

    with open(os.path.join(args.folder, "fl.json"), "w") as f:
        json.dump(results, f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=str, default="Results/test")
    parser.add_argument("--dataset", type=str, default="quixbugs-python")
    parser.add_argument("--few_shot", type=int, default=0)
    parser.add_argument("--total_tries", type=int, default=50)
    parser.add_argument("--key_file", type=str, default="api_key.txt")
    args = parser.parse_args()

    openai.api_key = open(args.key_file, 'r').read().strip()
    os.makedirs(args.folder, exist_ok=True)
    with open(os.path.join(args.folder, "args.txt"), "w") as f:
        f.write(str(args))

    if args.dataset == "quixbugs-python":
        bugs = parse_python("../")
    elif args.dataset == "quixbugs-java":
        bugs = parse_java("../")
    elif args.dataset == "defects4j-1.2-function":
        bugs = parse_defects4j_12("../Dataset/")
    elif args.dataset == "defects4j-1.2-single-hunk":
        bugs = parse_defects4j_12("../Dataset/", single_hunk=True)
    elif args.dataset == "defects4j-1.2-single-line":
        bugs = parse_defects4j_12("../Dataset/", single_line=True)
    else:
        raise NotImplementedError

    chatgpt_localize(args, bugs)


if __name__ == "__main__":
    main()
