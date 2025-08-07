import os
import json
import sys

def get_resolved_ids(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)
        return set(data.get('resolved_ids', []))

def main(directory):
    al_path = os.path.join(directory, 'agentless.al.json')
    al_ids = get_resolved_ids(al_path)

    tr_ids = set()
    for i in range(1, 11):
        tr_path = os.path.join(directory, f'agentless.tr_{i}.json')
        if os.path.exists(tr_path):
            tr_ids.update(get_resolved_ids(tr_path))

    unique_ids = tr_ids - al_ids
    print(f'Number of unique ids: {len(unique_ids)}')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'Usage: python {sys.argv[0]} <directory>')
    else:
        main(sys.argv[1])