import os
import copy
import json
import argparse
import tqdm
import concurrent.futures
from threading import Lock

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
parser.add_argument('--it', type=int, default=1) 

parser.add_argument('--fail_list', type=list, default=[])
parser.add_argument('--append', action='store_true')
parser.add_argument('--verbose', action='store_true')
parser.add_argument("--timeout", type=float, default=10, help="how many seconds to wait during execution for each test case")

# Add concurrent execution parameters
parser.add_argument('--num_proc', type=int, default=4, help='Number of parallel processes')
parser.add_argument('--use_threading', action='store_true', help='Use ThreadPoolExecutor instead of ProcessPoolExecutor')

args = parser.parse_args()


def process_task(task, model, majority, max_tokens, temperature, top_p, max_round, output_path, it):
    """
    Process a single task and return the result.
    Returns a tuple: (success: bool, task_id: str, error_msg: str or None)
    """
    from roles.rule_descriptions_act import TEAM, ANALYST, DEVELOPER, TESTER
    
    try:
        intent = prompt_xcodeeval(task)[0]
        test = task['hidden_unit_tests']

        session = Session(TEAM, ANALYST, DEVELOPER, TESTER, requirement=intent, model=model, majority=majority, 
                        max_tokens=max_tokens, temperature=temperature, 
                        top_p=top_p, max_round=max_round)
        
        code, session_history = session.run_session()

        if code == "error":
            return False, task['bug_code_uid'], "Session returned error"

        solution = {
            'task_id': task['bug_code_uid'],
            'src_uid': task['src_uid'],
            'lang': task['lang_cluster'],
            'prompt': intent,
            'test': test,
            'completion': code,
            'session_history': session_history,
        }
        
        file_path = os.path.join(output_path, f"{task['bug_code_uid']}_{it}.json")
        with open(file_path, 'w') as f:
            f.write(json.dumps(solution) + '\n')
            f.flush()
        
        return True, task['bug_code_uid'], None

    except RuntimeError as e:
        error_msg = f"RuntimeError: {str(e)}"
        return False, task['bug_code_uid'], error_msg
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        return False, task['bug_code_uid'], error_msg


def run_concurrent_processing(dataset, args):
    """
    Run the processing with concurrent execution
    """
    OUTPUT_PATH = args.output_path
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    
    # Choose executor type
    if args.use_threading:
        executor_class = concurrent.futures.ThreadPoolExecutor
        print(f"Using ThreadPoolExecutor with {args.num_proc} workers")
    else:
        executor_class = concurrent.futures.ProcessPoolExecutor
        print(f"Using ProcessPoolExecutor with {args.num_proc} workers")
    
    fail_list = []

    failed_id = []
    if os.path.exists('./fail_list.txt'):
        with open('./fail_list.txt', 'r') as fi:
            for line in fi.readlines():
                id = line.strip()
                if id != '':
                    failed_id.append(id)
    
    with executor_class(max_workers=args.num_proc) as executor:
        # Submit all tasks
        futures = []
        for task in tqdm.tqdm(dataset, desc="Submitting tasks"):
            if task['bug_code_uid'] in failed_id:
                continue
            future = executor.submit(
                process_task,
                task,
                args.model,
                args.majority,
                args.max_tokens,
                args.temperature,
                args.top_p,
                args.max_round,
                OUTPUT_PATH,
                args.it
            )
            futures.append(future)
        
        # Process completed tasks
        for future in tqdm.tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Processing tasks"
        ):
            try:
                success, task_id, error_msg = future.result()
                if not success:
                    print(f"task-{task_id} fail: {error_msg}")
                    fail_list.append(task_id)
                elif args.verbose:
                    print(f"task-{task_id} completed successfully")
            except Exception as e:
                print(f"Error occurred in future: {e}")
                # We can't get task_id in this case, so add a generic error
                fail_list.append(f"unknown_task_error_{len(fail_list)}")
    
    return fail_list


def run_sequential_processing(dataset, args):
    """
    Run the original sequential processing (fallback)
    """
    from roles.rule_descriptions_act import TEAM, ANALYST, DEVELOPER, TESTER

    OUTPUT_PATH = args.output_path
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    
    fail_list = []

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
            fail_list.append(task['bug_code_uid'])
            continue

        if code == "error":
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
    
    return fail_list


if __name__ == '__main__':
    # load dataset
    dataset = load_from_disk(args.dataset_path)
    
    # Run processing (concurrent by default, sequential if num_proc = 1)
    if args.num_proc > 1:
        fail_list = run_concurrent_processing(dataset, args)
    else:
        print("Running sequential processing (num_proc = 1)")
        fail_list = run_sequential_processing(dataset, args)
    
    # save fail list
    if fail_list:
        with open(f'fail_list_{args.it}.txt', 'w') as fail_file:
            for item in fail_list:
                fail_file.write(f"{item}\n")
        print(f"Failed tasks saved to fail_list.txt: {fail_list}")
    else:
        print("All tasks completed successfully.")