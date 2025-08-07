import argparse
import json
import os
import random
from tqdm import tqdm
from agentless.util.utils import load_jsonl
from agentless.multilang.const import (
    LANGUAGE
)

# Available target languages
TARGET_LANGUAGES = ["python", "c", "c++", "java", "javascript", "php", "go", "rust", "c#", "ruby", "kotlin"]
TARGET_LANGUAGES.remove(LANGUAGE)  # Remove the current language from the selection

def load_previous_selections(output_file_pattern, current_it):
    """Load language selections from previous iterations."""
    used_languages = {}  # instance_id -> set of used languages
    
    for it in range(1, current_it):
        # Replace iter_{current_it} with iter_{it} in the output file path
        prev_file = output_file_pattern.replace(f"iter_{current_it}", f"iter_{it}")
        
        if os.path.exists(prev_file):
            try:
                with open(prev_file, "r") as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line.strip())
                            instance_id = data["instance_id"]
                            target_language = data["target_language"]
                            
                            if instance_id not in used_languages:
                                used_languages[instance_id] = set()
                            used_languages[instance_id].add(target_language)
            except (FileNotFoundError, json.JSONDecodeError):
                # Skip if file doesn't exist or has invalid JSON
                continue
    
    return used_languages

def select_target_languages(args):
    """Select target programming languages for each instance."""
    # Load prepared contexts
    contexts = load_jsonl(args.context_file)
    
    # Set random seed for reproducibility if provided
    if args.seed is not None:
        random.seed(args.seed)
    
    # Load previous language selections if it > 1
    used_languages = {}
    if args.it > 1:
        used_languages = load_previous_selections(args.output_file, args.it)
        print(f"Loaded previous selections from {args.it - 1} iterations")
    
    language_selections = []
    
    for context_data in tqdm(contexts, total=len(contexts), colour="GREEN"):
        instance_id = context_data["instance_id"]
        
        # Skip instances with empty context
        if context_data["topn_content"].strip() == "":
            continue
        
        # Get available languages for this instance
        available_languages = TARGET_LANGUAGES.copy()
        if instance_id in used_languages:
            # Remove already used languages for this instance
            available_languages = [lang for lang in available_languages 
                                 if lang not in used_languages[instance_id]]
        
        # If no languages available, skip this instance
        if not available_languages:
            print(f"Warning: No available languages for instance {instance_id}, skipping")
            continue
            
        # Randomly select a target language from available ones
        target_language = random.choice(available_languages)
        
        language_selections.append({
            "instance_id": instance_id,
            "target_language": target_language
        })
    
    if not os.path.exists(os.path.dirname(args.output_file)):
        os.makedirs(os.path.dirname(args.output_file))
    
    # Save language selections
    with open(args.output_file, "w") as f:
        for selection in language_selections:
            f.write(json.dumps(selection) + "\n")
    
    print(f"Selected target languages for {len(language_selections)} instances and saved to {args.output_file}")
    
    # Print language distribution for reference
    language_counts = {}
    for selection in language_selections:
        lang = selection["target_language"]
        language_counts[lang] = language_counts.get(lang, 0) + 1
    
    print("\nLanguage distribution:")
    for lang, count in sorted(language_counts.items()):
        print(f"  {lang}: {count}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context_file", type=str, required=True, help="Path to prepared contexts file")
    parser.add_argument("--output_file", type=str, required=True, help="Path to output language selections file")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--it", type=int, required=True, help="Current iteration number")
    
    args = parser.parse_args()
    
    select_target_languages(args)


if __name__ == "__main__":
    main()