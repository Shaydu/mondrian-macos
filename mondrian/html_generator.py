#!/usr/bin/env python3
"""
HTML Generation Module for AI Advisor Service
Generates iOS-compatible HTML for analysis output, summaries, and advisor bios.
"""

import os
import re
import base64
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def get_rating_style(score: int) -> tuple:
    """Return color and rating text based on score"""
    if score >= 8:
        return "#388e3c", "Excellent"  # Green
    elif score >= 6:
        return "#f57c00", "Good"       # Orange
    else:
        return "#d32f2f", "Needs Work" # Red


def format_dimension_name(name: str) -> str:
    """Format dimension names to have proper spacing (e.g., ColorHarmony -> Color Harmony)"""
    # Insert space before uppercase letters that follow lowercase letters
    formatted = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    return formatted


def normalize_dimension_key(name: str) -> str:
    """Normalize dimension name for lookup"""
    dim_key = name.lower().strip().replace(' & ', '_').replace(' and ', '_').replace(' ', '_')
    
    if 'focus' in dim_key:
        return 'focus_sharpness'
    elif 'color' in dim_key:
        return 'color_harmony'
    elif 'depth' in dim_key:
        return 'depth_perspective'
    elif 'balance' in dim_key:
        return 'visual_balance'
    elif 'emotion' in dim_key or 'impact' in dim_key:
        return 'emotional_impact'
    elif 'isolation' in dim_key:
        return 'subject_isolation'
    
    return dim_key


def generate_ios_detailed_html(
    analysis_data: Dict[str, Any], 
    advisor: str, 
    mode: str, 
    case_studies: List[Dict[str, Any]] = None
) -> str:
    """Generate iOS-compatible dark theme HTML for detailed analysis
    
    Args:
        analysis_data: Parsed analysis from LLM
        advisor: Advisor name
        mode: Analysis mode
        case_studies: Pre-computed case studies from _compute_case_studies()
            Each entry has: dimension_name, user_score, ref_image, ref_score, gap, relevance
    """
    
    if case_studies is None:
        case_studies = []
    
    # Build lookup for case studies by normalized dimension name
    case_study_lookup = {}
    for cs in case_studies:
        dim_name = cs.get('dimension_name', '').lower().replace(' ', '_')
        case_study_lookup[dim_name] = cs
    
    logger.info(f"[HTML Gen] Generating HTML with {len(case_studies)} pre-computed case studies for dimensions: {list(case_study_lookup.keys())}")
    
    # Extract data from the expected JSON structure
    image_description = analysis_data.get('image_description', 'Image analysis')
    dimensions = analysis_data.get('dimensions', [])
    overall_score = analysis_data.get('overall_score', 'N/A')
    technical_notes = analysis_data.get('technical_notes', '')
    
    # Format dimension names
    for dim in dimensions:
        if 'name' in dim and dim['name']:
            dim['name'] = format_dimension_name(dim['name'])
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', sans-serif;
            padding: 20px;
            background: #000000;
            line-height: 1.6;
            color: #ffffff;
            max-width: 100%;
        }}
        @media (max-width: 768px) {{ body {{ padding: 15px; }} .analysis {{ padding: 15px; }} }}
        @media (max-width: 375px) {{ body {{ padding: 10px; font-size: 14px; }} .analysis {{ padding: 12px; }} }}
        @media (min-width: 1024px) {{ body {{ max-width: 800px; margin: 0 auto; padding: 30px; }} }}
        .analysis {{
            background: #1c1c1e;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            text-align: left;
        }}
        .analysis h2 {{
            color: #ffffff;
            font-size: 22px;
            font-weight: 600;
            margin: 0 0 12px 0;
            text-align: left;
        }}
        .analysis p {{
            color: #d1d1d6;
            font-size: 16px;
            margin: 0 0 16px 0;
            line-height: 1.6;
            text-align: left;
        }}
        .feedback-card {{
            background: #fff;
            margin: 20px 0;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 8px;
        }}
        .feedback-card h3 {{
            margin-top: 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: #333;
        }}
        .feedback-comment {{
            margin: 15px 0;
            padding: 12px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .feedback-comment p {{ margin: 0; line-height: 1.6; color: #333; }}
        .feedback-recommendation {{
            margin-top: 15px;
            padding: 12px;
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            border-radius: 4px;
        }}
        .feedback-recommendation strong {{
            display: block;
            margin-bottom: 8px;
            color: #1976d2;
        }}
        .feedback-recommendation p {{ margin: 0; line-height: 1.6; color: #333; }}
        .reference-citation {{
            margin-top: 16px;
            padding: 0;
            background: transparent;
            border: none;
            border-radius: 0;
            font-size: 14px;
        }}
        .reference-citation .case-study-box {{
            background: #2c2c2e;
            border-radius: 8px;
            padding: 16px;
            border-left: 4px solid #30b0c0;
            overflow: hidden;
        }}
        .reference-citation .case-study-image {{
            width: 100%;
            height: auto;
            max-width: 100%;
            border-radius: 6px;
            margin-bottom: 12px;
            display: block;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }}
        .reference-citation .case-study-title {{
            color: #ffffff;
            font-size: 16px;
            margin: 0 0 12px 0;
            font-weight: 600;
        }}
        .reference-citation .case-study-metadata {{
            color: #d1d1d6;
            font-size: 13px;
            line-height: 1.5;
            margin: 8px 0 0 0;
        }}
        .reference-citation strong {{ color: #30b0c0; }}
        .advisor-quote-box {{
            background: #2c2c2e;
            border-radius: 8px;
            padding: 16px;
            border-left: 4px solid #ff9500;
            overflow: hidden;
            margin-top: 12px;
        }}
        .advisor-quote-box .advisor-quote-title {{
            color: #ffffff;
            font-size: 14px;
            margin: 0 0 12px 0;
            font-weight: 600;
        }}
        .advisor-quote-box .advisor-quote-text {{
            color: #d1d1d6;
            font-size: 14px;
            line-height: 1.6;
            font-style: italic;
            margin: 0;
        }}
        .advisor-quote-box .advisor-quote-source {{
            color: #a1a1a6;
            font-size: 12px;
            margin-top: 8px;
            font-style: normal;
        }}
    </style>
</head>
<body>
<div class="advisor-section" data-advisor="{advisor}">
  <div class="analysis">
  <h2>Description</h2>
  <p>{image_description}</p>

  <h2>Improvement Guide</h2>
  <p style="color: #666; margin-bottom: 20px;">Each dimension is analyzed with specific feedback and actionable recommendations for improvement.</p>
'''
    
    # Add dimension cards
    for dim in dimensions:
        name = dim.get('name', 'Unknown')
        score = dim.get('score', 0)
        comment = dim.get('comment', 'No analysis available.')
        recommendation = dim.get('recommendation', 'No recommendation available.')
        color, rating = get_rating_style(score)
        
        # Check if this dimension has a pre-computed case study
        reference_citation = ""
        dim_key = normalize_dimension_key(name)
        
        case_study = case_study_lookup.get(dim_key)
        if case_study:
            best_ref = case_study.get('ref_image', {})
            best_gap = case_study.get('gap', 0)
            ref_score_val = case_study.get('ref_score', 0)
            
            ref_title = best_ref.get('image_title', 'Reference Image')
            ref_year = best_ref.get('date_taken', '')
            ref_path = best_ref.get('image_path', '')
            
            # Format title with year if available
            if ref_year and str(ref_year).strip():
                title_with_year = f"{ref_title} ({ref_year})"
            else:
                title_with_year = ref_title
            
            # Get image data and convert to base64 for embedding
            ref_image_url = ''
            if ref_path and os.path.exists(ref_path):
                try:
                    with open(ref_path, 'rb') as img_file:
                        image_data = img_file.read()
                        b64_image = base64.b64encode(image_data).decode('utf-8')
                        img_ext = os.path.splitext(ref_path)[1].lower()
                        mime_type = 'image/png' if img_ext == '.png' else 'image/jpeg' if img_ext in ['.jpg', '.jpeg'] else 'image/png'
                        ref_image_url = f"data:{mime_type};base64,{b64_image}"
                except Exception as e:
                    logger.warning(f"Failed to embed image as base64: {e}")
            
            # Build case study box with image
            reference_citation = '<div class="reference-citation"><div class="case-study-box">'
            reference_citation += f'<div class="case-study-title">Case Study: {title_with_year}</div>'
            
            # Add image if available
            if ref_image_url:
                reference_citation += f'<img src="{ref_image_url}" alt="{title_with_year}" class="case-study-image" />'
            
            # Add metadata
            metadata_parts = []
            if best_ref.get('image_description'):
                metadata_parts.append(f'<strong>Description:</strong> {best_ref["image_description"]}')
            if best_ref.get('location'):
                metadata_parts.append(f'<strong>Location:</strong> {best_ref["location"]}')
            metadata_parts.append(f'<strong>Score:</strong> {ref_score_val}/10 in {name}')
            metadata_parts.append(f'<strong>Your Gap:</strong> {best_gap:.1f} points to master this technique')
            
            reference_citation += f'<div class="case-study-metadata">' + '<br/>'.join(metadata_parts) + '</div>'
            reference_citation += '</div></div>'
            
            logger.info(f"[HTML Gen] Added case study for {name}: '{ref_title}' (gap={best_gap:.1f})")
        
        html += f'''
  <div class="feedback-card">
    <h3>
      <span>{name}</span>
      <span style="color: {color}; font-size: 1.1em;">{score}/10 <span style="font-size: 0.7em; font-weight: normal;">({rating})</span></span>
    </h3>
    <div class="feedback-comment" style="border-left: 4px solid {color};">
      <p>{comment}</p>
    </div>
    <div class="feedback-recommendation">
      <strong>How to Improve:</strong>
      <p>{recommendation}</p>
    </div>{reference_citation}
  </div>
'''
    
    html += f'''
  <h2>Overall Grade</h2>
  <p><strong>{overall_score}/10</strong></p>
  <p><strong>Grade Note:</strong> {technical_notes}</p>
'''
    
    html += '''
</div>
</div>
</body>
</html>'''
    
    return html


def generate_summary_html(analysis_data: Dict[str, Any], disclaimer_text: str = None) -> str:
    """Generate iOS-compatible summary HTML with Top 3 recommendations (lowest scoring dimensions)
    
    Args:
        analysis_data: Parsed analysis data with dimensions
        disclaimer_text: Optional disclaimer text to display
    """
    
    dimensions = analysis_data.get('dimensions', [])
    
    # Format dimension names
    for dim in dimensions:
        if 'name' in dim and dim['name']:
            dim['name'] = format_dimension_name(dim['name'])
    
    # Sort by score ascending to get lowest/weakest areas first
    sorted_dims = sorted(dimensions, key=lambda d: d.get('score', 10))[:3]
    
    # Default disclaimer if not provided
    if disclaimer_text is None:
        disclaimer_text = "These recommendations are generated by AI and should be used as creative guidance. Individual artistic interpretation may vary."
    
    html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            padding: 16px;
            background: #000000;
            color: #ffffff;
        }
        .summary-header { margin-bottom: 8px; padding-bottom: 16px; }
        .summary-header h1 { font-size: 24px; font-weight: 600; margin-bottom: 8px; }
        .recommendations-list { display: flex; flex-direction: column; gap: 12px; }
        .recommendation-item {
            display: flex;
            gap: 12px;
            padding: 10px;
            background: #1c1c1e;
            border-radius: 6px;
            border-left: 3px solid #30b0c0;
        }
        .rec-number {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            background: #0a84ff;
            color: #ffffff;
            border-radius: 50%;
            font-weight: 600;
            font-size: 12px;
            flex-shrink: 0;
        }
        .rec-content { flex: 1; }
        .rec-text { font-size: 14px; line-height: 1.4; color: #e0e0e0; }
        .disclaimer {
            margin-top: 24px;
            padding: 16px;
            background: #1c1c1e;
            border-radius: 8px;
            border-left: 3px solid #ff9500;
        }
        .disclaimer p { font-size: 12px; line-height: 1.4; color: #d1d1d6; margin: 0; }
    </style>
</head>
<body>
<div class="summary-header"><h1>Top 3 Recommendations</h1></div>
<div class="recommendations-list">
'''
    
    for i, dim in enumerate(sorted_dims, 1):
        name = dim.get('name', 'Unknown')
        score = dim.get('score', 0)
        recommendation = dim.get('recommendation', 'No recommendation available.')
        
        html += f'''  <div class="recommendation-item">
    <div class="rec-number">{i}</div>
    <div class="rec-content">
      <p class="rec-text"><strong>{name}</strong> ({score}/10): {recommendation}</p>
    </div>
  </div>
'''
    
    html += f'''</div>
<div class="disclaimer">
    <p><strong>Note:</strong> {disclaimer_text}</p>
</div>
</body>
</html>'''
    
    return html


def generate_advisor_bio_html(advisor_data: Dict[str, Any]) -> str:
    """Generate iOS-compatible advisor bio HTML from database
    
    Args:
        advisor_data: Dictionary with advisor info (name, bio, years, wikipedia_url, commons_url)
    """
    
    name = advisor_data.get('name', 'Unknown Advisor')
    bio = advisor_data.get('bio', 'No biography available.')
    years = advisor_data.get('years', '')
    wikipedia_url = advisor_data.get('wikipedia_url', '')
    commons_url = advisor_data.get('commons_url', '')
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            padding: 20px;
            background: #000000;
            color: #ffffff;
            line-height: 1.6;
        }}
        .advisor-profile {{
            background: #1c1c1e;
            padding: 24px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}
        .advisor-profile h1 {{
            color: #ffffff;
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .advisor-years {{
            color: #98989d;
            font-size: 16px;
            font-weight: 400;
            margin-bottom: 16px;
        }}
        .advisor-bio {{
            color: #d1d1d6;
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 16px;
        }}
        .link-button {{
            display: inline-block;
            color: #007AFF;
            text-decoration: none;
            font-size: 16px;
            font-weight: 500;
            padding: 8px 16px;
            border: 1px solid #007AFF;
            border-radius: 6px;
            margin-right: 10px;
            margin-bottom: 10px;
        }}
    </style>
</head>
<body>
<div class="advisor-profile">
    <h1>{name}</h1>
    <p class="advisor-years">{years}</p>
    <p class="advisor-bio">{bio}</p>
'''
    
    if wikipedia_url:
        html += f'    <a href="{wikipedia_url}" class="link-button">Wikipedia</a>\n'
    if commons_url:
        html += f'    <a href="{commons_url}" class="link-button">Wikimedia Commons</a>\n'
    
    html += '''</div>
</body>
</html>'''
    
    return html
