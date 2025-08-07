import argparse
import json
import os
import re
from difflib import unified_diff
from tqdm import tqdm

from agentless.multilang.const import LANGUAGE
from agentless.util.postprocess_data import (
    check_code_differ_by_just_empty_lines,
    check_syntax,
    fake_git_repo,
    parse_diff_edit_commands,
    parse_edit_commands,
    parse_str_replace_edit_commands,
    split_edit_multifile_commands,
    extract_python_blocks,
)
from agentless.util.utils import load_jsonl, setup_logger, cleanup_logger


def fix_malformed_patch_markers(patch_content: str) -> str:
    """Fix malformed SEARCH/REPLACE markers that might have extra characters."""
    # Fix endings like >>>>>>> REPLACE1 to >>>>>>> REPLACE
    patch_content = re.sub(r'>>>>>>> REPLACE\d+', '>>>>>>> REPLACE', patch_content)
    # Also fix potential issues with SEARCH markers
    patch_content = re.sub(r'<<<<<<< SEARCH\d+', '<<<<<<< SEARCH', patch_content)
    return patch_content

def split_patch_string_to_list(patch_string: str) -> list[str]:
    """Split a patch string containing multiple SEARCH/REPLACE blocks into a list of individual patches."""
    if not patch_string.strip():
        return []
    
    # Split by lines to process
    lines = patch_string.strip().split('\n')
    patches = []
    current_patch = []
    
    for line in lines:
        # Check if this is the start of a new file patch
        if line.strip().startswith('### ') and current_patch and any('<<<<<<< SEARCH' in l for l in current_patch):
            # Save the current patch
            patches.append('\n'.join(current_patch).strip())
            current_patch = [line]
        else:
            current_patch.append(line)
    
    # Don't forget the last patch
    if current_patch:
        patches.append('\n'.join(current_patch).strip())
    
    return patches

def apply_extracted_patches(
    extracted_patch: str,
    file_contents: dict[str, str],
    logger,
    file_loc_intervals: dict[str, list],
    diff_format=False,
    str_replace_format=False,
) -> tuple[list[str], list[str]]:
    """Apply already-extracted patches (not raw model output)."""
    edited_files = []
    new_contents = []
    
    if not extracted_patch.strip():
        logger.info("Empty patch content")
        return edited_files, new_contents
    
    # Fix malformed patch markers
    extracted_patch = fix_malformed_patch_markers(extracted_patch)
    logger.info(f"Fixed patch content:\n{extracted_patch}")
    
    try:
        # For already-extracted patches, we don't need to extract python blocks again
        # The patches are already in the correct format
        logger.info(f"Type of patches:\n{type(extracted_patch)}")
        logger.info(f"Number of SEARCH/REPLACE:\n{extracted_patch.count('SEARCH')} SEARCH, {extracted_patch.count('REPLACE')} REPLACE")
        # split the patch string into individual patches
        extracted_patch_list = split_patch_string_to_list(extracted_patch)
        logger.info(f"Number of patches after split: {len(extracted_patch_list)}")
        # logger.info(f"{extracted_patch_list}")
        file_to_commands = split_edit_multifile_commands(
            extracted_patch_list,
            diff_format=diff_format,
            str_replace_format=str_replace_format,
        )
    except Exception as e:
        logger.error(f"Error splitting commands: {e}")
        logger.error(f"Patch content that failed:\n{extracted_patch}")
        return edited_files, new_contents

    logger.info("=== file_to_commands: ===")
    logger.info(json.dumps(file_to_commands, indent=2))
    
    if not file_to_commands:
        logger.error("No commands extracted from patch")
        return edited_files, new_contents

    for edited_file_key in file_to_commands:
        edited_file = ""
        new_content = ""
        try:
            logger.info(f"=== edited_file: {edited_file_key} ===")
            edit_commands = file_to_commands[edited_file_key]
            logger.info("=== edit_commands: ===")
            for c in edit_commands:
                logger.info(c)
                logger.info("\n" + "-" * 40)
            
            # Extract the actual filename
            edited_file = eval(edited_file_key)  # convert '"file.py"' to 'file.py'
            
            # Check if file exists in file_contents
            if edited_file not in file_contents:
                logger.error(f"File {edited_file} not found in file_contents")
                logger.error(f"Available files: {list(file_contents.keys())}")
                continue
                
            content = file_contents[edited_file]
            
            if diff_format:
                new_content = parse_diff_edit_commands(
                    edit_commands, content, file_loc_intervals.get(edited_file, [])
                )
            elif str_replace_format:
                new_content = parse_str_replace_edit_commands(
                    edit_commands, content, file_loc_intervals.get(edited_file, [])
                )
            else:
                new_content = parse_edit_commands(edit_commands, content)
                
        except Exception as e:
            logger.error(f"Error processing file {edited_file_key}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            edited_file = ""
            new_content = ""

        if edited_file == "" or new_content == "":
            continue
            
        edited_files.append(edited_file)
        new_contents.append(new_content)
        
        diff = list(
            unified_diff(
                content.split("\n"),
                new_content.split("\n"),
                fromfile=edited_file,
                tofile=edited_file,
                lineterm="",
            )
        )

        logger.info(f"extracted patch:")
        logger.info("\n".join(diff))

    return edited_files, new_contents


def post_process_patch_application(args):
    """Process patch applications and generate output in the correct format."""
    patch_data_list = load_jsonl(args.patch_file)
    original_contexts = load_jsonl(args.original_context_file)
    
    # Create mapping from instance_id to original context
    original_contexts_map = {ctx["instance_id"]: ctx for ctx in original_contexts}
    
    for patch_data in tqdm(patch_data_list, total=len(patch_data_list), colour="GREEN"):
        instance_id = patch_data["instance_id"]
        
        if args.target_id is not None:
            if args.target_id != instance_id:
                continue
        
        log_file = os.path.join(args.output_folder, "patch_application_logs", f"{instance_id}.log")
        logger = setup_logger(log_file)
        
        logger.info(f"================ processing {instance_id} ================")
        
        # Get original context data
        if instance_id not in original_contexts_map:
            logger.error(f"original context not found for {instance_id}")
            # Write empty result
            with open(args.output_file, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "model_name_or_path": "agentless",
                            "instance_id": instance_id,
                            "model_patch": "",
                            "raw_model_patch": "",
                            "original_file_content": [],
                            "edited_files": [],
                            "new_file_content": [],
                        }
                    )
                    + "\n"
                )
            cleanup_logger(logger)
            continue
        
        original_context = original_contexts_map[instance_id]
        file_contents = original_context["file_contents"]
        file_loc_intervals = original_context["file_loc_intervals"]
        
        logger.info(f"Available files in context: {list(file_contents.keys())}")
        
        # Get translated patches
        translated_patches = patch_data.get("translated_patches", [])
        for i, item in enumerate(translated_patches):
            if item == []:
                translated_patches[i] = ""
        # Handle empty patches
        if not translated_patches or all(not patch.strip() for patch in translated_patches):
            logger.info("No translated patches found")
            with open(args.output_file, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "model_name_or_path": "agentless",
                            "instance_id": instance_id,
                            "model_patch": "",
                            "raw_model_patch": "",
                            "original_file_content": [],
                            "edited_files": [],
                            "new_file_content": [],
                        }
                    )
                    + "\n"
                )
            cleanup_logger(logger)
            continue
        
        # Select which patch to use
        if args.select_id == -1:
            # Use the last patch
            patch_idx = len(translated_patches) - 1
        else:
            # Use the specified index
            patch_idx = min(args.select_id, len(translated_patches) - 1)
        
        selected_patch = translated_patches[patch_idx]
        
        ept = False
        if isinstance(selected_patch, str):
            if not selected_patch.strip():
                ept = True
        elif isinstance(selected_patch, list):
            if len(selected_patch) == 0:
                ept = True
        if ept:
            # Empty patch
            logger.info(f"Empty patch at index {patch_idx}")
            with open(args.output_file, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "model_name_or_path": "agentless",
                            "instance_id": instance_id,
                            "model_patch": "",
                            "raw_model_patch": "",
                            "original_file_content": [],
                            "edited_files": [],
                            "new_file_content": [],
                        }
                    )
                    + "\n"
                )
            cleanup_logger(logger)
            continue
        
        logger.info(f"Using patch at index {patch_idx}")
        logger.info(f"Patch content:\n{selected_patch}")
        
        try:
            # Apply the selected patch
            edited_files, new_contents = apply_extracted_patches(
                selected_patch,
                file_contents,
                logger,
                file_loc_intervals,
                diff_format=args.diff_format,
                str_replace_format=args.str_replace_format,
            )
            
            if len(new_contents) == 0:
                logger.info("No files were edited")
                git_diffs = ""
                raw_git_diffs = ""
                contents = []
            else:
                # Generate git diff
                contents = [file_contents[edited_file] for edited_file in edited_files]
                git_diff = fake_git_repo("playground", edited_files, contents, new_contents)
                raw_git_diffs = git_diff.replace("\ No newline at end of file\n", "")
                
                # Check syntax and empty line differences
                # Get original language from context_data
                context_data = patch_data.get("context_data", {})
                original_language = context_data.get("original_language", "python")
                
                syntax_success = True if original_language.lower() != 'python' else check_syntax(new_contents)
                differ_by_empty_lines = check_code_differ_by_just_empty_lines(new_contents, contents)
                
                logger.info(f"{differ_by_empty_lines = }")
                logger.info(f"{syntax_success = }")
                
                if syntax_success and not differ_by_empty_lines:
                    git_diffs = raw_git_diffs
                else:
                    git_diffs = ""  # no need to evaluate
            
        except Exception as e:
            logger.error(f"Error processing patch: {e}")
            import traceback
            logger.error(traceback.format_exc())
            git_diffs = ""
            raw_git_diffs = ""
            contents = []
            edited_files = []
            new_contents = []
        
        # Write result in the expected format
        with open(args.output_file, "a") as f:
            f.write(
                json.dumps(
                    {
                        "model_name_or_path": "agentless",
                        "instance_id": instance_id,
                        "model_patch": git_diffs.lstrip() if git_diffs else "",
                        "raw_model_patch": raw_git_diffs.lstrip() if raw_git_diffs else "",
                        "original_file_content": contents,
                        "edited_files": edited_files,
                        "new_file_content": new_contents,
                    }
                )
                + "\n"
            )
        
        cleanup_logger(logger)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch_file", type=str, required=True, help="Path to translated patches file")
    parser.add_argument("--original_context_file", type=str, required=True, help="Path to original contexts file")
    parser.add_argument("--output_folder", type=str, required=True)
    parser.add_argument("--diff_format", action="store_true")
    parser.add_argument("--str_replace_format", action="store_true")
    parser.add_argument(
        "--select_id",
        type=int,
        default=-1,
        help="Index of the patch to select. -1 means process all samples.",
    )
    parser.add_argument("--target_id", type=str, help="Target specific instance ID")
    parser.add_argument(
        "--max_samples",
        type=int,
        default=2,
        help="Maximum number of samples to process when select_id is -1.",
    )
    
    args = parser.parse_args()
    
    # diff_format and str_replace_format cannot be both True
    assert not (
        args.diff_format and args.str_replace_format
    ), "Cannot use both diff_format and str_replace_format"
    
    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)
    if not os.path.exists(os.path.join(args.output_folder, "patch_application_logs")):
        os.makedirs(os.path.join(args.output_folder, "patch_application_logs"))
    
    with open(f"{args.output_folder}/patch_application_args.json", "w") as f:
        json.dump(vars(args), f, indent=4)
    
    # Check if we should process all samples or just one
    if args.select_id == -1:
        # Process all samples (similar to gen_and_process in repair.py)
        for i in range(args.max_samples):
            args.output_file = os.path.join(args.output_folder, f"output_{i}_processed.jsonl")
            args.select_id = i
            print(f"Processing sample {i}...")
            post_process_patch_application(args)
        print(f"Patch application completed for all {args.max_samples} samples.")
    else:
        # Process only the specified sample
        args.output_file = os.path.join(args.output_folder, f"output_{args.select_id}_processed.jsonl")
        post_process_patch_application(args)
        print(f"Patch application completed. Results saved to {args.output_file}")


if __name__ == "__main__":
    main()