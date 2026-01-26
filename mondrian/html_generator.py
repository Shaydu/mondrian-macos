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


def resolve_image_path(image_path: str) -> Optional[str]:
    """
    Resolve image path for Docker/RunPod environments (working dir: /app).
    Database may contain absolute paths from development machine, but in Docker
    images are at ./mondrian/source/...
    
    Args:
        image_path: Path from database (may be absolute from dev machine or relative)
    
    Returns:
        Resolved path to image file in container, or None if not found
    """
    if not image_path:
        return None
    
    logger.debug(f"[Path Resolve] Resolving: {image_path}")
    
    # If absolute path (from development machine), extract the mondrian-relative part
    if os.path.isabs(image_path):
        # Example: /home/doo/dev/mondrian-macos/mondrian/source/... → mondrian/source/...
        if 'mondrian/' in image_path:
            relative = image_path[image_path.find('mondrian/'):]
            if os.path.exists(relative):
                logger.debug(f"[Path Resolve] ✅ Found: {relative}")
                return relative
            
            # Try with ./ prefix for Docker
            relative_dot = f"./{relative}"
            if os.path.exists(relative_dot):
                logger.debug(f"[Path Resolve] ✅ Found: {relative_dot}")
                return relative_dot
    
    # If already relative, try as-is and with common prefixes
    fallbacks = [
        image_path,
        f"mondrian/{image_path}",
        f"./mondrian/{image_path}",
    ]
    
    for path in fallbacks:
        if os.path.exists(path):
            logger.debug(f"[Path Resolve] ✅ Found: {path}")
            return path
    
    # Last resort: search by filename in advisor directories
    filename = os.path.basename(image_path)
    search_dirs = [
        "mondrian/source/advisor/photographer",
        "mondrian/source/advisor/painter", 
        "mondrian/source/advisor/architect",
    ]
    
    for base in search_dirs:
        if os.path.isdir(base):
            for root, _, files in os.walk(base):
                if filename in files:
                    found = os.path.join(root, filename)
                    logger.info(f"[Path Resolve] ✅ Found by search: {found}")
                    return found
    
    logger.warning(f"[Path Resolve] ❌ Not found: {image_path}")
    return None


def generate_reference_image_html(
    ref_image: Dict[str, Any],
    dimension_name: str,
    ref_score: Optional[float] = None,
    user_gap: Optional[float] = None
) -> str:
    """
    Generate consolidated HTML for reference image case study box.
    
    Args:
        ref_image: Dictionary containing reference image data from database
        dimension_name: Display name of the dimension (e.g., "Composition")
        ref_score: Optional reference score to display
        user_gap: Optional gap between user and reference score
    
    Returns:
        HTML string for case study box
    """
    ref_title = ref_image.get('image_title', 'Reference Image')
    ref_year = ref_image.get('date_taken', '')
    ref_path = ref_image.get('image_path', '')
    ref_location = ref_image.get('location', '')
    
    # Format title with year
    if ref_year and str(ref_year).strip():
        title_with_year = f"{ref_title} ({ref_year})"
    else:
        title_with_year = ref_title
    
    # Get image data and convert to base64 with smart path resolution
    ref_image_url = ''
    if ref_path:
        logger.info(f"[HTML Gen] Attempting to load image: {ref_path} for dimension: {dimension_name}")
        resolved_path = resolve_image_path(ref_path)
        if resolved_path:
            try:
                logger.info(f"[HTML Gen] Resolved path: {resolved_path}")
                with open(resolved_path, 'rb') as img_file:
                    image_data = img_file.read()
                    b64_image = base64.b64encode(image_data).decode('utf-8')
                    img_ext = os.path.splitext(resolved_path)[1].lower()
                    mime_type = 'image/png' if img_ext == '.png' else 'image/jpeg' if img_ext in ['.jpg', '.jpeg'] else 'image/png'
                    ref_image_url = f"data:{mime_type};base64,{b64_image}"
                    logger.info(f"[HTML Gen] ✅ Successfully embedded reference image: {os.path.basename(resolved_path)} ({len(image_data)} bytes, base64: {len(b64_image)} chars)")
            except Exception as e:
                logger.error(f"[HTML Gen] ❌ Failed to embed image as base64: {e} (resolved_path={resolved_path})", exc_info=True)
        else:
            logger.error(f"[HTML Gen] ❌ Could not resolve image path for reference: {ref_path} (dimension={dimension_name})")
    
    # Build case study box
    html = '<div class="reference-citation"><div class="case-study-box">'
    html += f'<div class="case-study-title">Case Study: {title_with_year}</div>'
    
    if ref_image_url:
        html += f'<img src="{ref_image_url}" alt="{title_with_year}" class="case-study-image" />'
    
    # Add metadata - use instructive text if available
    metadata_parts = []
    
    # Get dimension-specific instructive text
    dim_key = dimension_name.lower().replace(' ', '_')
    instructive_key = f"{dim_key}_instructive"
    instructive_text = ref_image.get(instructive_key)
    
    if instructive_text:
        # Use pre-generated instructive explanation
        metadata_parts.append(f'<strong>Focus On:</strong> {instructive_text}')
    elif ref_image.get('image_description'):
        # Fallback to description if no instructive text
        metadata_parts.append(f'<strong>Focus On:</strong> {ref_image["image_description"][:200]}...')
    
    if ref_location:
        metadata_parts.append(f'<strong>Location:</strong> {ref_location}')
    
    if ref_score is not None:
        metadata_parts.append(f'<strong>Reference Score:</strong> {ref_score}/10 in {dimension_name}')
    
    if user_gap is not None:
        metadata_parts.append(f'<strong>Your Gap:</strong> {user_gap:.1f} points')
    
    html += f'<div class="case-study-metadata">' + '<br/>'.join(metadata_parts) + '</div>'
    html += '</div></div>'
    
    logger.info(f"[HTML Gen] Generated case study for {dimension_name}: '{ref_title}'")
    
    return html


def normalize_dimension_key(name: str) -> str:
    """Normalize dimension name for lookup"""
    dim_key = name.lower().strip().replace(' & ', '_').replace(' and ', '_').replace(' ', '_')
    
    if 'focus' in dim_key:
        return 'focus_sharpness'
    elif 'depth' in dim_key:
        return 'depth_perspective'
    elif 'balance' in dim_key:
        return 'visual_balance'
    elif 'emotion' in dim_key or 'impact' in dim_key:
        return 'emotional_impact'
    
    return dim_key


# DEPRECATED: Use QwenAdvisor._generate_ios_detailed_html() instead
# This standalone function has been moved to ai_advisor_service_linux.py as a class method
# The class method has full support for rendering quotes from book_passages
def generate_ios_detailed_html(
    analysis_data: Dict[str, Any], 
    advisor: str, 
    mode: str, 
    case_studies: List[Dict[str, Any]] = None
) -> str:
    """DEPRECATED: Do not use this function - use QwenAdvisor._generate_ios_detailed_html() instead
    
    This function is kept for backwards compatibility but does NOT support quote rendering.
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
            width: 99%;
            margin-left: auto;
            margin-right: auto;
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
            
            reference_citation = generate_reference_image_html(
                ref_image=best_ref,
                dimension_name=name,
                ref_score=ref_score_val,
                user_gap=best_gap
            )
        
        # Check if LLM cited a quote for this dimension
        quote_citation_html = ""
        cited_quote = dim.get('_cited_quote')
        if cited_quote:
            book_title = cited_quote.get('book_title', 'Unknown Book')
            passage_text = cited_quote.get('passage_text', cited_quote.get('text', ''))
            
            # Truncate to 75 words
            words = passage_text.split()
            truncated_text = ' '.join(words[:75])
            if len(words) > 75:
                truncated_text += "..."
            
            quote_citation_html = '<div class="advisor-quote-box">'
            quote_citation_html += '<div class="advisor-quote-title">Advisor Insight</div>'
            quote_citation_html += f'<div class="advisor-quote-text">"{truncated_text}"</div>'
            quote_citation_html += f'<div class="advisor-quote-source"><strong>From:</strong> {book_title}</div>'
            quote_citation_html += '</div>'
            
            logger.info(f"[HTML Gen] Added LLM-cited quote for {name} from '{book_title}'")
        
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
    </div>{reference_citation}{quote_citation_html}
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
    
    # Check if dimensions are missing or empty
    if not dimensions or len(dimensions) == 0:
        logger.warning(f"⚠️  generate_summary_html: No dimensions found in analysis_data. Keys: {list(analysis_data.keys())}")
        if 'parse_error' in analysis_data:
            logger.error(f"❌ Parse error detected: {analysis_data.get('parse_error', 'Unknown')}")
        # Return fallback HTML
        return f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 16px; background: #000000; color: #ffffff; }}
        .error {{ background: #1c1c1e; padding: 20px; border-radius: 8px; border-left: 3px solid #ff3b30; margin: 16px 0; }}
        .error p {{ margin: 8px 0; color: #d1d1d6; }}
    </style>
</head>
<body>
<div class="error">
    <p><strong>⚠️ Unable to Generate Recommendations</strong></p>
    <p>The analysis failed to parse properly. Error: {analysis_data.get('parse_error', 'JSON parsing failed - dimensions array is empty')}</p>
    <p>This typically indicates the model response was incomplete or truncated.</p>
</div>
</body>
</html>'''
    
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
            width: 99%;
            margin-left: auto;
            margin-right: auto;
        }
        .summary-header { margin-bottom: 8px; padding-bottom: 16px; }
        .summary-header h1 { font-size: 24px; font-weight: 600; margin-bottom: 8px; }
        .recommendations-list { display: flex; flex-direction: column; gap: 12px; width: 99%; margin-left: auto; margin-right: auto; }
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
        
        # Strip IMG_X references since images are shown in detailed view
        recommendation = re.sub(r'\bIMG_\d+\b', '', recommendation)
        # Clean up extra spaces and punctuation left by removal
        recommendation = re.sub(r'\s+', ' ', recommendation).strip()
        recommendation = re.sub(r'\s+([.,;:])', r'\1', recommendation)  # Fix spacing before punctuation
        
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
