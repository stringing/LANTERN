import os
from pathlib import Path
import sys

def rename_files_without_suffix(directory_path):
    """
    Rename files without suffixes by adding '_10' and '.json' extension.
    
    Args:
        directory_path (str): Path to the directory containing files to rename
    """
    try:
        # Convert to Path object for easier handling
        directory = Path(directory_path)
        
        # Check if directory exists
        if not directory.exists():
            print(f"Error: Directory '{directory_path}' does not exist.")
            return
        
        if not directory.is_dir():
            print(f"Error: '{directory_path}' is not a directory.")
            return
        
        # Counter for renamed files
        renamed_count = 0
        
        # Iterate through all items in the directory
        for item in directory.iterdir():
            # Check if it's a file (not a directory) and has no suffix
            if item.is_file() and not item.suffix:
                # Create new filename: original_name + '_10' + '.json'
                new_name = item.stem + "_10.json"
                new_path = item.parent / new_name
                
                # Check if the new filename already exists
                if new_path.exists():
                    print(f"Warning: '{new_name}' already exists. Skipping '{item.name}'.")
                    continue
                
                try:
                    # Rename the file
                    item.rename(new_path)
                    print(f"Renamed: '{item.name}' -> '{new_name}'")
                    renamed_count += 1
                except OSError as e:
                    print(f"Error renaming '{item.name}': {e}")
        
        print(f"\nTotal files renamed: {renamed_count}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    # Get directory path from command line argument or user input
    if len(sys.argv) > 1:
        directory_path = sys.argv[1]
    else:
        directory_path = input("Enter the directory path: ").strip()
    
    # Remove quotes if present
    directory_path = directory_path.strip('"\'')
    
    rename_files_without_suffix(directory_path)

if __name__ == "__main__":
    main()