import os
import copy
import json
import argparse
import tqdm

from session import Session
from datasets import load_dataset, load_from_disk
from utils import prompt_split_humaneval, find_method_name, code_split, build_test_method, prompt_xcodeeval

parser = argparse.ArgumentParser()
parser.add_argument('--dataset', type=str, default='humaneval')
parser.add_argument('--dataset_path', type=str, default='/root/my/data/xCodeEval/apr')
parser.add_argument('--lang', type=str, default='python')
parser.add_argument('--output_path', type=str, default='output.jsonl')

parser.add_argument('--signature', action='store_true')
parser.add_argument('--model', type=str, default='gpt-3.5-turbo-0301')
parser.add_argument('--max_round', type=int, default=2)

parser.add_argument('--max_tokens', type=int, default=512) 
parser.add_argument('--majority', type=int, default=1)
parser.add_argument('--temperature', type=float, default=0.0)
parser.add_argument('--top_p', type=float, default=0.95)

parser.add_argument('--fail_list', type=list, default=[])
parser.add_argument('--append', action='store_true')
parser.add_argument('--verbose', action='store_true')
parser.add_argument("--timeout", type=float, default=10, help="how many seconds to wait during execution for each test case")
args = parser.parse_args()


if __name__ == '__main__':
    from roles.rule_descriptions_act import TEAM, ANALYST, DEVELOPER, TESTER

    OUTPUT_PATH = args.output_path

    os.makedirs(OUTPUT_PATH, exist_ok=True)

    # load dataset
    dataset = load_from_disk(args.dataset_path)

    pbar = tqdm.tqdm(dataset, total=len(dataset))
    for idx, task in enumerate(pbar):
        intent = prompt_xcodeeval(task)[0]

        test = task['hidden_unit_tests']

        try:
            session = Session(TEAM, ANALYST, DEVELOPER, TESTER, requirement=intent, model=args.model, majority=args.majority, 
                            max_tokens=args.max_tokens, temperature=args.temperature, 
                            top_p=args.top_p, max_round=args.max_round)
            
            code, session_history = session.run_session()

        except RuntimeError as e:
            print(str(e))
            print(f"task-{task['bug_code_uid']} fail")
            args.fail_list.append(task['bug_code_uid'])
            continue

        if  code == "error":
            continue

        solution = {
            'task_id': task['bug_code_uid'],
            'src_uid': task['src_uid'],
            'lang': task['lang_cluster'],
            'prompt': intent,
            'test': test,
            'completion': code,
            'session_history': session_history,
        }
        file_path = os.path.join(OUTPUT_PATH, task['bug_code_uid'])
        with open(file_path, 'w') as f:
            f.write(json.dumps(solution) + '\n')
            f.flush()
    
    # save fail list
    if args.fail_list:
        with open('fail_list.txt', 'w') as fail_file:
            for item in args.fail_list:
                fail_file.write(f"{item}\n")
        print(f"Failed tasks saved to fail_list.txt: {args.fail_list}")
    else:
        print("All tasks completed successfully.")
