import argparse
import json
import os
import time
import random
import concurrent.futures
import tqdm

import openai

from Dataset.dataset import parse_defects4j_12, parse_defects4j_2
from prompt import TRANS_PROMPT


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


def get_iteration_number(base_folder):
    """
    Automatically determine the next iteration number
    """
    if not os.path.exists(base_folder):
        return 1
    
    existing_iters = []
    for item in os.listdir(base_folder):
        if item.startswith("iter_") and os.path.isdir(os.path.join(base_folder, item)):
            try:
                iter_num = int(item.split("_")[1])
                existing_iters.append(iter_num)
            except ValueError:
                continue
    
    return max(existing_iters) + 1 if existing_iters else 1


def load_repair_results(base_folder, it=1):
    """
    Load repair results from all iterations and identify bugs without valid patches
    """
    unsolved_bugs = set()
    solved_bugs = set()
    
    if not os.path.exists(base_folder):
        return unsolved_bugs, solved_bugs
    
    # Check all iterations for repair results
    if it > 1:
        iter_folder = os.path.join(base_folder, f'iter_{it - 1}')
        
        # Check repair results in this iteration
        repair_folder = os.path.join(iter_folder, "back_trans")
        if os.path.exists(repair_folder):
            result_files = [f for f in os.listdir(repair_folder) if f.endswith('_result.json')]
            
            for result_file in result_files:
                try:
                    with open(os.path.join(repair_folder, result_file), "r") as f:
                        result = json.load(f)
                        bug = result['bug']
                        valid = result.get('valid', False)
                        
                        if valid:
                            solved_bugs.add(bug)
                            if bug in unsolved_bugs:
                                unsolved_bugs.remove(bug)
                        else:
                            if bug not in solved_bugs:  # Only add if not already solved
                                unsolved_bugs.add(bug)
                except Exception as e:
                    print(f"Error reading {result_file}: {e}")
    else:
        # Also check the base folder (original repair results)
        result_files = [f for f in os.listdir(base_folder) if f.endswith('_result.json')]
        for result_file in result_files:
            try:
                with open(os.path.join(base_folder, result_file), "r") as f:
                    result = json.load(f)
                    bug = result['bug']
                    valid = result.get('valid', False)
                    
                    if valid:
                        solved_bugs.add(bug)
                        if bug in unsolved_bugs:
                            unsolved_bugs.remove(bug)
                    else:
                        if bug not in solved_bugs:
                            unsolved_bugs.add(bug)
            except Exception as e:
                print(f"Error reading {result_file}: {e}")
    
    # Remove solved bugs from unsolved set
    # unsolved_bugs = unsolved_bugs - solved_bugs
    
    return unsolved_bugs, solved_bugs


def load_translation_history(base_folder):
    """
    Load translation history from all iterations
    """
    history = {}
    
    if not os.path.exists(base_folder):
        return history
    
    # Load history from all iterations
    for item in os.listdir(base_folder):
        if item.startswith("iter_") and os.path.isdir(os.path.join(base_folder, item)):
            iter_folder = os.path.join(base_folder, item)
            trans_folder = os.path.join(iter_folder, "translation")
            
            if os.path.exists(trans_folder):
                # Load from translation_history.json if exists
                history_file = os.path.join(trans_folder, "translation_history.json")
                if os.path.exists(history_file):
                    try:
                        with open(history_file, "r") as f:
                            iter_history = json.load(f)
                            for bug, langs in iter_history.items():
                                if bug not in history:
                                    history[bug] = []
                                history[bug].extend(langs)
                    except Exception as e:
                        print(f"Error loading translation history from {history_file}: {e}")
                
                # Also scan actual translation result files
                result_files = [f for f in os.listdir(trans_folder) if f.endswith('_result.json') and '_trans_' in f]
                for result_file in result_files:
                    try:
                        with open(os.path.join(trans_folder, result_file), "r") as f:
                            result = json.load(f)
                            bug = result['bug']
                            target_lang = result['target_lang']
                            
                            if bug not in history:
                                history[bug] = []
                            if target_lang not in history[bug]:
                                history[bug].append(target_lang)
                    except Exception as e:
                        print(f"Error reading {result_file}: {e}")
    
    return history


def save_translation_history(trans_folder, history):
    """
    Save translation history to iteration-specific folder
    """
    history_file = os.path.join(trans_folder, "translation_history.json")
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)


def get_next_target_language(bug, history, available_languages):
    """
    Get next target language for a bug that hasn't been used before
    """
    if bug not in history:
        history[bug] = []
    
    used_languages = set(history[bug])
    available = [lang for lang in available_languages if lang not in used_languages]
    
    if not available:
        print(f"Warning: All languages have been tried for bug {bug}")
        return None
    
    return random.choice(available)


def process_single_translation(translation_data, args, trans_folder):
    """
    Process a single translation task
    """
    bug, v, target_lang = translation_data
    
    # Create translation result file path in iteration-specific folder
    trans_result_file = os.path.join(trans_folder, f"{bug.replace('.java', '')}_trans_{target_lang.lower()}_result.json")
    
    # Skip if translation already exists
    if os.path.exists(trans_result_file):
        print(f"Skipping {bug} -> {target_lang} - translation already exists")
        return bug, target_lang, "skipped"
    
    # Prepare translation prompt
    prompt = TRANS_PROMPT.format(
        source_lang="Java",
        target_lang=target_lang,
        buggy_code=v['buggy']
    )
    
    # Prepare messages for API call
    messages = [
        {"role": "system", "content": "You are an expert programmer skilled in multiple programming languages."},
        {"role": "user", "content": prompt}
    ]
    
    print(f"Translating {bug} from Java to {target_lang}...")
    
    # Make API call
    ret = gen(messages, temperature=args.temperature, nsample=1)
    
    if ret is None:
        print(f"Failed to get response for {bug} -> {target_lang}")
        return bug, target_lang, "failed"
    
    # Extract translated code
    translated_code = ret["choices"][0]['message']["content"].strip()
    
    # Create result entry
    result_entry = {
        'bug': bug,
        'source_lang': 'Java',
        'target_lang': target_lang,
        'original_code': v['buggy'],
        'translated_code': translated_code,
        'prompt': messages,
        'output': ret,
        'iteration': args.iteration,
        'timestamp': time.time()
    }
    
    # Save translation result
    with open(trans_result_file, "w") as f:
        json.dump(result_entry, f, indent=2)
    
    print(f"Translation {bug} -> {target_lang} completed - Saved to {trans_result_file}")
    return bug, target_lang, "completed"


def translate_concurrent(args, bugs, unsolved_bugs, trans_folder):
    """
    Process translations concurrently
    """
    # Available target languages
    target_languages = ["C", "C#", "C++", "Go", "Javascript", "Kotlin", "PHP", "Python", "Ruby", "Rust"]
    
    # Load translation history from all iterations
    history = load_translation_history(args.folder)
    
    # Create translation tasks for unsolved bugs
    translation_tasks = []
    current_iteration_history = {}
    
    for bug in unsolved_bugs:
        if bug in bugs:  # Make sure bug exists in dataset
            target_lang = get_next_target_language(bug, history, target_languages)
            if target_lang:
                translation_tasks.append((bug, bugs[bug], target_lang))
                # Track what we're doing in this iteration
                if bug not in current_iteration_history:
                    current_iteration_history[bug] = []
                current_iteration_history[bug].append(target_lang)
    
    # Save current iteration history
    save_translation_history(trans_folder, current_iteration_history)
    
    if not translation_tasks:
        print("No translation tasks to process")
        return
    
    print(f"Processing {len(translation_tasks)} translation tasks concurrently...")
    
    # Process translations concurrently
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.num_proc) as executor:
        futures = []
        
        # Submit all jobs
        for translation_data in translation_tasks:
            future = executor.submit(process_single_translation, translation_data, args, trans_folder)
            futures.append(future)
        
        # Collect results as they complete
        completed = 0
        skipped = 0
        failed = 0
        
        for future in tqdm.tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Processing translations"
        ):
            try:
                bug, target_lang, status = future.result()
                if status == "completed":
                    completed += 1
                elif status == "skipped":
                    skipped += 1
                elif status == "failed":
                    failed += 1
                    
            except Exception as e:
                print(f"Error occurred: {e}")
                failed += 1
    
    print(f"\nTranslation Summary for Iteration {args.iteration}:")
    print(f"  Total tasks: {len(translation_tasks)}")
    print(f"  Completed: {completed}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed: {failed}")
    
    # Create translation summary
    summary = {
        'iteration': args.iteration,
        'total_unsolved_bugs': len(unsolved_bugs),
        'total_translation_tasks': len(translation_tasks),
        'completed': completed,
        'skipped': skipped,
        'failed': failed,
        'timestamp': time.time()
    }
    
    with open(os.path.join(trans_folder, "translation_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)


def translate_sequential(args, bugs, unsolved_bugs, trans_folder):
    """
    Process translations sequentially
    """
    target_languages = ["C", "C#", "C++", "Go", "Javascript", "Kotlin", "PHP", "Python", "Ruby", "Rust"]
    
    # Load translation history from all iterations
    history = load_translation_history(args.folder)
    current_iteration_history = {}
    
    for bug in unsolved_bugs:
        if bug not in bugs:
            continue
            
        print(f"---- {bug} ----")
        target_lang = get_next_target_language(bug, history, target_languages)
        
        if target_lang:
            # Track what we're doing in this iteration
            if bug not in current_iteration_history:
                current_iteration_history[bug] = []
            current_iteration_history[bug].append(target_lang)
            
            # Save history after each update
            save_translation_history(trans_folder, current_iteration_history)
            
            # Process translation
            process_single_translation((bug, bugs[bug], target_lang), args, trans_folder)
        else:
            print(f"No more target languages available for {bug}")


def show_translation_status(base_folder, bugs, it):
    """
    Show current translation status across all iterations
    """
    history = load_translation_history(base_folder)
    unsolved_bugs, solved_bugs = load_repair_results(base_folder, it)
    
    print(f"\nOverall Translation Status:")
    print(f"  Total bugs: {len(bugs)}")
    print(f"  Solved bugs: {len(solved_bugs)}")
    print(f"  Unsolved bugs: {len(unsolved_bugs)}")
    
    print(f"\nTranslation History:")
    target_languages = ["C", "C#", "C++", "Go", "Javascript", "Kotlin", "PHP", "Python", "Ruby", "Rust"]
    
    for bug in sorted(unsolved_bugs):
        if bug in history:
            tried = set(history[bug])
            remaining = set(target_languages) - tried
            print(f"  {bug}:")
            print(f"    Tried: {', '.join(sorted(tried)) if tried else 'None'}")
            print(f"    Remaining: {', '.join(sorted(remaining)) if remaining else 'None'}")
        else:
            print(f"  {bug}: No translations yet")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=str, default="Results/test", help="Base folder for results")
    parser.add_argument("--dataset", type=str, default="defects4j-1.2-function")
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--num_proc", type=int, default=1, help="Number of parallel processes")
    parser.add_argument("--iteration", type=int, default=None, help="Iteration number (auto-detect if not specified)")
    parser.add_argument("--concurrent", action="store_true", help="Use concurrent processing")
    parser.add_argument("--show_status", action="store_true", help="Show current translation status")
    args = parser.parse_args()

    # Set up OpenAI API
    openai.api_key = os.environ.get("API_KEY", "your-api-key")
    openai.api_base = os.environ.get("API_BASE", "your-api-base")
    
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
    
    
    # Auto-detect iteration number if not specified
    if args.iteration is None:
        args.iteration = get_iteration_number(args.folder)
        print(f"Auto-detected iteration number: {args.iteration}")
    
    if args.show_status:
        show_translation_status(args.folder, bugs, args.iteration)
        return
    
    # Create iteration-specific directories
    iter_folder = os.path.join(args.folder, f"iter_{args.iteration}")
    trans_folder = os.path.join(iter_folder, "translation")
    os.makedirs(trans_folder, exist_ok=True)
    
    # Load repair results and identify unsolved bugs
    print("Loading repair results from all iterations...")
    unsolved_bugs, solved_bugs = load_repair_results(args.folder, args.iteration)
    print(f"Found {len(unsolved_bugs)} unsolved bugs out of {len(bugs)} total bugs")
    # print(f"Found {len(solved_bugs)} solved bugs")
    
    if not unsolved_bugs:
        print("No unsolved bugs to translate!")
        return
    
    # Save args
    with open(os.path.join(trans_folder, "translate_args.txt"), "w") as f:
        f.write(str(args))
    
    # Choose processing method
    if args.concurrent and args.num_proc > 1:
        translate_concurrent(args, bugs, unsolved_bugs, trans_folder)
    else:
        translate_sequential(args, bugs, unsolved_bugs, trans_folder)


if __name__ == "__main__":
    main()