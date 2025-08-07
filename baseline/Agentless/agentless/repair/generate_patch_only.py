import argparse
import concurrent.futures
import json
import os
from threading import Lock

from tqdm import tqdm

from agentless.multilang.const import get_config
from agentless.util.api_requests import num_tokens_from_messages
from agentless.util.model import make_model
from agentless.util.postprocess_data import (
    extract_python_blocks,
    split_edit_multifile_commands,
)
from agentless.util.utils import load_jsonl, setup_logger

repair_relevant_file_instruction = """
Below are some code segments, each from a relevant file. One or more of these files may contain bugs.
"""

repair_prompt_combine_topn = """
We are currently solving the following issue within our repository. Here is the issue text:
--- BEGIN ISSUE ---
{problem_statement}
--- END ISSUE ---

{repair_relevant_file_instruction}
--- BEGIN FILE ---
{content}
--- END FILE ---

Please generate `edit_file` commands to fix the issue.

The `edit_file` command takes four arguments:

edit_file(filename: str, start: int, end: int, content: str) -> None:
    Edit a file. It replaces lines `start` through `end` (inclusive) with the given text `content` in the open file.
    Args:
    filename: str: The full file name to edit.
    start: int: The start line number. Must satisfy start >= 1.
    end: int: The end line number. Must satisfy start <= end <= number of lines in the file.
    content: str: The content to replace the lines with.

Please note that THE `edit_file` FUNCTION REQUIRES PROPER INDENTATION. If you would like to add the line '        print(x)', you must fully write that out, with all those spaces before the code!
Wrap the `edit_file` command in blocks ```python...```.
"""

repair_prompt_combine_topn_cot = """
We are currently solving the following issue within our repository. Here is the issue text:
--- BEGIN ISSUE ---
{problem_statement}
--- END ISSUE ---

{repair_relevant_file_instruction}
--- BEGIN FILE ---
{content}
--- END FILE ---

Please first localize the bug based on the issue statement, and then generate `edit_file` commands to fix the issue.

The `edit_file` command takes four arguments:

edit_file(filename: str, start: int, end: int, content: str) -> None:
    Edit a file. It replaces lines `start` through `end` (inclusive) with the given text `content` in the open file.
    Args:
    filename: str: The full file name to edit.
    start: int: The start line number. Must satisfy start >= 1.
    end: int: The end line number. Must satisfy start <= end <= number of lines in the file.
    content: str: The content to replace the lines with.

Please note that THE `edit_file` FUNCTION REQUIRES PROPER INDENTATION. If you would like to add the line '        print(x)', you must fully write that out, with all those spaces before the code!
Wrap the `edit_file` command in blocks ```python...```.
"""

repair_prompt_combine_topn_cot_diff = """
We are currently solving the following issue within our repository. Here is the issue text:
--- BEGIN ISSUE ---
{problem_statement}
--- END ISSUE ---

{repair_relevant_file_instruction}
--- BEGIN FILE ---
{content}
--- END FILE ---

Please first localize the bug based on the issue statement, and then generate *SEARCH/REPLACE* edits to fix the issue.

Every *SEARCH/REPLACE* edit must use this format:
1. The file path
2. The start of search block: <<<<<<< SEARCH
3. A contiguous chunk of lines to search for in the existing source code
4. The dividing line: =======
5. The lines to replace into the source code
6. The end of the replace block: >>>>>>> REPLACE

Here is an example:

{example}

Please note that the *SEARCH/REPLACE* edit REQUIRES PROPER INDENTATION. If you would like to add the line '        print(x)', you must fully write that out, with all those spaces before the code!
Wrap the *SEARCH/REPLACE* edit in blocks ```{language}...```.
"""

repair_prompt_combine_topn_cot_str_replace = """
We are currently solving the following issue within our repository. Here is the issue text:
--- BEGIN ISSUE ---
{problem_statement}
--- END ISSUE ---

{repair_relevant_file_instruction}
--- BEGIN FILE ---
{content}
--- END FILE ---

Please first localize the bug based on the issue statement, and then generate editing commands to fix the issue.
"""


def extract_patches_from_raw_output(raw_output, args, logger, target_language):
    """Extract actual patches from raw model output."""
    if not raw_output.strip():
        return ""
    
    try:
        if not args.str_replace_format:
            # Extract code blocks (edit_file commands or SEARCH/REPLACE blocks)
            edit_multifile_commands = extract_python_blocks(raw_output, target_language)
        else:
            # For str_replace format, use the raw output directly
            edit_multifile_commands = raw_output
        
        if args.diff_format or args.str_replace_format:
            # For diff/str_replace format, return the extracted commands as-is
            return edit_multifile_commands
        else:
            # For edit_file format, also return the extracted commands
            return edit_multifile_commands
            
    except Exception as e:
        logger.error(f"Error extracting patches: {e}")
        return ""


def construct_prompt(context_data, args):
    """Construct the prompt from context data."""
    topn_content = context_data["topn_content"]
    problem_statement = context_data["problem_statement"]
    target_language = context_data["target_language"]
    
    if topn_content.strip() == "":
        return ""
    
    prompt_template = (
        repair_prompt_combine_topn_cot_str_replace
        if args.cot and args.str_replace_format
        else repair_prompt_combine_topn_cot_diff
        if args.cot and args.diff_format
        else repair_prompt_combine_topn_cot
        if args.cot
        else repair_prompt_combine_topn
    )
    
    file_instruction = repair_relevant_file_instruction
    prompt = prompt_template.format(
        repair_relevant_file_instruction=file_instruction,
        problem_statement=problem_statement,
        content=topn_content.rstrip(),
        language=target_language,
        example=get_config(target_language)['DIFF_EXAMPLE'],
    ).strip()
    
    return prompt


def generate_patches_for_instance(context_data, args, write_lock=None):
    """Generate patches for a single instance using prepared context."""
    instance_id = context_data["instance_id"]

    if args.target_id is not None:
        if args.target_id != instance_id:
            return

    log_file = os.path.join(args.output_folder, "patch_generation_logs", f"{instance_id}.log")
    logger = setup_logger(log_file)

    # Check if already processed
    prev_o = load_jsonl(args.output_file) if os.path.exists(args.output_file) else []
    found = False
    for o in prev_o:
        if o["instance_id"] == instance_id:
            found = True
            break

    if found:
        logger.info(f"skipping {instance_id} since patches already generated")
        return None

    logger.info(f"================ generating patches for {instance_id} ================")

    # Construct prompt from context data
    message = construct_prompt(context_data, args)
    
    # Check if context/prompt is empty
    if message.strip() == "":
        if write_lock is not None:
            write_lock.acquire()
        with open(args.output_file, "a") as f:
            f.write(
                json.dumps(
                    {
                        "instance_id": instance_id,
                        "raw_outputs": [""],
                        "extracted_patches": [""],
                        "try_count": [0],
                        "all_raw_generations": [[]],
                        "all_extracted_patches": [[]],
                        "traj": [],
                        "context_data": context_data,
                    }
                )
                + "\n"
            )
        if write_lock is not None:
            write_lock.release()
        return

    logger.info(f"prompting with message:\n{message}")

    raw_outputs, extracted_patches, counts, all_raw_generations, all_extracted_patches, traj = [], [], [], [], [], []

    sample_responses = []
    
    # Get greedy sample
    model = make_model(
        model=args.model,
        logger=logger,
        backend=args.backend,
        max_tokens=1024,
        temperature=0,
        batch_size=1,
    )
    
    if args.skip_greedy:
        greedy_traj = {
            "response": "",
            "usage": {
                "completion_tokens": 0,
                "prompt_tokens": 0,
            },
        }
    else:
        if args.mock:
            greedy_traj = {
                "response": "",
                "usage": {
                    "prompt_tokens": num_tokens_from_messages(message, args.model),
                },
            }
        else:
            if args.str_replace_format:
                greedy_traj = model.codegen_w_tool(
                    message, num_samples=1, prompt_cache=args.max_samples > 1
                )[0]
            else:
                greedy_traj = model.codegen(
                    message, num_samples=1, prompt_cache=args.max_samples > 1
                )[0]

    sample_responses.append(greedy_traj)
    
    # Get temperature samples
    model = make_model(
        model=args.model,
        logger=logger,
        backend=args.backend,
        max_tokens=1024,
        temperature=0.8,
        batch_size=args.max_samples - 1,  # minus the 1 greedy sample
    )

    if args.mock:
        first_traj = {
            "response": "",
            "usage": {
                "prompt_tokens": num_tokens_from_messages(message, args.model),
            },
        }
        later_traj = {
            "response": "",
            "usage": {"prompt_tokens": 0},
        }
        if args.max_samples - 1:
            sample_trajs = [first_traj] + [later_traj] * (args.max_samples - 2)
        else:
            sample_trajs = []
    else:
        if args.max_samples - 1:
            # always use cached prompt if possible for later samples
            if args.str_replace_format:
                sample_trajs = model.codegen_w_tool(
                    message, num_samples=args.max_samples - 1, prompt_cache=True
                )
            else:
                sample_trajs = model.codegen(
                    message, num_samples=args.max_samples - 1, prompt_cache=True
                )
        else:
            sample_trajs = []

    sample_responses.extend(sample_trajs)

    target_language = context_data["target_language"]
    count = 0
    while count < args.max_samples:
        print(f"trying the {count + 1}-th sample ...")
        ret = sample_responses[count]
        count += 1
        traj.append({**ret, "prompt": message})

        if args.mock:
            continue

        raw_output = ret["response"]
        logger.info(f"raw output:\n{raw_output}")
        all_raw_generations.append(raw_output)
        
        # Extract actual patches from raw output
        extracted_patch = extract_patches_from_raw_output(raw_output, args, logger, target_language)
        logger.info(f"extracted patch:\n{extracted_patch}")
        all_extracted_patches.append(extracted_patch)
        
        counts.append(count)
        raw_outputs.append(raw_output)
        extracted_patches.append(extracted_patch)

    if write_lock is not None:
        write_lock.acquire()
    with open(args.output_file, "a") as f:
        f.write(
            json.dumps(
                {
                    "instance_id": instance_id,
                    "raw_outputs": raw_outputs,
                    "extracted_patches": extracted_patches,  # These are the actual patches to be back-translated
                    "all_raw_generations": [all_raw_generations],
                    "all_extracted_patches": [all_extracted_patches],
                    "try_count": counts,
                    "traj": traj,
                    "context_data": context_data,  # Save context data for back-translation
                }
            )
            + "\n"
        )
    if write_lock is not None:
        write_lock.release()


def generate_patches(args):
    """Main function to generate patches for all instances."""
    with open(f"{args.output_folder}/patch_generation_args.json", "w") as f:
        json.dump(vars(args), f, indent=4)

    # Load prepared contexts
    all_contexts = load_jsonl(args.context_file)

    # Load resolved IDs to skip already resolved instances
    resolved_file = os.path.join(os.path.dirname(args.output_folder), "resolved_ids.json")
    with open(resolved_file, "r") as f:
        resolved_data = json.load(f)
        resolved_ids = resolved_data.get("resolved_ids", [])
    contexts = [
        context for context in all_contexts if context["instance_id"] not in resolved_ids
    ]

    if args.num_threads == 1:
        for context_data in tqdm(contexts, total=len(contexts), colour="BLUE"):
            generate_patches_for_instance(context_data, args)
    else:
        write_lock = Lock()
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=args.num_threads
        ) as executor:
            futures = {
                executor.submit(
                    generate_patches_for_instance, context_data, args, write_lock
                ): context_data
                for context_data in contexts
            }
            for future in tqdm(
                concurrent.futures.as_completed(futures),
                total=len(contexts),
                colour="BLUE",
            ):
                future.result()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context_file", type=str, required=True, help="Path to prepared contexts file")
    parser.add_argument("--max_samples", type=int, default=20, help="Sampling budget.")
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
    parser.add_argument("--output_folder", type=str, required=True)
    parser.add_argument("--cot", action="store_true")
    parser.add_argument("--diff_format", action="store_true")
    parser.add_argument("--str_replace_format", action="store_true")
    parser.add_argument("--skip_greedy", action="store_true")
    parser.add_argument(
        "--num_threads",
        type=int,
        default=1,
        help="Number of threads to use for creating API requests",
    )
    parser.add_argument("--target_id", type=str)
    parser.add_argument(
        "--mock", action="store_true", help="Mock run to compute prompt tokens."
    )

    args = parser.parse_args()

    assert (not "deepseek" in args.model) or (
        args.backend == "deepseek"
    ), "Must specify `--backend deepseek` if using a DeepSeek model"

    # diff_format and str_replace_format cannot be both True
    assert not (
        args.diff_format and args.str_replace_format
    ), "Cannot use both diff_format and str_replace_format"

    # str_replace_format only supported with anthropic backend
    assert not (
        args.str_replace_format and args.backend != "anthropic"
    ), "str_replace_format only supported with anthropic backend"

    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)
    if not os.path.exists(os.path.join(args.output_folder, "patch_generation_logs")):
        os.makedirs(os.path.join(args.output_folder, "patch_generation_logs"))

    args.output_file = os.path.join(args.output_folder, "extracted_patches.jsonl")
    
    generate_patches(args)


if __name__ == "__main__":
    main()