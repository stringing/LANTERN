import json

def calculate_missing_pass10(json_file_path):
    # Load the JSON data
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    
    # Find languages with pass@10 and calculate gaps
    gaps = []
    languages_with_pass10 = []
    languages_without_pass10 = []
    
    for language, scores in data.items():
        if language == 'avg':  # Skip the average entry
            continue
            
        if 'pass@10' in scores and 'pass@9' in scores:
            gap = scores['pass@10'] - scores['pass@9']
            gaps.append(gap)
            languages_with_pass10.append(language)
        elif 'pass@9' in scores and 'pass@10' not in scores:
            languages_without_pass10.append(language)
    
    # Calculate average gap
    if gaps:
        average_gap = sum(gaps) / len(gaps)
        print(f"Languages with pass@10: {languages_with_pass10}")
        print(f"Individual gaps: {[f'{gap:.6f}' for gap in gaps]}")
        print(f"Average gap between pass@10 and pass@9: {average_gap:.6f}")
        print()
        
        # Add estimated pass@10 to languages that lack it
        print("Adding estimated pass@10 to languages that lack it:")
        for language in languages_without_pass10:
            estimated_pass10 = data[language]['pass@9'] + average_gap
            data[language]['pass@10'] = estimated_pass10
            print(f"{language}: pass@9 = {data[language]['pass@9']:.6f}, "
                  f"estimated pass@10 = {estimated_pass10:.6f}")
        
        return data
    else:
        print("No languages found with both pass@9 and pass@10")
        return data

def save_updated_data(data, output_file_path):
    with open(output_file_path, 'w') as file:
        json.dump(data, file, indent=4)
    print(f"\nUpdated data saved to: {output_file_path}")

# Usage
if __name__ == "__main__":
    input_file = "cal_results/results_2025_7_18_18_42.json"
    output_file = "cal_results/results_2025_7_18_18_42_updated.json"
    
    # Calculate and add missing pass@10 values
    updated_data = calculate_missing_pass10(input_file)
    
    # Save the updated data
    save_updated_data(updated_data, output_file)
    
    # Print the final results
    print("\nFinal results with estimated pass@10:")
    for language, scores in updated_data.items():
        if language != 'avg' and 'pass@10' in scores:
            print(f"{language}: pass@10 = {scores['pass@10']:.6f}")