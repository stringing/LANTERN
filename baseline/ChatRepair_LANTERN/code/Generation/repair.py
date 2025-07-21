import argparse
import json
import os
import time
import concurrent.futures
import tqdm

import openai

from Dataset.dataset import parse_defects4j_12, parse_defects4j_2
from Dataset.dataset import get_unified_diff
from prompt import INIT_CHATGPT_INFILL_FUNCTION_FAILING_TEST_LINE
import util.util
from util.util import simple_chatgpt_parse, num_tokens_from_messages_offline
from util.util import write_file, build_values


def gen(messages, temperature=1.0, nsample=1):
    """
    API call function similar to gen.py
    """
    cnt = 0
    while True:
        if cnt == 999:
            return None
        try:
            c = openai.ChatCompletion.create(
                model=os.environ.get("MODEL_NAME", "deepseek-chat"),
                messages=messages,
                temperature=temperature,
                top_p=1,
                n=nsample,
                frequency_penalty=0.0,
                presence_penalty=0.0,
            )
            break
        except Exception as e:
            cnt += 1
            time.sleep(5)
            print(f"{e}")
    
    return c


def process_single_repair_only(repair_data, args):
    """
    Process a single repair attempt - generate repair only (without evaluation)
    """
    bug, v, attempt = repair_data
    
    # Create individual result file path
    bug_result_file = os.path.join(args.folder, f"{bug.replace('.java', '')}_attempt_{attempt}_result.json")
    
    # Skip if result already exists and has patch
    if os.path.exists(bug_result_file):
        try:
            with open(bug_result_file, "r") as f:
                existing_result = json.load(f)
                if existing_result.get('patch'):  # Check if patch exists
                    print(f"Skipping {bug} attempt {attempt} - repair already exists")
                    return bug, attempt, "skipped"
        except:
            pass  # File might be corrupted, continue processing
    
    prompt = INIT_CHATGPT_INFILL_FUNCTION_FAILING_TEST_LINE.format(
        buggy_code=v['buggy'],
        failing_test=v['failing_tests'][0]['test_method_name'],
        error_message=v['failing_tests'][0]['failure_message'].strip(),
        failing_line=v['failing_tests'][0]['failing_line'].strip()
    )

    # Prepare messages for API call
    messages = [
        {"role": "system", "content": "You are an automated program repair tool."},
        {"role": "user", "content": prompt}
    ]

    print(f"Generating repair for {bug} attempt {attempt}...")

    # Make API call
    ret = gen(messages, temperature=args.temperature, nsample=1)
    
    if ret is None:
        print(f"Failed to get response for {bug} attempt {attempt}")
        return bug, attempt, "failed"

    # Parse the response
    func, _ = simple_chatgpt_parse(ret["choices"][0]['message']["content"])
    
    if func != "":
        print(f"Generated patch for {bug} attempt {attempt}")
        
        # Create result entry (without evaluation)
        result_entry = {
            'bug': bug,
            'attempt': attempt,
            'patch': func,
            'evaluated': False,  # Mark as not evaluated yet
            'valid': None,  # Will be set during evaluation
            'prompt': messages,
            'error': None,  # Will be set during evaluation
            'output': ret,
            'timestamp': time.time()
        }
        
        # Save result file
        with open(bug_result_file, "w") as f:
            json.dump(result_entry, f, indent=2)
        
        print(f"Repair {bug} attempt {attempt}: Generated - Saved to {bug_result_file}")
            
        return bug, attempt, "completed"
    else:
        print(f"No valid function extracted for {bug} attempt {attempt}")
        
        # Save failure result
        result_entry = {
            'bug': bug,
            'attempt': attempt,
            'patch': None,
            'evaluated': True,  # No need to evaluate if no patch
            'valid': False,
            'prompt': messages,
            'error': "No valid function extracted",
            'output': ret,
            'timestamp': time.time()
        }
        
        with open(bug_result_file, "w") as f:
            json.dump(result_entry, f, indent=2)
            
        return bug, attempt, "no_patch"


def process_single_evaluation(bug_result_file, args):
    """
    Evaluate a single repair using write_file
    """
    try:
        with open(bug_result_file, "r") as f:
            result = json.load(f)
        
        # Skip if already evaluated or no patch to evaluate
        if result.get('evaluated', False) or not result.get('patch'):
            return result['bug'], result['attempt'], "skipped"
        
        bug = result['bug']
        attempt = result['attempt']
        func = result['patch']
        
        print(f"Evaluating {bug} attempt {attempt}...")
        
        # Validate the patch using write_file
        valid, error_message = write_file(
            args, args.folder, func,
            bug.split(".java")[0] + f"_{attempt}.java",
            bug.split(".java")[0], 
            skip_val=False, 
            lang="java",
            reset=True
        )
        
        # Update result with evaluation
        result['evaluated'] = True
        result['valid'] = valid
        result['error'] = error_message
        result['evaluation_timestamp'] = time.time()
        
        # Save updated result
        with open(bug_result_file, "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"Evaluation {bug} attempt {attempt}: Valid={valid}")
        if not valid:
            print(f"Error: {error_message}")
        elif valid:
            print(f"SUCCESS: {bug} attempt {attempt} produced a valid patch!")
            
        return bug, attempt, "evaluated"
        
    except Exception as e:
        print(f"Error evaluating {bug_result_file}: {e}")
        return None, None, "error"


def collect_all_results(folder):
    """
    Collect all individual result files into a single summary
    """
    results = {}
    result_files = [f for f in os.listdir(folder) if f.endswith('_result.json') and '_attempt_' in f]
    
    for result_file in result_files:
        try:
            with open(os.path.join(folder, result_file), "r") as f:
                result = json.load(f)
                bug = result['bug']
                if bug not in results:
                    results[bug] = []
                results[bug].append(result)
        except Exception as e:
            print(f"Error reading {result_file}: {e}")
    
    return results


def chatgpt_apr_concurrent(args, bugs):
    """
    Process bugs concurrently: repair generation concurrent, evaluation sequential
    """
    # Step 1: Create repair tasks for all attempts
    repair_tasks = []
    for bug, v in bugs.items():
        for attempt in range(args.nattempt):
            repair_tasks.append((bug, v, attempt))
    
    print(f"Step 1: Generating repairs for {len(bugs)} bugs × {args.nattempt} attempts = {len(repair_tasks)} total tasks concurrently...")

    # Process repair generation concurrently
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.num_proc) as executor:
        futures = []
        
        # Submit all repair generation jobs
        for repair_data in repair_tasks:
            future = executor.submit(process_single_repair_only, repair_data, args)
            futures.append(future)
        
        # Collect repair results as they complete
        generated = 0
        skipped = 0
        failed = 0
        
        for future in tqdm.tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Generating repairs"
        ):
            try:
                bug, attempt, status = future.result()
                if status == "completed":
                    generated += 1
                elif status == "skipped":
                    skipped += 1
                elif status in ["failed", "no_patch"]:
                    failed += 1
                    
            except Exception as e:
                print(f"Error occurred during repair generation: {e}")
                failed += 1

    print(f"\nRepair Generation Summary:")
    print(f"  Total tasks: {len(repair_tasks)}")
    print(f"  Generated: {generated}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed: {failed}")
    
    # Step 2: Evaluate all generated repairs sequentially
    print(f"\nStep 2: Evaluating generated repairs sequentially...")
    
    # Find all result files
    result_files = [f for f in os.listdir(args.folder) if f.endswith('_result.json') and '_attempt_' in f]
    
    evaluated = 0
    eval_skipped = 0
    valid_patches = 0
    
    for result_file in tqdm.tqdm(result_files, desc="Evaluating repairs"):
        result_file_path = os.path.join(args.folder, result_file)
        bug, attempt, status = process_single_evaluation(result_file_path, args)
        
        if status == "evaluated":
            evaluated += 1
            # Check if it's valid
            try:
                with open(result_file_path, "r") as f:
                    result = json.load(f)
                    if result.get('valid', False):
                        valid_patches += 1
            except:
                pass
        elif status == "skipped":
            eval_skipped += 1

    print(f"\nEvaluation Summary:")
    print(f"  Total result files: {len(result_files)}")
    print(f"  Evaluated: {evaluated}")
    print(f"  Skipped: {eval_skipped}")
    print(f"  Valid patches: {valid_patches}")
    
    # Create final summary
    summary = {
        'total_bugs': len(bugs),
        'nattempt': args.nattempt,
        'total_tasks': len(repair_tasks),
        'generated': generated,
        'generation_skipped': skipped,
        'generation_failed': failed,
        'evaluated': evaluated,
        'evaluation_skipped': eval_skipped,
        'valid_patches': valid_patches,
        'timestamp': time.time()
    }
    
    with open(os.path.join(args.folder, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)


def chatgpt_apr_sequential(args, bugs):
    """
    Sequential processing - do both repair and evaluation for each bug and attempt
    """
    for bug, v in bugs.items():
        print("---- {} ----".format(bug))
        for attempt in range(args.nattempt):
            print(f"  Attempt {attempt + 1}/{args.nattempt}")
            
            # Generate repair
            status = process_single_repair_only((bug, v, attempt), args)
            
            # If repair generation succeeded, do evaluation
            if status[2] == "completed":
                bug_result_file = os.path.join(args.folder, f"{bug.replace('.java', '')}_attempt_{attempt}_result.json")
                process_single_evaluation(bug_result_file, args)


def merge_results(args):
    """
    Merge all individual result files into the original lm_repair.json format
    """
    results = collect_all_results(args.folder)
    
    # Convert to original format
    lm_repair_format = {}
    for bug, bug_results in results.items():
        lm_repair_format[bug] = []
        for result in bug_results:
            entry = {
                'patch': result['patch'],
                'valid': result['valid'],
                'prompt': result['prompt'],
                'error': result['error'],
                'output': result['output'],
                'attempt': result['attempt']
            }
            lm_repair_format[bug].append(entry)
    
    with open(os.path.join(args.folder, "lm_repair.json"), "w") as f:
        json.dump(lm_repair_format, f, indent=2)
    
    print(f"Merged {len(results)} bug results into lm_repair.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=str, default="Results/test")
    parser.add_argument("--dataset", type=str, default="defects4j-1.2-function")
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--tmp_prefix", type=str, default="test")
    parser.add_argument("--num_proc", type=int, default=1, help="Number of parallel processes")
    parser.add_argument("--nattempt", type=int, default=1, help="Number of attempts for each bug")
    parser.add_argument("--concurrent", action="store_true", help="Use concurrent processing")
    parser.add_argument("--merge_only", action="store_true", help="Only merge existing result files")
    parser.add_argument("--eval_only", action="store_true", help="Only run evaluation on existing repairs")
    parser.add_argument("--show_valid", action="store_true", help="Show valid patches summary")
    args = parser.parse_args()

    # Set up OpenAI API
    openai.api_key = os.environ.get("API_KEY", "your-api-key")
    openai.api_base = os.environ.get("API_BASE", "your-api-base")
    
    os.makedirs(args.folder, exist_ok=True)
    
    if args.merge_only:
        merge_results(args)
        return
    
    if args.show_valid:
        # Show valid patches summary
        results = collect_all_results(args.folder)
        valid_count = 0
        print(f"\nValid patches:")
        for bug, bug_results in results.items():
            valid_attempts = []
            for result in bug_results:
                if result.get('valid', False):
                    valid_attempts.append(result['attempt'])
                    valid_count += 1
            if valid_attempts:
                print(f"  {bug}: Valid attempts {valid_attempts}")
        print(f"Total valid patches: {valid_count}")
        return
    
    if args.eval_only:
        # Only run evaluation on existing repairs
        print("Running evaluation only on existing repairs...")
        result_files = [f for f in os.listdir(args.folder) if f.endswith('_result.json') and '_attempt_' in f]
        
        valid_patches = 0
        for result_file in tqdm.tqdm(result_files, desc="Evaluating repairs"):
            result_file_path = os.path.join(args.folder, result_file)
            bug, attempt, status = process_single_evaluation(result_file_path, args)
            
            if status == "evaluated":
                # Check if it's valid
                try:
                    with open(result_file_path, "r") as f:
                        result = json.load(f)
                        if result.get('valid', False):
                            valid_patches += 1
                except:
                    pass
        
        print(f"\nEvaluation Complete:")
        print(f"  Valid patches: {valid_patches}")
        return
    
    with open(os.path.join(args.folder, "args.txt"), "w") as f:
        f.write(str(args))

    # Parse dataset
    if args.dataset == "defects4j-1.2-function":
        bugs = parse_defects4j_12("../Dataset/")
    elif args.dataset == "defects4j-1.2-single-hunk":
        bugs = parse_defects4j_12("../Dataset/", single_hunk=True)
    elif args.dataset == "defects4j-1.2-single-line":
        bugs = parse_defects4j_12("../Dataset/", single_line=True)
    elif args.dataset == "defects4j-2.0-single-line":
        bugs = parse_defects4j_2("../Dataset/")
    else:
        raise NotImplementedError(f"Dataset {args.dataset} not supported")

    # Choose processing method
    if args.concurrent and args.num_proc > 1:
        chatgpt_apr_concurrent(args, bugs)
    else:
        chatgpt_apr_sequential(args, bugs)
    
    # Optionally merge results into original format
    print("\nMerging individual results...")
    merge_results(args)


if __name__ == "__main__":
    main()