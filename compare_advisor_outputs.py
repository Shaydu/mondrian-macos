#!/usr/bin/env python3
"""
Compare RAG (embedding) and baseline advisor outputs for a given image.
- Shows the image at the top
- Extracts and displays the top 3 feedback cards (by score) for each output
- Shows all recommendations for both RAG and baseline outputs
Usage:
  python3 compare_advisor_outputs.py --image source/mike-shrub.jpg --rag advisor_output_review/<rag_file>.html --baseline advisor_output_review/<baseline_file>.html [--compare]
"""
import argparse
import re
from bs4 import BeautifulSoup
import os

parser = argparse.ArgumentParser(description="Compare RAG and baseline advisor outputs.")
parser.add_argument('--image', required=True, help='Path to the analyzed image (relative or absolute)')
parser.add_argument('--rag', required=True, help='Path to the RAG/embedding HTML output')
parser.add_argument('--baseline', required=True, help='Path to the baseline HTML output')
parser.add_argument('--compare', action='store_true', help='Show comparison view with image, top 3, and recommendations')
parser.add_argument('--output', default='advisor_output_review/comparison.html', help='Output HTML file')
args = parser.parse_args()

def extract_feedback_cards(html):
    soup = BeautifulSoup(html, 'html.parser')
    cards = []
    for card in soup.select('.feedback-card'):
        # Extract score (e.g., (8/10))
        score_tag = card.select_one('.dimension-score')
        score = 0
        if score_tag:
            m = re.search(r'(\d+(?:\.\d+)?)/10', score_tag.text)
            if m:
                score = float(m.group(1))
        cards.append({'score': score, 'html': str(card)})
    return sorted(cards, key=lambda x: -x['score'])

def extract_recommendations(html):
    soup = BeautifulSoup(html, 'html.parser')
    recs = []
    for rec in soup.select('.feedback-recommendation'):
        recs.append(str(rec))
    return recs

def get_advisor_bio(html):
    """Extract advisor bio from the HTML (looks for <div class='advisor-section'> or <div class='analysis'> blocks)."""
    soup = BeautifulSoup(html, 'html.parser')
    section = soup.select_one('.advisor-section')
    if section:
        for child in section.children:
            if getattr(child, 'name', None) == 'h2':
                break
            if getattr(child, 'name', None) == 'p' and len(child.text.strip()) > 40:
                return child.text.strip()
    analysis = soup.select_one('.analysis')
    if analysis:
        for child in analysis.children:
            if getattr(child, 'name', None) == 'p' and len(child.text.strip()) > 40:
                return child.text.strip()
    return None

def build_comparison_html(image_path, rag_cards, baseline_cards, rag_recs, baseline_recs, rag_bio, baseline_bio):
    img_tag = f'<img src="{image_path}" style="max-width:100%;margin-bottom:20px;border-radius:12px;">'
    html = f"""
    <html><head><title>Advisor Output Comparison</title>
    <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif; background: #181818; color: #fff; padding: 24px; }}
    h1, h2, h3 {{ color: #fff; }}
    .compare-section {{ display: flex; gap: 32px; flex-wrap: wrap; }}
    .compare-block {{ background: #232323; border-radius: 12px; padding: 20px; flex: 1 1 400px; min-width: 350px; }}
    .feedback-card, .feedback-recommendation {{ margin-bottom: 16px; }}
    .top3-title {{ margin-top: 0; }}
    .bio-block {{ background: #1c1c1e; border-radius: 8px; padding: 16px; margin-bottom: 24px; color: #d1d1d6; }}
    </style></head><body>
    <h1>Advisor Output Comparison</h1>
    {img_tag}
    <div class="compare-section">
      <div class="compare-block">
        <h2>RAG/Embedding Output</h2>
        {f'<div class="bio-block"><strong>Advisor Bio:</strong> {rag_bio}</div>' if rag_bio else ''}
        <h3 class="top3-title">Top 3 Feedback</h3>
        {''.join(card['html'] for card in rag_cards[:3])}
        <h3>All Recommendations</h3>
        {''.join(rag_recs)}
      </div>
      <div class="compare-block">
        <h2>Baseline Output</h2>
        {f'<div class="bio-block"><strong>Advisor Bio:</strong> {baseline_bio}</div>' if baseline_bio else ''}
        <h3 class="top3-title">Top 3 Feedback</h3>
        {''.join(card['html'] for card in baseline_cards[:3])}
        <h3>All Recommendations</h3>
        {''.join(baseline_recs)}
      </div>
    </div>
    <div style='margin-top:32px;color:#aaa;font-size:14px;'>
      <b>Tip:</b> Use <code>--compare</code> to see both RAG and baseline outputs side-by-side. Without it, only RAG output is shown.
    </div>
    </body></html>
    """
    return html

with open(args.rag, encoding='utf-8') as f:
    rag_html = f.read()
with open(args.baseline, encoding='utf-8') as f:
    baseline_html = f.read()

rag_cards = extract_feedback_cards(rag_html)
baseline_cards = extract_feedback_cards(baseline_html)
rag_recs = extract_recommendations(rag_html)
baseline_recs = extract_recommendations(baseline_html)

if args.compare:
    rag_bio = get_advisor_bio(rag_html)
    baseline_bio = get_advisor_bio(baseline_html)
    html = build_comparison_html(args.image, rag_cards, baseline_cards, rag_recs, baseline_recs, rag_bio, baseline_bio)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[OK] Comparison HTML written to {args.output}")
else:
    # Only show image, top 3, and all RAG feedback, plus advisor bio
    rag_bio = get_advisor_bio(rag_html)
    img_path = args.image
    if not os.path.isabs(img_path):
        img_path = os.path.abspath(img_path)
    img_tag = f'<img src="file://{img_path}" style="max-width:100%;margin-bottom:20px;border-radius:12px;">'
    html = f"""
    <html><head><title>Advisor Output (RAG Only)</title>
    <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif; background: #181818; color: #fff; padding: 24px; }}
    h1, h2, h3 {{ color: #fff; }}
    .feedback-card, .feedback-recommendation {{ margin-bottom: 16px; }}
    .top3-title {{ margin-top: 0; }}
    .main-block {{ background: #232323; border-radius: 12px; padding: 20px; max-width: 700px; margin: 0 auto; }}
    .bio-block {{ background: #1c1c1e; border-radius: 8px; padding: 16px; margin-bottom: 24px; color: #d1d1d6; }}
    </style></head><body>
    <h1>Advisor Output (RAG Only)</h1>
    {img_tag}
    <div class="main-block">
      {f'<div class="bio-block"><strong>Advisor Bio:</strong> {rag_bio}</div>' if rag_bio else ''}
      <h2>Top 3 Feedback</h2>
      {''.join(card['html'] for card in rag_cards[:3])}
      <h2>All Recommendations</h2>
      {''.join(rag_recs)}
    </div>
    <div style='margin-top:32px;color:#aaa;font-size:14px;'>
      <b>Tip:</b> Use <code>--compare</code> to see both RAG and baseline outputs side-by-side. Without it, only RAG output is shown.
    </div>
    </body></html>
    """
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"[OK] RAG-only HTML written to {args.output}")
