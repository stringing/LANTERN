import argparse
import json
import os
import time
import concurrent.futures
import tqdm

import openai

from Dataset.dataset import parse_defects4j_12, parse_defects4j_2
from prompt import REPAIR_TRANSLATED_PROMPT, REPAIR_TRANSLATED_PROMPT_2
import util.util
from util.util import simple_chatgpt_parse, num_tokens_from_messages_offline

D4J_PATH = "/root/FSE_ChatRepair/code/Dataset/Defects4j/location"

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


def load_translation_results(trans_folder):
    """
    Load translation results from the translation folder
    """
    translations = {}
    if not os.path.exists(trans_folder):
        return translations
    
    result_files = [f for f in os.listdir(trans_folder) if f.endswith('_result.json') and '_trans_' in f]
    
    for result_file in result_files:
        try:
            with open(os.path.join(trans_folder, result_file), "r") as f:
                result = json.load(f)
                bug = result['bug']
                target_lang = result['target_lang']
                
                if bug not in translations:
                    translations[bug] = {}
                translations[bug][target_lang] = result
        except Exception as e:
            print(f"Error reading {result_file}: {e}")
    
    return translations


def get_file_extension(target_lang):
    """
    Get file extension for target language
    """
    extensions = {
        "Java": ".java",
        "C": ".c",
        "C++": ".cpp",
        "C#": ".cs",
        "Python": ".py",
        "Go": ".go",
        "Javascript": ".js",
        "Kotlin": ".kt",
        "PHP": ".php",
        "Ruby": ".rb",
        "Rust": ".rs"
    }
    return extensions.get(target_lang, ".txt")


def simple_code_parse(content):
    """
    Simple code parsing - extract code blocks or return content as is
    """
    # Try to extract code blocks first
    if "```" in content:
        lines = content.split('\n')
        in_code_block = False
        code_lines = []
        
        for line in lines:
            if line.strip().startswith("```"):
                if in_code_block:
                    break  # End of code block
                else:
                    in_code_block = True  # Start of code block
                continue
            
            if in_code_block:
                code_lines.append(line)
        
        if code_lines:
            return '\n'.join(code_lines)
    
    # If no code blocks, return the whole content
    return content.strip()


def process_single_translated_repair(repair_data, args, repair_folder, original_bugs):
    """
    Process repair for a single translated bug
    """
    bug, target_lang, translation_result, attempt = repair_data
    
    # Create repair result file path
    repair_result_file = os.path.join(
        repair_folder, 
        f"{bug.replace('.java', '')}_repair_{target_lang.lower()}_attempt_{attempt}_result.json"
    )
    
    # Skip if repair already exists
    if os.path.exists(repair_result_file):
        print(f"Skipping {bug} ({target_lang}) attempt {attempt} - repair already exists")
        return bug, target_lang, attempt, "skipped"
    
    # Get original bug info for test details
    if bug not in original_bugs:
        print(f"Error: {bug} not found in original dataset")
        return bug, target_lang, attempt, "failed"
    
    original_bug_info = original_bugs[bug]
    
    # Use unified prompt
    prompt = REPAIR_TRANSLATED_PROMPT.format(
        target_lang=target_lang,
        translated_buggy_code=translation_result['translated_code'],
        failing_test=original_bug_info['failing_tests'][0]['test_method_name'],
        error_message=original_bug_info['failing_tests'][0]['failure_message'].strip(),
        failing_line=original_bug_info['failing_tests'][0]['failing_line'].strip(),
        failing_test_function=original_bug_info['failing_tests'][0]['failing_function']
    )


    
    # Prepare messages for API call
    messages = [
        {"role": "system", "content": f"You are an automated program repair tool."},
        {"role": "user", "content": prompt}
    ]
    
    print(f"Repairing {bug} ({target_lang}) attempt {attempt}...")
    
    # Make API call
    ret = gen(messages, temperature=args.temperature, nsample=1)
    
    if ret is None:
        print(f"Failed to get response for {bug} ({target_lang}) attempt {attempt}")
        return bug, target_lang, attempt, "failed"
    
    # Parse the response
    repaired_code, _ = simple_chatgpt_parse(ret["choices"][0]['message']["content"])
    
    if repaired_code != "":
        print(f"Generated repair for {bug} ({target_lang}) attempt {attempt}")
        
        # Save the repaired code to file
        file_ext = get_file_extension(target_lang)
        output_file = os.path.join(
            repair_folder,
            bug.split(".java")[0] + f"_repair_{target_lang.lower()}_attempt_{attempt}{file_ext}"
        )
        
        try:
            with open(output_file, "w") as f:
                f.write(repaired_code)
            print(f"Saved repaired code to {output_file}")
            save_success = True
        except Exception as e:
            print(f"Failed to save file: {e}")
            save_success = False
        
        # Create result entry (no validation at this step)
        result_entry = {
            'bug': bug,
            'target_lang': target_lang,
            'attempt': attempt,
            'original_translated_code': translation_result['translated_code'],
            'repaired_code': repaired_code,
            'saved': save_success,
            'output_file': output_file if save_success else None,
            'prompt': messages,
            'output': ret,
            'iteration': args.iteration,
            'timestamp': time.time(),
            'translation_info': {
                'source_lang': translation_result['source_lang'],
                'target_lang': translation_result['target_lang']
            }
        }
        
        # Save repair result
        with open(repair_result_file, "w") as f:
            json.dump(result_entry, f, indent=2)
        
        print(f"Repair {bug} ({target_lang}) attempt {attempt}: Saved={save_success} - Result saved to {repair_result_file}")
            
        return bug, target_lang, attempt, "completed"
    else:
        print(f"No valid code extracted for {bug} ({target_lang}) attempt {attempt}")
        
        # Save failure result
        result_entry = {
            'bug': bug,
            'target_lang': target_lang,
            'attempt': attempt,
            'original_translated_code': translation_result['translated_code'],
            'repaired_code': None,
            'saved': False,
            'output_file': None,
            'prompt': messages,
            'error': "No valid code extracted",
            'output': ret,
            'iteration': args.iteration,
            'timestamp': time.time()
        }
        
        with open(repair_result_file, "w") as f:
            json.dump(result_entry, f, indent=2)
            
        return bug, target_lang, attempt, "no_repair"


def repair_translated_concurrent(args, translations, repair_folder, original_bugs):
    """
    Process translated repairs concurrently
    """
    # Create repair tasks
    repair_tasks = []
    for bug, lang_translations in translations.items():
        for target_lang, translation_result in lang_translations.items():
            for attempt in range(args.nattempt):
                repair_tasks.append((bug, target_lang, translation_result, attempt))
    
    if not repair_tasks:
        print("No repair tasks to process")
        return
    
    print(f"Processing {len(repair_tasks)} repair tasks concurrently...")
    
    # Process repairs concurrently
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.num_proc) as executor:
        futures = []
        
        # Submit all jobs
        for repair_data in repair_tasks:
            future = executor.submit(process_single_translated_repair, repair_data, args, repair_folder, original_bugs)
            futures.append(future)
        
        # Collect results as they complete
        completed = 0
        skipped = 0
        failed = 0
        saved_repairs = 0
        
        for future in tqdm.tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Processing repairs"
        ):
            try:
                bug, target_lang, attempt, status = future.result()
                if status == "completed":
                    completed += 1
                    # Check if it was saved by reading the result file
                    repair_result_file = os.path.join(
                        repair_folder,
                        f"{bug.replace('.java', '')}_repair_{target_lang.lower()}_attempt_{attempt}_result.json"
                    )
                    try:
                        with open(repair_result_file, "r") as f:
                            result = json.load(f)
                            if result.get('saved', False):
                                saved_repairs += 1
                    except:
                        pass
                elif status == "skipped":
                    skipped += 1
                elif status == "failed":
                    failed += 1
                    
            except Exception as e:
                print(f"Error occurred: {e}")
                failed += 1
    
    print(f"\nRepair Summary for Iteration {args.iteration}:")
    print(f"  Total tasks: {len(repair_tasks)}")
    print(f"  Completed: {completed}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed: {failed}")
    print(f"  Successfully saved: {saved_repairs}")
    
    # Create repair summary
    summary = {
        'iteration': args.iteration,
        'total_repair_tasks': len(repair_tasks),
        'completed': completed,
        'skipped': skipped,
        'failed': failed,
        'saved_repairs': saved_repairs,
        'timestamp': time.time()
    }
    
    with open(os.path.join(repair_folder, "repair_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)


def repair_translated_sequential(args, translations, repair_folder, original_bugs):
    """
    Process translated repairs sequentially
    """
    for bug, lang_translations in translations.items():
        for target_lang, translation_result in lang_translations.items():
            print(f"---- {bug} ({target_lang}) ----")
            for attempt in range(args.nattempt):
                print(f"  Attempt {attempt + 1}/{args.nattempt}")
                process_single_translated_repair((bug, target_lang, translation_result, attempt), args, repair_folder, original_bugs)



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=str, default="Results/test", help="Base folder for results")
    parser.add_argument("--iteration", type=int, required=True, help="Iteration number")
    parser.add_argument("--dataset", type=str, default="defects4j-1.2-function")
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--num_proc", type=int, default=1, help="Number of parallel processes")
    parser.add_argument("--nattempt", type=int, default=1, help="Number of attempts for each translated bug")
    parser.add_argument("--concurrent", action="store_true", help="Use concurrent processing")
    args = parser.parse_args()

    # Set up OpenAI API
    openai.api_key = os.environ.get("API_KEY", "your-api-key")
    openai.api_base = os.environ.get("API_BASE", "your-api-base")
    
    # Create iteration-specific directories
    iter_folder = os.path.join(args.folder, f"iter_{args.iteration}")
    trans_folder = os.path.join(iter_folder, "translation")
    repair_folder = os.path.join(iter_folder, "repair")
    os.makedirs(repair_folder, exist_ok=True)
    
    # Load original dataset (needed for test information)
    if args.dataset == "defects4j-1.2-function":
        original_bugs = parse_defects4j_12("../Dataset/")
    elif args.dataset == "defects4j-1.2-single-hunk":
        original_bugs = parse_defects4j_12("../Dataset/", single_hunk=True)
    elif args.dataset == "defects4j-1.2-single-line":
        original_bugs = parse_defects4j_12("../Dataset/", single_line=True)
    elif args.dataset == "defects4j-2.0-single-line":
        original_bugs = parse_defects4j_2("../Dataset/")
    else:
        raise NotImplementedError(f"Dataset {args.dataset} not supported")
    
    # Load translation results
    print(f"Loading translation results from {trans_folder}...")
    translations = load_translation_results(trans_folder)
    
    if not translations:
        print(f"No translation results found in {trans_folder}")
        return
    
    print(f"Found translations for {len(translations)} bugs")
    total_translations = sum(len(lang_trans) for lang_trans in translations.values())
    print(f"Total translation-language pairs: {total_translations}")
    
    # Save args
    with open(os.path.join(repair_folder, "repair_translated_args.txt"), "w") as f:
        f.write(str(args))
    

    # Choose processing method
    if args.concurrent and args.num_proc > 1:
        repair_translated_concurrent(args, translations, repair_folder, original_bugs)
    else:
        repair_translated_sequential(args, translations, repair_folder, original_bugs)


if __name__ == "__main__":
    main()