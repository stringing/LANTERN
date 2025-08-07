import argparse
import json
import os
from datasets import load_dataset
from tqdm import tqdm

from agentless.multilang.utils import load_local_json
from agentless.util.preprocess_data import (
    get_full_file_paths_and_classes_and_functions,
    get_repo_structure,
    line_wrap_content,
    transfer_arb_locs_to_locs,
)
from agentless.util.utils import load_jsonl, setup_logger


def construct_topn_file_context(
    file_to_locs,
    pred_files,
    file_contents,
    structure,
    context_window: int,
    loc_interval: bool = True,
    fine_grain_loc_only: bool = False,
    add_space: bool = False,
    sticky_scroll: bool = False,
    no_line_number: bool = True,
):
    """Concatenate provided locations to form a context.

    loc: {"file_name_1": ["loc_str_1"], ...}
    """
    file_loc_intervals = dict()
    topn_content = ""

    for pred_file, locs in file_to_locs.items():
        content = file_contents[pred_file]
        line_locs, context_intervals = transfer_arb_locs_to_locs(
            locs,
            structure,
            pred_file,
            context_window,
            loc_interval,
            fine_grain_loc_only,
            file_content=file_contents[pred_file] if pred_file in file_contents else "",
        )

        if len(line_locs) > 0:
            # Note that if no location is predicted, we exclude this file.
            file_loc_content = line_wrap_content(
                content,
                context_intervals,
                add_space=add_space,
                no_line_number=no_line_number,
                sticky_scroll=sticky_scroll,
            )
            topn_content += f"### {pred_file}\n{file_loc_content}\n\n\n"
            file_loc_intervals[pred_file] = context_intervals

    return topn_content, file_loc_intervals


def prepare_context_for_instance(loc, args, swe_bench_data):
    """Prepare context for a single instance."""
    instance_id = loc["instance_id"]

    if args.target_id is not None:
        if args.target_id != instance_id:
            return None

    log_file = os.path.join(args.output_folder, "context_logs", f"{instance_id}.log")
    logger = setup_logger(log_file)

    logger.info(f"================ preparing context for {instance_id} ================")
    
    if len(loc["found_files"]) == 0:
        logger.info(f"No files found for {instance_id}")
        return {
            "instance_id": instance_id,
            "topn_content": "",
            "file_loc_intervals": {},
            "file_contents": {},
            "pred_files": [],
            "problem_statement": "",
            "repo": "",
            "base_commit": ""
        }

    pred_files = loc["found_files"][: args.top_n]
    bench_data = [x for x in swe_bench_data if x["instance_id"] == instance_id][0]
    problem_statement = bench_data["problem_statement"]
    repo = bench_data["repo"]
    base_commit = bench_data["base_commit"]
    
    structure = get_repo_structure(
        instance_id, repo, base_commit, "playground"
    )
    files, _, _ = get_full_file_paths_and_classes_and_functions(structure)

    # Construct file contents
    file_contents = dict()
    for i, pred_file in enumerate(pred_files):
        content = None
        for file_content in files:
            if file_content[0] == pred_file:
                content = "\n".join(file_content[1])
                file_contents[pred_file] = content
                break

        assert content is not None, f"{pred_file} file not found"

    # Construct top-n file context
    file_to_edit_locs = dict()
    if "found_edit_locs" in loc:
        file_to_edit_locs = loc["found_edit_locs"]

    topn_content, file_loc_intervals = construct_topn_file_context(
        file_to_edit_locs,
        pred_files,
        file_contents,
        structure,
        context_window=args.context_window,
        loc_interval=args.loc_interval,
        fine_grain_loc_only=args.fine_grain_loc_only,
        add_space=args.add_space,
        no_line_number=args.diff_format or args.str_replace_format,
        sticky_scroll=args.sticky_scroll,
    )

    logger.info(f"Context prepared for {instance_id}")
    
    return {
        "instance_id": instance_id,
        "topn_content": topn_content,
        "file_loc_intervals": file_loc_intervals,
        "file_contents": file_contents,
        "pred_files": pred_files,
        "problem_statement": problem_statement,
        "repo": repo,
        "base_commit": base_commit,
        "found_edit_locs": loc.get("found_edit_locs", {}),
        "found_files": loc["found_files"]
    }


def prepare_contexts(args):
    """Main function to prepare contexts for all instances."""
    with open(f"{args.output_folder}/args.json", "w") as f:
        json.dump(vars(args), f, indent=4)

    if args.dataset == 'local_json':
        swe_bench_data = load_local_json()
    else:
        swe_bench_data = load_dataset(args.dataset, split=args.split)
    
    locs = load_jsonl(args.loc_file)
    
    # Save used locations
    with open(f"{args.output_folder}/used_locs.jsonl", "w") as f:
        for loc in locs:
            f.write(json.dumps(loc) + "\n")

    contexts = []
    for loc in tqdm(locs, total=len(locs), colour="MAGENTA"):
        context_data = prepare_context_for_instance(loc, args, swe_bench_data)
        if context_data is not None:
            contexts.append(context_data)

    # Save all contexts
    with open(args.context_file, "w") as f:
        for context in contexts:
            f.write(json.dumps(context) + "\n")

    print(f"Prepared contexts for {len(contexts)} instances and saved to {args.context_file}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--loc_file", type=str, required=True)
    parser.add_argument("--top_n", type=int, default=1)
    parser.add_argument("--loc_interval", action="store_true")
    parser.add_argument("--context_window", type=int, default=10)
    parser.add_argument("--output_folder", type=str, required=True)
    parser.add_argument("--add_space", action="store_true")
    parser.add_argument("--fine_grain_loc_only", action="store_true")
    parser.add_argument("--diff_format", action="store_true")
    parser.add_argument("--str_replace_format", action="store_true")
    parser.add_argument("--sticky_scroll", action="store_true")
    parser.add_argument("--target_id", type=str)
    parser.add_argument(
        "--dataset",
        type=str,
        default="princeton-nlp/SWE-bench_Lite",
        choices=["princeton-nlp/SWE-bench_Lite", "princeton-nlp/SWE-bench_Verified", "Daoguang/Multi-SWE-bench", "local_json"],
    )
    parser.add_argument(
        "--split",
        type=str,
        default="test",
    )

    args = parser.parse_args()

    # diff_format and str_replace_format cannot be both True
    assert not (
        args.diff_format and args.str_replace_format
    ), "Cannot use both diff_format and str_replace_format"

    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)
    if not os.path.exists(os.path.join(args.output_folder, "context_logs")):
        os.makedirs(os.path.join(args.output_folder, "context_logs"))

    args.context_file = os.path.join(args.output_folder, "contexts.jsonl")
    
    prepare_contexts(args)


if __name__ == "__main__":
    main()