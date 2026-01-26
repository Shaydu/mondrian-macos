#!/usr/bin/env python3
"""
Citation rendering service for advisor case studies and quotes.
Centralizes HTML generation for dimension-specific citations.
"""
import logging

logger = logging.getLogger(__name__)


def render_cited_image_html(cited_image: dict, dimension_name: str) -> str:
    """
    Render HTML for a cited reference image in a dimension card.
    
    Args:
        cited_image: Image dict with keys: title, year, photographer, image_path, score, dimensions
        dimension_name: Name of the dimension citing this image
    
    Returns:
        HTML string for the case study citation box
    """
    from mondrian.html_generator import generate_reference_image_html
    
    return generate_reference_image_html(
        ref_image=cited_image,
        dimension_name=dimension_name
    )


def render_cited_quote_html(cited_quote: dict, dimension_name: str) -> str:
    """
    Render HTML for a cited advisor quote in a dimension card.
    
    Args:
        cited_quote: Quote dict with keys: book_title, passage_text (or text), dimensions
        dimension_name: Name of the dimension citing this quote
    
    Returns:
        HTML string for the advisor quote box
    """
    book_title = cited_quote.get('book_title', 'Unknown Book')
    passage_text = cited_quote.get('passage_text', cited_quote.get('text', ''))
    
    # Truncate to 75 words
    words = passage_text.split()
    truncated_text = ' '.join(words[:75])
    if len(words) > 75:
        truncated_text += "..."
    
    html = '<div class="advisor-quote-box">'
    html += '<div class="advisor-quote-title">Advisor Insight</div>'
    html += f'<div class="advisor-quote-text">"{truncated_text}"</div>'
    html += f'<div class="advisor-quote-source"><strong>From:</strong> {book_title}</div>'
    html += '</div>'
    
    logger.info(f"[Citation Service] Rendered quote for {dimension_name} from '{book_title}'")
    
    return html
