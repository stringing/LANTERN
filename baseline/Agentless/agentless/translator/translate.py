import argparse
import concurrent.futures
import json
import os
from threading import Lock
from tqdm import tqdm

from agentless.util.model import make_model
from agentless.util.utils import load_jsonl, setup_logger

# Language file extensions mapping
LANGUAGE_EXTENSIONS = {
    "Python": "py",
    "C": "c", 
    "C++": "cpp",
    "Java": "java",
    "Javascript": "js",
    "Typescript": "ts",
    "Go": "go",
    "Rust": "rs"
}

TRANSLATION_PROMPT = """
Here is one or more code segments in {original} programming language, separated by file names. Translate the segment from {original} to {target}. Note that it is just a segment of code. You only need to translate each segment and do not complete the code at the beginning or the end where it was truncated. Do not add extra brackets even if the brackets are not closed either at the beginning or the end. Keep the ellipses at the beginning and the end for each segment. The suffix of each file name should also be changed to corresponding language. Provide the translated code without any description or extra tokens. 

{code_with_context}
"""


def get_original_language():
    """Get the original programming language. """
    # This could be made configurable or detected from the code
    return os.environ.get('SWEBENCH_LANG', 'python').lower()


def translate_filename_extensions(content, target_language):
    """Replace file extensions in the content to match target language."""
    if target_language not in LANGUAGE_EXTENSIONS:
        return content
    
    target_ext = LANGUAGE_EXTENSIONS[target_language]
    lines = content.split('\n')
    translated_lines = []
    
    for line in lines:
        # Look for lines that start with "### " which indicate file names
        if line.startswith('### ') and '.' in line:
            # Extract the filename and change its extension
            filename = line[4:]  # Remove "### "
            if '.' in filename:
                name_part = filename.rsplit('.', 1)[0]
                new_filename = f"{name_part}.{target_ext}"
                translated_lines.append(f"### {new_filename}")
            else:
                translated_lines.append(line)
        else:
            translated_lines.append(line)
    
    return '\n'.join(translated_lines)


def translate_instance(context_data, target_language, args, write_lock=None):
    """Translate code for a single instance."""
    instance_id = context_data["instance_id"]
    
    if args.target_id is not None:
        if args.target_id != instance_id:
            return None
    
    log_file = os.path.join(args.output_folder, "translation_logs", f"{instance_id}.log")
    logger = setup_logger(log_file)
    
    logger.info(f"================ translating {instance_id} to {target_language} ================")
    
    # Check if already processed
    if os.path.exists(args.output_file):
        existing_translations = load_jsonl(args.output_file)
        for existing in existing_translations:
            if existing["instance_id"] == instance_id:
                logger.info(f"skipping {instance_id} since translation already exists")
                return None
    
    topn_content = context_data["topn_content"]
    
    # Skip instances with empty context
    if topn_content.strip() == "":
        logger.info(f"skipping {instance_id} due to empty context")
        return None
    
    original_language = get_original_language()
    
    # Skip if target language is the same as original
    if target_language.lower() == original_language.lower():
        logger.info(f"skipping {instance_id} since target language {target_language} is same as original {original_language}")
        # Still save the original context data but mark it as not translated
        translated_context = context_data.copy()
        translated_context["target_language"] = target_language
        translated_context["translated"] = False
    else:
        # Construct translation prompt
        message = TRANSLATION_PROMPT.format(
            original=original_language,
            target=target_language,
            code_with_context=topn_content
        )
        
        logger.info(f"translating with prompt:\n{message}")
        
        if args.mock:
            # Mock translation for testing
            translated_code = topn_content
        else:
            # Get translation from model
            model = make_model(
                model=args.model,
                logger=logger,
                backend=args.backend,
                max_tokens=4096,  # Allow more tokens for translation
                temperature=0.2,
                batch_size=1,
            )
            
            try:
                response = model.codegen(message, num_samples=1)[0]
                translated_code = response["response"]
                logger.info(f"translated code:\n{translated_code}")
            except Exception as e:
                logger.error(f"Translation failed: {e}")
                translated_code = topn_content  # Fallback to original
        
        # Update file extensions in the translated code
        # translated_code = translate_filename_extensions(translated_code, target_language)
        
        # Create translated context data
        translated_context = context_data.copy()
        translated_context["topn_content"] = translated_code
        translated_context["target_language"] = target_language
        translated_context["original_language"] = original_language
        translated_context["translated"] = True
    
    # Write to output file
    if write_lock is not None:
        write_lock.acquire()
    try:
        with open(args.output_file, "a") as f:
            f.write(json.dumps(translated_context) + "\n")
    finally:
        if write_lock is not None:
            write_lock.release()
    
    logger.info(f"translation completed for {instance_id}")
    return translated_context

def get_resolved(args):
    resolved_ids = set()
    initial_resolved_file = "/root/SWE-bench/agentless.al.json"
    with open(initial_resolved_file, "r") as f:
        data = json.load(f)
        resolved_ids.update(data.get("resolved_ids", []))
    for i in range(1, args.it):
        resolved_file = f"/root/SWE-bench/agentless.tr_{i}.json"
        if os.path.exists(resolved_file):
            with open(resolved_file, "r") as f:
                data = json.load(f)
                resolved_ids.update(data.get("resolved_ids", []))
    # save the already resolved ids
    save_dir = os.path.dirname(args.output_folder)
    with open(os.path.join(save_dir, 'resolved_ids.json'), "w") as f:
        json.dump({"resolved_ids": list(resolved_ids)}, f, indent=4)
    print(f"Total resolved ids: {len(resolved_ids)}")
    return resolved_ids

def translate_code(args):
    """Main function to translate code for all instances."""
    with open(f"{args.output_folder}/translation_args.json", "w") as f:
        json.dump(vars(args), f, indent=4)
    
    # Load contexts and language selections
    contexts = load_jsonl(args.context_file)
    language_selections = load_jsonl(args.language_file)
    
    # Create mapping from instance_id to target_language
    lang_map = {sel["instance_id"]: sel["target_language"] for sel in language_selections}
    
    resolved_ids = get_resolved(args)
    # Filter contexts to only those with language selections
    contexts_to_translate = []
    for context in contexts:
        instance_id = context["instance_id"]
        if instance_id in resolved_ids:
            continue
        if instance_id in lang_map:
            contexts_to_translate.append((context, lang_map[instance_id]))
    
    print(f"Found {len(contexts_to_translate)} instances to translate")
    
    if args.num_threads == 1:
        for context_data, target_language in tqdm(contexts_to_translate, total=len(contexts_to_translate), colour="YELLOW"):
            translate_instance(context_data, target_language, args)
    else:
        write_lock = Lock()
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.num_threads) as executor:
            futures = {
                executor.submit(translate_instance, context_data, target_language, args, write_lock): (context_data, target_language)
                for context_data, target_language in contexts_to_translate
            }
            for future in tqdm(
                concurrent.futures.as_completed(futures),
                total=len(contexts_to_translate),
                colour="YELLOW",
            ):
                future.result()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context_file", type=str, required=True, help="Path to prepared contexts file")
    parser.add_argument("--language_file", type=str, required=True, help="Path to language selections file")
    parser.add_argument("--output_folder", type=str, required=True)
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-2024-05-13",
        choices=[
            "gpt-4o-2024-05-13",
            "deepseek-coder",
            "gpt-4o-mini-2024-07-18",
            "claude-3-5-sonnet-20241022",
        ],
    )
    parser.add_argument(
        "--backend",
        type=str,
        default="openai",
        choices=["openai", "deepseek", "anthropic"],
    )
    parser.add_argument(
        "--num_threads",
        type=int,
        default=1,
        help="Number of threads to use for translation requests",
    )
    parser.add_argument(
        "--it",
        type=int,
        default=1,
        help="Current iteration",
    )
    parser.add_argument("--target_id", type=str, help="Target specific instance ID")
    parser.add_argument(
        "--mock", action="store_true", help="Mock run without actual translation."
    )
    
    args = parser.parse_args()
    
    assert (not "deepseek" in args.model) or (
        args.backend == "deepseek"
    ), "Must specify `--backend deepseek` if using a DeepSeek model"
    
    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)
    if not os.path.exists(os.path.join(args.output_folder, "translation_logs")):
        os.makedirs(os.path.join(args.output_folder, "translation_logs"))
    
    args.output_file = os.path.join(args.output_folder, "translated_contexts.jsonl")
    
    translate_code(args)
    print(f"Translation completed. Results saved to {args.output_file}")


if __name__ == "__main__":
    main()