import json
import os
from collections import defaultdict
import sys

def count_solved_bugs_in_dir(directory):
    """Count solved bugs in a single directory"""
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
    
    return solved_bugs

def count_solved_bugs_all_dirs(directory):
    """Count solved bugs across all specified directories"""

    base_path = directory
    # base_path = "Results/1.2sl"
    
    # Create list of directories to check
    directories = [base_path]  # Start with the base directory
    
    # Add iter_1 through iter_10 directories
    for i in range(1, 11):
        iter_dir = os.path.join(base_path, f"iter_{i}", "back_trans")
        directories.append(iter_dir)
    
    # Collect all solved bugs from all directories
    all_solved_bugs = set()
    project_bug_counts = defaultdict(int)
    
    for directory in directories:
        if os.path.exists(directory):
            print(f"Processing directory: {directory}")
            solved_bugs = count_solved_bugs_in_dir(directory)
            print(f"  Found {len(solved_bugs)} solved bugs: {solved_bugs}")
            
            # Add to overall set
            all_solved_bugs.update(solved_bugs)
            
            # Count bugs per project
            for bug in solved_bugs:
                # Extract project name (part before the first "-")
                if "-" in bug:
                    project_name = bug.split("-")[0]
                    project_bug_counts[project_name] += 1
        else:
            print(f"Directory does not exist: {directory}")
    
    # Convert set to sorted list for JSON export
    solved_bugs_list = sorted(list(all_solved_bugs))
    
    # Export all solved bugs to JSON file
    # output_file = "Results/CR_combine/cr_1.2sl_all_solved_bugs.json"
    output_file = os.path.join(os.path.dirname(directory), "CR_combine/cr_1.2sl_all_solved_bugs.json")
    # output_file = "Results/CR_combine/test.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    try:
        with open(output_file, 'w') as f:
            json.dump(solved_bugs_list, f, indent=2)
        print(f"\nExported all solved bugs to: {output_file}")
    except Exception as e:
        print(f"Error exporting to JSON: {e}")
    
    # Print results
    print("\n" + "="*50)
    print("SUMMARY:")
    print("="*50)
    print(f"Total unique solved bugs: {len(all_solved_bugs)}")
    print(f"All solved bugs: {solved_bugs_list}")
    
    print(f"\nSolved bugs by project:")
    for project, count in sorted(project_bug_counts.items()):
        print(f"  {project}: {count} bugs")
    
    return len(all_solved_bugs), dict(project_bug_counts)


if len(sys.argv) > 1:
    directory = sys.argv[1]
    total_count, project_counts = count_solved_bugs_all_dirs(directory)
