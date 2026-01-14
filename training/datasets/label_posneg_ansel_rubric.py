# This script creates a new JSONL file with both positive (good) and negative (bad/counterexample) examples for LoRA training.
# It scans the rubric-filtered dataset for negative/critical keywords and labels each entry as 'positive' or 'negative'.
# Output: ansel_combined_train_rubric_posneg.jsonl

import json
import re


# Rubric evaluation keywords (focus on critique of exposure, contrast, sharpness, etc.)
RUBRIC_KEYWORDS = [
    'exposure', 'contrast', 'sharpness', 'tonal range', 'composition', 'emotional impact',
    'conservation', 'technical excellence', 'visual storytelling', 'light and shadow',
    'perspective', 'depth', 'grade', 'recommendation', 'comment', 'score', 'mark', 'rating',
    'clarity', 'focus', 'detail', 'balance', 'dynamic range', 'highlights', 'shadows', 'midtones',
    'color balance', 'texture', 'visual impact', 'storytelling', 'message', 'aesthetic', 'artistic',
    'visual', 'composition', 'framing', 'subject placement', 'leading lines', 'rule of thirds',
    'symmetry', 'asymmetry', 'pattern', 'rhythm', 'visual weight', 'negative space', 'cropping',
    'background', 'foreground', 'depth of field', 'lighting', 'mood', 'atmosphere', 'emotion',
    'intent', 'purpose', 'interpretation', 'vision', 'style', 'originality', 'creativity', 'innovation'
]
RUBRIC_REGEX = re.compile(r'(' + '|'.join([re.escape(k) for k in RUBRIC_KEYWORDS]) + r')', re.IGNORECASE)

# Negative/critical keywords (for negative examples)
NEGATIVE_KEYWORDS = [
    'incorrect', 'poor', 'mistake', 'problem', 'bad', 'avoid', 'wrong', 'fail', 'flaw', 'error',
    'weak', 'lacking', 'insufficient', 'overexposed', 'underexposed', 'distracting', 'unbalanced',
    'cluttered', 'flat', 'muddy', 'harsh', 'blown out', 'soft focus', 'out of focus', 'noisy', 'grainy',
    'uninspired', 'boring', 'cliché', 'cliche', 'uninteresting', 'overdone', 'overprocessed', 'underwhelming',
    'unconvincing', 'fails', 'failure', 'missed', 'misses', 'unresolved', 'unrefined', 'unpolished', 'unskilled',
    'amateurish', 'unprofessional', 'dull', 'lifeless', 'awkward', 'unintentional', 'unintended', 'overly', 'under',
    'detracts', 'detract', 'detracted', 'detracting', 'detracts from', 'lacks', 'lack', 'lacked', 'lacking in',
    'not enough', 'too much', 'overly bright', 'overly dark', 'overly saturated', 'underexposed', 'overexposed'
]
NEGATIVE_REGEX = re.compile(r'(' + '|'.join([re.escape(k) for k in NEGATIVE_KEYWORDS]) + r')', re.IGNORECASE)

input_path = 'ansel_combined_train_rubric_filtered.jsonl'
output_path = 'ansel_combined_train_rubric_posneg.jsonl'


# Only include entries that evaluate rubric dimensions (not purely technical/camera)
with open(input_path, 'r') as infile, open(output_path, 'w') as outfile:
    for line in infile:
        try:
            obj = json.loads(line)
            label = 'positive'
            assistant_content = ''
            if isinstance(obj, dict) and 'messages' in obj:
                for msg in obj['messages']:
                    if msg.get('role') == 'assistant':
                        assistant_content = msg.get('content', '')
                        break
            # Only keep if rubric evaluation is present
            if not RUBRIC_REGEX.search(assistant_content):
                continue
            if NEGATIVE_REGEX.search(assistant_content):
                label = 'negative'
            obj['label'] = label
            outfile.write(json.dumps(obj) + '\n')
        except Exception as e:
            continue  # skip malformed lines

print(f"Labeled dataset saved to {output_path}")
