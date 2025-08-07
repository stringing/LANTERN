import argparse
import concurrent.futures
import json
import os
import re
from threading import Lock
from tqdm import tqdm

from agentless.util.model import make_model
from agentless.util.utils import load_jsonl, setup_logger

BACK_TRANSLATION_PROMPT = """Here is one or more buggy code segment in {original_language} programming language.

{original_code_segments}

Here is the {target_language} version of patches solving the same bug in the SEARCH/REPLACE format (each starts with the file name) for the buggy code segments. Can you map the SEARCH part of each patch to the corresponding part in the {original_language} code segments and translate the REPLACE part from {target_language} to {original_language}? Finally, generate corresponding {original_language} version of SEARCH/REPLACE patches for the {original_language} code segments. You should also change the suffix of file names at the beginning of each patch. Provide only the patches without any description or extra tokens (starts with the file name).

{patches_in_target_language}"""


def extract_original_context_data(context_data):
    """Extract original context data from translated context data."""
    # Load original contexts to get the original code segments
    original_context = {
        "instance_id": context_data["instance_id"],
        "topn_content": context_data.get("original_topn_content", ""),
        "file_contents": context_data.get("original_file_contents", {}),
        "file_loc_intervals": context_data["file_loc_intervals"],
        "pred_files": context_data["pred_files"],
        "problem_statement": context_data["problem_statement"],
    }
    return original_context


def get_original_language(context_data):
    """Get the original programming language."""
    return context_data.get("original_language", "python")


def translate_patches_back_for_instance(patch_data, original_contexts_map, args, write_lock=None):
    """Translate patches back to original language for a single instance."""
    instance_id = patch_data["instance_id"]
    
    if args.target_id is not None:
        if args.target_id != instance_id:
            return None
    
    log_file = os.path.join(args.output_folder, "patch_translation_logs", f"{instance_id}.log")
    logger = setup_logger(log_file)
    
    logger.info(f"================ translating patches back for {instance_id} ================")
    
    # Check if already processed
    if os.path.exists(args.output_file):
        existing_translations = load_jsonl(args.output_file)
        for existing in existing_translations:
            if existing["instance_id"] == instance_id:
                logger.info(f"skipping {instance_id} since patch translation already exists")
                return None
    
    context_data = patch_data["context_data"]
    extracted_patches = patch_data.get("extracted_patches", [])
    
    # Skip instances with empty patches
    if not extracted_patches or all(len(patch) == 0 for patch in extracted_patches):
        logger.info(f"skipping {instance_id} due to empty patches")
        translated_patch_data = patch_data.copy()
        translated_patch_data["translated_patches"] = extracted_patches
        translated_patch_data["translation_successful"] = False
        
        if write_lock is not None:
            write_lock.acquire()
        try:
            with open(args.output_file, "a") as f:
                f.write(json.dumps(translated_patch_data) + "\n")
        finally:
            if write_lock is not None:
                write_lock.release()
        return None
    
    original_language = get_original_language(context_data)
    target_language = context_data.get("target_language", "")
    
    # Skip if target language is the same as original or if not translated
    if (target_language.lower() == original_language.lower() or 
        not context_data.get("translated", False)):
        logger.info(f"skipping {instance_id} since no translation needed")
        translated_patch_data = patch_data.copy()
        translated_patch_data["translated_patches"] = extracted_patches
        translated_patch_data["translation_successful"] = False
        
        if write_lock is not None:
            write_lock.acquire()
        try:
            with open(args.output_file, "a") as f:
                f.write(json.dumps(translated_patch_data) + "\n")
        finally:
            if write_lock is not None:
                write_lock.release()
        return None
    
    # Get original context data
    if instance_id in original_contexts_map:
        original_context = original_contexts_map[instance_id]
        original_code_segments = original_context["topn_content"]
    else:
        logger.error(f"original context not found for {instance_id}")
        return None
    
    translated_patches = []
    
    for i, extracted_patch in enumerate(extracted_patches):
        if len(extracted_patch) == 0:
            translated_patches.append("")
            continue
        
        logger.info(f"translating patch {i+1}/{len(extracted_patches)}")
        
        # Construct back-translation prompt
        message = BACK_TRANSLATION_PROMPT.format(
            original_language=original_language,
            target_language=target_language,
            original_code_segments=original_code_segments,
            patches_in_target_language=extracted_patch
        )
        
        logger.info(f"back-translating with prompt:\n{message}")
        
        if args.mock:
            # Mock translation for testing
            translated_patch = extracted_patch
        else:
            # Get back-translation from model
            model = make_model(
                model=args.model,
                logger=logger,
                backend=args.backend,
                max_tokens=4096,
                temperature=0,
                batch_size=1,
            )
            
            try:
                response = model.codegen(message, num_samples=1)[0]
                translated_patch = response["response"]
                logger.info(f"back-translated patch:\n{translated_patch}")
            except Exception as e:
                logger.error(f"Back-translation failed: {e}")
                translated_patch = extracted_patch  # Fallback to original
        
        translated_patches.append(translated_patch)
    
    # Create translated patch data
    translated_patch_data = patch_data.copy()
    translated_patch_data["translated_patches"] = translated_patches
    translated_patch_data["original_patches"] = extracted_patches
    translated_patch_data["translation_successful"] = True
    
    # Write to output file
    if write_lock is not None:
        write_lock.acquire()
    try:
        with open(args.output_file, "a") as f:
            f.write(json.dumps(translated_patch_data) + "\n")
    finally:
        if write_lock is not None:
            write_lock.release()
    
    logger.info(f"patch back-translation completed for {instance_id}")
    return translated_patch_data


def translate_patches_back(args):
    """Main function to translate patches back for all instances."""
    with open(f"{args.output_folder}/patch_translation_args.json", "w") as f:
        json.dump(vars(args), f, indent=4)
    
    # Load patch data and original contexts
    patch_data_list = load_jsonl(args.patch_file)
    original_contexts = load_jsonl(args.original_context_file)
    
    # Create mapping from instance_id to original context
    original_contexts_map = {ctx["instance_id"]: ctx for ctx in original_contexts}
    
    print(f"Found {len(patch_data_list)} patch instances to translate back")
    
    if args.num_threads == 1:
        for patch_data in tqdm(patch_data_list, total=len(patch_data_list), colour="CYAN"):
            translate_patches_back_for_instance(patch_data, original_contexts_map, args)
    else:
        write_lock = Lock()
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.num_threads) as executor:
            futures = {
                executor.submit(translate_patches_back_for_instance, patch_data, original_contexts_map, args, write_lock): patch_data
                for patch_data in patch_data_list
            }
            for future in tqdm(
                concurrent.futures.as_completed(futures),
                total=len(patch_data_list),
                colour="CYAN",
            ):
                future.result()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch_file", type=str, required=True, help="Path to raw patches file")
    parser.add_argument("--original_context_file", type=str, required=True, help="Path to original contexts file")
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
    if not os.path.exists(os.path.join(args.output_folder, "patch_translation_logs")):
        os.makedirs(os.path.join(args.output_folder, "patch_translation_logs"))
    
    args.output_file = os.path.join(args.output_folder, "translated_patches.jsonl")
    
    translate_patches_back(args)
    print(f"Patch back-translation completed. Results saved to {args.output_file}")


if __name__ == "__main__":
    main()