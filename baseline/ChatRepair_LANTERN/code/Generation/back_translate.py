import argparse
import json
import os
import time
import concurrent.futures
import tqdm

import openai

from Dataset.dataset import parse_defects4j_12, parse_defects4j_2
from prompt import BACK_TRANS_PROMPT
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


def load_repair_results(repair_folder):
    """
    Load repair results from the repair folder
    """
    repairs = {}
    if not os.path.exists(repair_folder):
        return repairs
    
    result_files = [f for f in os.listdir(repair_folder) if f.endswith('_result.json') and '_repair_' in f]
    
    for result_file in result_files:
        try:
            with open(os.path.join(repair_folder, result_file), "r") as f:
                result = json.load(f)
                
                # Only process repairs that were successfully saved and have repaired code
                if result.get('saved', False) and result.get('repaired_code'):
                    bug = result['bug']
                    target_lang = result['target_lang']
                    attempt = result['attempt']
                    
                    if bug not in repairs:
                        repairs[bug] = {}
                    if target_lang not in repairs[bug]:
                        repairs[bug][target_lang] = []
                    
                    repairs[bug][target_lang].append(result)
        except Exception as e:
            print(f"Error reading {result_file}: {e}")
    
    return repairs


def process_single_back_translation_only(back_trans_data, args, back_trans_folder, prefix):
    """
    Process back-translation for a single repair (without evaluation)
    """
    bug, target_lang, repair_result = back_trans_data
    attempt = repair_result['attempt']
    
    # Create back-translation result file path
    back_trans_result_file = os.path.join(
        back_trans_folder, 
        f"{bug.replace('.java', '')}_backtrans_{target_lang.lower()}_attempt_{attempt}_result.json"
    )
    
    # Skip if back-translation already exists
    if os.path.exists(back_trans_result_file):
        try:
            with open(back_trans_result_file, "r") as f:
                existing_result = json.load(f)
                if existing_result.get('back_translated_code'):  # Check if translation exists
                    print(f"Skipping {bug} ({target_lang}) attempt {attempt} - back-translation already exists")
                    return bug, target_lang, attempt, "skipped"
        except:
            pass  # File might be corrupted, continue processing
    
    prefix = prefix.strip()
    # Prepare back-translation prompt (swap source and target languages)
    prompt = BACK_TRANS_PROMPT.format(
        source_lang=target_lang,
        target_lang="Java",
        prefix=prefix,
        buggy_code=repair_result['repaired_code']
    )
    
    # Prepare messages for API call
    messages = [
        {"role": "system", "content": "You are an expert programmer skilled in multiple programming languages and code translation."},
        {"role": "user", "content": prompt}
    ]
    
    print(f"Back-translating {bug} ({target_lang}) attempt {attempt} to Java...")
    
    # Make API call
    ret = gen(messages, temperature=args.temperature, nsample=1)
    
    if ret is None:
        print(f"Failed to get response for {bug} ({target_lang}) attempt {attempt}")
        return bug, target_lang, attempt, "failed"
    
    # Parse the response
    func, _ = simple_chatgpt_parse(ret["choices"][0]['message']["content"])
    
    if func != "":
        print(f"Generated back-translation for {bug} ({target_lang}) attempt {attempt}")
        
        # Create result entry (without evaluation)
        result_entry = {
            'bug': bug,
            'source_lang': target_lang,
            'target_lang': 'Java',
            'attempt': attempt,
            'repaired_code': repair_result['repaired_code'],
            'back_translated_code': func,
            'evaluated': False,  # Mark as not evaluated yet
            'valid': None,  # Will be set during evaluation
            'prompt': messages,
            'error': None,  # Will be set during evaluation
            'output': ret,
            'iteration': args.iteration,
            'timestamp': time.time(),
            'repair_info': {
                'original_translated_code': repair_result.get('original_translated_code'),
                'translation_info': repair_result.get('translation_info')
            }
        }
        
        # Save back-translation result
        with open(back_trans_result_file, "w") as f:
            json.dump(result_entry, f, indent=2)
        
        print(f"Back-translation {bug} ({target_lang}) attempt {attempt}: Completed - Saved to {back_trans_result_file}")
            
        return bug, target_lang, attempt, "completed"
    else:
        print(f"No valid function extracted for {bug} ({target_lang}) attempt {attempt}")
        
        # Save failure result
        result_entry = {
            'bug': bug,
            'source_lang': target_lang,
            'target_lang': 'Java',
            'attempt': attempt,
            'repaired_code': repair_result['repaired_code'],
            'back_translated_code': None,
            'evaluated': True,  # No need to evaluate if no code
            'valid': False,
            'prompt': messages,
            'error': "No valid function extracted",
            'output': ret,
            'iteration': args.iteration,
            'timestamp': time.time()
        }
        
        with open(back_trans_result_file, "w") as f:
            json.dump(result_entry, f, indent=2)
            
        return bug, target_lang, attempt, "no_back_translation"


def process_single_evaluation(back_trans_result_file, args, back_trans_folder):
    """
    Evaluate a single back-translated result using write_file
    """
    try:
        with open(back_trans_result_file, "r") as f:
            result = json.load(f)
        
        # Skip if already evaluated or no code to evaluate
        if result.get('evaluated', False) or not result.get('back_translated_code'):
            return result['bug'], result['source_lang'], result['attempt'], "skipped"
        
        bug = result['bug']
        target_lang = result['source_lang']  # Source lang for back-translation
        attempt = result['attempt']
        func = result['back_translated_code']
        
        print(f"Evaluating {bug} ({target_lang}) attempt {attempt}...")
        
        # Validate the back-translated Java code using write_file
        valid, error_message = write_file(
            args, back_trans_folder, func,
            bug.split(".java")[0] + f"_backtrans_{target_lang.lower()}_attempt_{attempt}.java",
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
        with open(back_trans_result_file, "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"Evaluation {bug} ({target_lang}) attempt {attempt}: Valid={valid}")
        if not valid:
            print(f"Error: {error_message}")
        elif valid:
            print(f"SUCCESS: {bug} ({target_lang}) attempt {attempt} produced a valid Java patch!")
            
        return bug, target_lang, attempt, "evaluated"
        
    except Exception as e:
        print(f"Error evaluating {back_trans_result_file}: {e}")
        return None, None, None, "error"


def back_translate_concurrent(args, repairs, back_trans_folder):
    """
    Process back-translations concurrently, then evaluate sequentially
    """
    # Step 1: Create back-translation tasks
    back_trans_tasks = []
    for bug, lang_repairs in repairs.items():
        for target_lang, repair_list in lang_repairs.items():
            for repair_result in repair_list:
                back_trans_tasks.append((bug, target_lang, repair_result))
    
    if not back_trans_tasks:
        print("No back-translation tasks to process")
        return
    
    print(f"Step 1: Processing {len(back_trans_tasks)} back-translation tasks concurrently...")
    
    with open('/root/FSE_ChatRepair/code/Dataset/Defects4j/single_function_repair.json', 'r') as f:
        data = json.load(f)
    # Process back-translations concurrently (without evaluation)
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.num_proc) as executor:
        futures = []
        
        # Submit all translation jobs
        for back_trans_data in back_trans_tasks:
            prefix = data[back_trans_data[0].split('.')[0]]['buggy'].split('\n')[0]
            future = executor.submit(process_single_back_translation_only, back_trans_data, args, back_trans_folder, prefix)
            futures.append(future)
        
        # Collect translation results as they complete
        translated = 0
        skipped = 0
        failed = 0
        
        for future in tqdm.tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Processing back-translations"
        ):
            try:
                bug, target_lang, attempt, status = future.result()
                if status == "completed":
                    translated += 1
                elif status == "skipped":
                    skipped += 1
                elif status in ["failed", "no_back_translation"]:
                    failed += 1
                    
            except Exception as e:
                print(f"Error occurred during translation: {e}")
                failed += 1
    
    print(f"\nBack-translation Summary:")
    print(f"  Total tasks: {len(back_trans_tasks)}")
    print(f"  Translated: {translated}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed: {failed}")
    
    # Step 2: Evaluate all back-translated results sequentially
    print(f"\nStep 2: Evaluating back-translated results sequentially...")
    
    # Find all back-translation result files
    result_files = [f for f in os.listdir(back_trans_folder) if f.endswith('_result.json') and '_backtrans_' in f]
    
    evaluated = 0
    eval_skipped = 0
    valid_patches = 0
    
    for result_file in tqdm.tqdm(result_files, desc="Evaluating results"):
        result_file_path = os.path.join(back_trans_folder, result_file)
        bug, target_lang, attempt, status = process_single_evaluation(result_file_path, args, back_trans_folder)
        
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
    print(f"  Valid Java patches: {valid_patches}")
    
    # Create final summary
    summary = {
        'iteration': args.iteration,
        'total_back_trans_tasks': len(back_trans_tasks),
        'translated': translated,
        'translation_skipped': skipped,
        'translation_failed': failed,
        'evaluated': evaluated,
        'evaluation_skipped': eval_skipped,
        'valid_patches': valid_patches,
        'timestamp': time.time()
    }
    
    with open(os.path.join(back_trans_folder, "back_translation_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)


def back_translate_sequential(args, repairs, back_trans_folder):
    """
    Process back-translations and evaluations sequentially
    """
    with open('/root/FSE_ChatRepair/code/Dataset/Defects4j/single_function_repair.json', 'r') as f:
        data = json.load(f)
    for bug, lang_repairs in repairs.items():
        for target_lang, repair_list in lang_repairs.items():
            print(f"---- {bug} ({target_lang}) ----")
            for repair_result in repair_list:
                attempt = repair_result['attempt']
                print(f"  Attempt {attempt}")
                prefix = data[bug.split('.')[0]]['buggy'].split('\n')[0]
                # Do translation
                status = process_single_back_translation_only((bug, target_lang, repair_result), args, back_trans_folder, prefix)
                
                # If translation succeeded, do evaluation
                if status[3] == "completed":
                    back_trans_result_file = os.path.join(
                        back_trans_folder, 
                        f"{bug.replace('.java', '')}_backtrans_{target_lang.lower()}_attempt_{attempt}_result.json"
                    )
                    process_single_evaluation(back_trans_result_file, args, back_trans_folder)


def collect_valid_patches(back_trans_folder):
    """
    Collect all valid patches from back-translation results
    """
    valid_patches = {}
    if not os.path.exists(back_trans_folder):
        return valid_patches
    
    result_files = [f for f in os.listdir(back_trans_folder) if f.endswith('_result.json') and '_backtrans_' in f]
    
    for result_file in result_files:
        try:
            with open(os.path.join(back_trans_folder, result_file), "r") as f:
                result = json.load(f)
                
                if result.get('valid', False):
                    bug = result['bug']
                    if bug not in valid_patches:
                        valid_patches[bug] = []
                    valid_patches[bug].append(result)
        except Exception as e:
            print(f"Error reading {result_file}: {e}")
    
    return valid_patches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=str, default="Results/test", help="Base folder for results")
    parser.add_argument("--iteration", type=int, required=True, help="Iteration number")
    parser.add_argument("--dataset", type=str, default="defects4j-1.2-function")
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--tmp_prefix", type=str, default="test")
    parser.add_argument("--num_proc", type=int, default=1, help="Number of parallel processes")
    parser.add_argument("--concurrent", action="store_true", help="Use concurrent processing")
    parser.add_argument("--show_valid", action="store_true", help="Show valid patches summary")
    parser.add_argument("--eval_only", action="store_true", help="Only run evaluation on existing back-translations")
    args = parser.parse_args()

    # Set up OpenAI API
    openai.api_key = os.environ.get("API_KEY", "your-api-key")
    openai.api_base = os.environ.get("API_BASE", "your-api-base")
    
    # Create iteration-specific directories
    iter_folder = os.path.join(args.folder, f"iter_{args.iteration}")
    repair_folder = os.path.join(iter_folder, "repair")
    back_trans_folder = os.path.join(iter_folder, "back_trans")
    os.makedirs(back_trans_folder, exist_ok=True)
    
    if args.show_valid:
        # Show valid patches summary
        valid_patches = collect_valid_patches(back_trans_folder)
        print(f"\nValid patches in iteration {args.iteration}:")
        for bug, patches in valid_patches.items():
            print(f"  {bug}: {len(patches)} valid patches")
            for patch in patches:
                print(f"    - {patch['source_lang']} attempt {patch['attempt']}")
        return
    
    if args.eval_only:
        # Only run evaluation on existing back-translations
        print("Running evaluation only on existing back-translations...")
        result_files = [f for f in os.listdir(back_trans_folder) if f.endswith('_result.json') and '_backtrans_' in f]
        
        for result_file in tqdm.tqdm(result_files, desc="Evaluating results"):
            result_file_path = os.path.join(back_trans_folder, result_file)
            process_single_evaluation(result_file_path, args, back_trans_folder)
        
        # Show final results
        valid_patches = collect_valid_patches(back_trans_folder)
        print(f"\nEvaluation Complete:")
        print(f"  Bugs with valid patches: {len(valid_patches)}")
        print(f"  Total valid patches: {sum(len(patches) for patches in valid_patches.values())}")
        return
    
    # Load repair results
    print(f"Loading repair results from {repair_folder}...")
    repairs = load_repair_results(repair_folder)
    
    if not repairs:
        print(f"No repair results found in {repair_folder}")
        return
    
    print(f"Found repairs for {len(repairs)} bugs")
    total_repairs = sum(len(lang_repairs) for lang_repairs in repairs.values())
    total_repair_attempts = sum(
        len(repair_list) 
        for lang_repairs in repairs.values() 
        for repair_list in lang_repairs.values()
    )
    print(f"Total repair language pairs: {total_repairs}")
    print(f"Total repair attempts: {total_repair_attempts}")
    
    # Save args
    with open(os.path.join(back_trans_folder, "back_translate_args.txt"), "w") as f:
        f.write(str(args))
    
    # Choose processing method
    if args.concurrent and args.num_proc > 1:
        back_translate_concurrent(args, repairs, back_trans_folder)
    else:
        back_translate_sequential(args, repairs, back_trans_folder)
    
    # Show final summary
    print("\nCollecting final results...")
    valid_patches = collect_valid_patches(back_trans_folder)
    
    print(f"\nFinal Summary for Iteration {args.iteration}:")
    print(f"  Bugs with valid patches: {len(valid_patches)}")
    print(f"  Total valid patches: {sum(len(patches) for patches in valid_patches.values())}")
    
    if valid_patches:
        print(f"\nValid patches by bug:")
        for bug, patches in valid_patches.items():
            languages = [f"{patch['source_lang']}(attempt {patch['attempt']})" for patch in patches]
            print(f"  {bug}: {', '.join(languages)}")


if __name__ == "__main__":
    main()