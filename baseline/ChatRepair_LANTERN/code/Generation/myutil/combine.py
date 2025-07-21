import json
import os
from collections import defaultdict
import sys

def combine_and_count_bugs(directory_path):
    """
    Read all JSON files in a directory, combine the bug lists, 
    and count unique solved bugs by project name.
    """
    
    if not os.path.exists(directory_path):
        print(f"Directory does not exist: {directory_path}")
        return
    
    # Set to store all unique bugs
    all_bugs = set()
    
    # Dictionary to track which files were processed
    processed_files = []
    
    # Read all JSON files in the directory
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            file_path = os.path.join(directory_path, filename)
            try:
                with open(file_path, 'r') as f:
                    bugs_list = json.load(f)
                
                # Ensure the loaded data is a list
                if isinstance(bugs_list, list):
                    print(f"Processing {filename}: {len(bugs_list)} bugs")
                    all_bugs.update(bugs_list)
                    processed_files.append(filename)
                else:
                    print(f"Warning: {filename} does not contain a list, skipping...")
                    
            except Exception as e:
                print(f"Error reading {filename}: {e}")
    
    if not processed_files:
        print("No valid JSON files found in the directory.")
        return
    
    # Count bugs by project
    project_bug_counts = defaultdict(set)  # Use set to ensure uniqueness per project
    
    for bug in all_bugs:
        # Extract project name (part before the first "-")
        if "-" in bug:
            project_name = bug.split("-")[0]
            project_bug_counts[project_name].add(bug)
        else:
            print(f"Warning: Bug name '{bug}' does not contain '-', skipping...")
    
    # Convert sets to counts
    project_counts = {project: len(bugs) for project, bugs in project_bug_counts.items()}
    
    # Export combined results
    combined_bugs_list = sorted(list(all_bugs))
    output_file = os.path.join(directory_path, "combined_solved_bugs.json")
    
    try:
        with open(output_file, 'w') as f:
            json.dump(combined_bugs_list, f, indent=2)
        print(f"\nExported combined bugs to: {output_file}")
    except Exception as e:
        print(f"Error exporting combined results: {e}")
    
    # Export project summary
    summary_output = {
        "total_unique_bugs": len(all_bugs),
        "bugs_by_project": project_counts,
        "processed_files": processed_files,
        "all_bugs": combined_bugs_list
    }
    
    summary_file = os.path.join(directory_path, "bug_summary.json")
    try:
        with open(summary_file, 'w') as f:
            json.dump(summary_output, f, indent=2)
        print(f"Exported summary to: {summary_file}")
    except Exception as e:
        print(f"Error exporting summary: {e}")
    
    # Print results
    print("\n" + "="*60)
    print("COMBINED RESULTS:")
    print("="*60)
    print(f"Processed files: {', '.join(processed_files)}")
    print(f"Total unique solved bugs: {len(all_bugs)}")
    
    print(f"\nSolved bugs by project:")
    total_project_bugs = 0
    for project, count in sorted(project_counts.items()):
        print(f"  {project}: {count} bugs")
        total_project_bugs += count
    
    print(f"\nVerification: Total bugs across all projects = {total_project_bugs}")
    
    # Show some example bugs for each project
    print(f"\nExample bugs by project:")
    for project, bugs in sorted(project_bug_counts.items()):
        example_bugs = sorted(list(bugs))[:3]  # Show first 3 bugs
        more_text = f" (and {len(bugs)-3} more)" if len(bugs) > 3 else ""
        print(f"  {project}: {', '.join(example_bugs)}{more_text}")
    
    return len(all_bugs), project_counts

def main():
    # Specify the directory containing JSON files
    directory = input("Enter the directory path containing JSON files: ").strip()
    
    # If no input provided, use current directory
    if not directory:
        directory = "."
        print("Using current directory...")
    
    print(f"Processing JSON files in: {os.path.abspath(directory)}")
    
    total_bugs, project_counts = combine_and_count_bugs(directory)
    
    return total_bugs, project_counts

if __name__ == "__main__":
    if len(sys.argv) > 1:
        directory = sys.argv[1]
        combine_and_count_bugs(directory)
    # else:
    #     main()