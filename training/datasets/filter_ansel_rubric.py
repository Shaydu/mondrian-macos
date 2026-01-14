# This script filters a JSONL dataset to only include entries relevant to Ansel Adams' rubric dimensions for LoRA training.
# It outputs a new JSONL file with only actionable, rubric-based training data.

import json
import re

# Define the rubric dimensions/keywords
RUBRIC_KEYWORDS = [
    'tonal range', 'composition', 'emotional impact', 'conservation',
    'technical excellence', 'visual storytelling', 'light and shadow', 'perspective', 'depth'
]

# Compile regex for fast matching (case-insensitive, word boundaries)
RUBRIC_REGEX = re.compile(r'(' + '|'.join([re.escape(k) for k in RUBRIC_KEYWORDS]) + r')', re.IGNORECASE)

input_path = 'ansel_combined_train.jsonl'
output_path = 'ansel_combined_train_rubric_filtered.jsonl'

with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
    for line in infile:
        try:
            obj = json.loads(line)
            # Check if any rubric keyword appears in the assistant's content
            assistant_content = ''
            if isinstance(obj, dict) and 'messages' in obj:
                for msg in obj['messages']:
                    if msg.get('role') == 'assistant':
                        assistant_content = msg.get('content', '')
                        break
            if RUBRIC_REGEX.search(assistant_content):
                outfile.write(line)
        except Exception as e:
            continue  # skip malformed lines

print(f"Filtered dataset saved to {output_path}")
