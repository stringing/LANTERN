import json
import os
import sys

def count_solved_bugs_in_dir(directory):
    lm_repair_path = os.path.join(directory, 'lm_repair.json')
    solved_bugs = set()
    if os.path.exists(lm_repair_path):
        with open(lm_repair_path, 'r') as f:
            bugs = json.load(f)
        for bug_id, patches in bugs.items():
            if any(patch.get('valid', False) for patch in patches):
                solved_bugs.add(bug_id)
    else:
        # Count solved bugs by reading all single json files in the directory
        for filename in os.listdir(directory):
            if filename.endswith('.json') and filename != 'lm_repair.json' and 'attempt' in filename:
                file_path = os.path.join(directory, filename)
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    if data['valid']:
                        solved_bugs.add(data['bug'])
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    print(solved_bugs)
    return len(solved_bugs)

def count_solved_bugs_all_dirs(directory):
    base_path = directory
    num_solved_bugs = 0
    num_solved_bugs += count_solved_bugs_in_dir(base_path)
    for i in range(1, 11):
        iter_dir = os.path.join(base_path, f"iter_{i}", "back_trans")
        num_solved_bugs += count_solved_bugs_in_dir(iter_dir)
    return num_solved_bugs


# Example usage:
# directory = "/root/ChatRepair_LANTERN/code/Generation/Results/1.2f/iter_1/back_trans"
if len(sys.argv) > 1:
    directory = sys.argv[1]
    print("Number of solved bugs:", count_solved_bugs_all_dirs(directory))
else:
    print("Usage: python count_num.py <directory>")

