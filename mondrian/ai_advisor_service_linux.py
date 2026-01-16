#!/usr/bin/env python3
"""
AI Advisor Service for Linux with NVIDIA CUDA Support
Uses PyTorch and HuggingFace Transformers for vision-language processing
Supports Qwen2-VL models with 4-bit quantization for RTX 3060
"""

import os
import sys
import json
import threading
import time
import sqlite3

# Set PyTorch memory optimization to reduce fragmentation
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import traceback

# Database path - project root
DB_PATH = str(Path(__file__).parent.parent / 'mondrian.db')

import torch
import torch.cuda
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Database Helper Functions
# ============================================================================

def get_config(db_path: str, key: str) -> Optional[str]:
    """Get a configuration value from the database config table"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key=?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            value = row[0]
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            return value
        return None
    except Exception as e:
        logger.error(f"Failed to get config {key}: {e}")
        return None


def get_advisor_from_db(db_path: str, advisor_id: str) -> Optional[Dict[str, Any]]:
    """Get advisor data from database advisors table"""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM advisors WHERE id = ?", (advisor_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(row)
        return None
    except Exception as e:
        logger.error(f"Failed to get advisor {advisor_id}: {e}")
        return None


class QwenAdvisor:
    """AI Advisor using Qwen2-VL or Qwen3-VL models with LoRA adapter"""
    
    def __init__(self, model_name: str = "Qwen/Qwen2-VL-7B-Instruct", 
                 load_in_4bit: bool = True, device: Optional[str] = None,
                 adapter_path: Optional[str] = None):
        """
        Initialize Qwen advisor with specified configuration
        
        Args:
            model_name: HuggingFace model ID
            load_in_4bit: Use 4-bit quantization (recommended for RTX 3060)
            device: Compute device ('cuda', 'cpu', or None for auto)
            adapter_path: Path to LoRA adapter (optional)
        """
        self.model_name = model_name
        self.load_in_4bit = load_in_4bit
        self.adapter_path = adapter_path
        self._offload_dir = None  # Track offload directory for cleanup
        
        # Determine device
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        logger.info(f"Initializing Qwen advisor on {self.device}")
        logger.info(f"Model: {model_name}")
        logger.info(f"4-bit quantization: {load_in_4bit}")
        if adapter_path:
            logger.info(f"LoRA adapter: {adapter_path}")
        
        if self.device == 'cuda':
            self._log_gpu_info()
        
        self.model = None
        self.processor = None
        self._load_model()
    
    def _log_gpu_info(self):
        """Log GPU information"""
        device_name = torch.cuda.get_device_name(0)
        device_props = torch.cuda.get_device_properties(0)
        vram_gb = device_props.total_memory / (1024**3)
        
        logger.info(f"GPU Device: {device_name}")
        logger.info(f"GPU VRAM: {vram_gb:.2f} GB")
        logger.info(f"GPU Compute Capability: {device_props.major}.{device_props.minor}")
    
    def _load_model(self):
        """Load the Qwen model, processor, and optional LoRA adapter"""
        try:
            from transformers import AutoProcessor, AutoModelForCausalLM
            
            logger.info("Loading model...")
            
            # Load processor
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            
            # Detect if this is a vision-language model (Qwen2-VL, Qwen3-VL, etc.)
            # Vision-language models require AutoModelForVision2Seq instead of AutoModelForCausalLM
            is_vision_model = "VL" in self.model_name or "vision" in self.model_name.lower()
            
            if is_vision_model:
                try:
                    from transformers import AutoModelForVision2Seq
                    model_loader = AutoModelForVision2Seq
                    logger.info("Detected vision-language model, using AutoModelForVision2Seq")
                except ImportError:
                    # Fallback to AutoModelForCausalLM if Vision2Seq not available
                    model_loader = AutoModelForCausalLM
                    logger.warning("AutoModelForVision2Seq not available, falling back to AutoModelForCausalLM")
            else:
                model_loader = AutoModelForCausalLM
            
            # Use appropriate loader for model type
            if self.load_in_4bit and self.device == 'cuda':
                from transformers import BitsAndBytesConfig
                
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                
                self.model = model_loader.from_pretrained(
                    self.model_name,
                    quantization_config=quantization_config,
                    device_map="auto",
                    low_cpu_mem_usage=True,
                    local_files_only=False,
                    trust_remote_code=True
                )
            else:
                self.model = model_loader.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
                    device_map="auto" if self.device == 'cuda' else None,
                    low_cpu_mem_usage=True,
                    local_files_only=False,
                    trust_remote_code=True
                )
                if self.device == 'cpu':
                    self.model = self.model.to('cpu')
            
            # Enable gradient checkpointing to save memory during inference
            if hasattr(self.model, 'gradient_checkpointing_enable'):
                self.model.gradient_checkpointing_enable()
                logger.info("Gradient checkpointing enabled for memory efficiency")
            
            logger.info("Model loaded successfully")
            
            # Load LoRA adapter if provided
            if self.adapter_path:
                self._load_lora_adapter()
            
        except ImportError as e:
            logger.error(f"Failed to import required libraries: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def _load_lora_adapter(self):
        """Load LoRA adapter from disk"""
        try:
            from peft import PeftModel
            from pathlib import Path
            import tempfile
            import os
            
            adapter_path = Path(self.adapter_path)
            if not adapter_path.exists():
                logger.warning(f"Adapter path does not exist: {self.adapter_path}")
                return
            
            logger.info(f"Loading LoRA adapter from {self.adapter_path}")
            
            # Create temporary offload directory for model dispatch
            offload_dir = tempfile.mkdtemp(prefix="mondrian_offload_")
            logger.info(f"Using offload directory: {offload_dir}")
            
            try:
                self.model = PeftModel.from_pretrained(
                    self.model, 
                    str(adapter_path),
                    offload_dir=offload_dir
                )
                self.model.eval()
                logger.info("LoRA adapter loaded successfully")
                
                # Store offload dir for cleanup later if needed
                self._offload_dir = offload_dir
                
            except Exception as e:
                # Cleanup offload dir if loading fails
                if os.path.exists(offload_dir):
                    import shutil
                    shutil.rmtree(offload_dir, ignore_errors=True)
                raise
            
        except Exception as e:
            logger.error(f"Failed to load LoRA adapter: {e}")
            logger.warning("Continuing with base model only")
            raise
    
    def analyze_image(self, image_path: str, advisor: str = "ansel", 
                     mode: str = "baseline") -> Dict[str, Any]:
        """
        Analyze an image and return structured insights
        
        Args:
            image_path: Path to image file
            advisor: Photography advisor persona (e.g., 'ansel')
            mode: Analysis mode ('baseline', 'rag', etc.)
        
        Returns:
            Dictionary with analysis results
        """
        try:
            # Load and validate image
            image = Image.open(image_path).convert('RGB')
            logger.info(f"Loaded image: {image_path} ({image.size})")
            
            # Create analysis prompt
            prompt = self._create_prompt(advisor, mode)
            
            # Use chat template for proper image token handling
            messages = [
                {"role": "user", "content": [
                    {"type": "image"},
                    {"type": "text", "text": prompt}
                ]}
            ]
            
            # Prepare inputs using processor with chat template
            text = self.processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            inputs = self.processor(
                text=text,
                images=[image],
                padding=True,
                return_tensors="pt"
            )
            
            # Move to device
            if self.device == 'cuda':
                inputs = {k: v.cuda() if hasattr(v, 'cuda') else v for k, v in inputs.items()}
            
            # Generate response
            logger.info("Running inference...")
            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs, 
                    max_new_tokens=2000,
                    eos_token_id=self.processor.tokenizer.eos_token_id
                )
            
            # Decode only the generated tokens (exclude input prompt)
            input_length = inputs['input_ids'].shape[1]
            generated_ids = output_ids[:, input_length:]
            
            response = self.processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )[0]
            
            logger.info(f"Generated response: {len(response)} chars")
            
            # Parse response into structured format
            analysis = self._parse_response(response, advisor, mode, prompt)
            
            return analysis
            
        except FileNotFoundError:
            logger.error(f"Image file not found: {image_path}")
            raise
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _create_prompt(self, advisor: str, mode: str) -> str:
        """Create analysis prompt by loading from database"""
        
        # Load system prompt from config table
        system_prompt = get_config(DB_PATH, "system_prompt")
        if not system_prompt:
            logger.warning("No system_prompt in database, using default")
            system_prompt = self._get_default_system_prompt()
        
        # Load advisor-specific prompt from advisors table
        advisor_data = get_advisor_from_db(DB_PATH, advisor)
        advisor_prompt = ""
        if advisor_data and advisor_data.get('prompt'):
            advisor_prompt = advisor_data['prompt']
            logger.info(f"Loaded advisor prompt for '{advisor}' ({len(advisor_prompt)} chars)")
        else:
            logger.warning(f"No prompt found for advisor '{advisor}'")
        
        # Combine prompts: system prompt + advisor prompt
        if advisor_prompt:
            full_prompt = f"{system_prompt}\n\n{advisor_prompt}"
        else:
            full_prompt = system_prompt
        
        logger.info(f"Created prompt for advisor='{advisor}', mode='{mode}' ({len(full_prompt)} chars)")
        return full_prompt
    
    def _get_default_system_prompt(self) -> str:
        """Fallback system prompt if database is unavailable"""
        return """You are a photography analysis assistant. Output valid JSON only.
Required JSON Structure:
{
  "image_description": "2-3 sentence description",
  "dimensions": [
    {"name": "Composition", "score": 8, "comment": "...", "recommendation": "..."},
    {"name": "Lighting", "score": 7, "comment": "...", "recommendation": "..."},
    {"name": "Focus & Sharpness", "score": 9, "comment": "...", "recommendation": "..."},
    {"name": "Color Harmony", "score": 6, "comment": "...", "recommendation": "..."},
    {"name": "Depth & Perspective", "score": 7, "comment": "...", "recommendation": "..."},
    {"name": "Visual Balance", "score": 8, "comment": "...", "recommendation": "..."},
    {"name": "Emotional Impact", "score": 7, "comment": "...", "recommendation": "..."}
  ],
  "overall_score": 7.4,
  "key_strengths": ["strength 1", "strength 2"],
  "priority_improvements": ["improvement 1", "improvement 2"],
  "technical_notes": "Technical observations"
}"""
    
    def _generate_ios_detailed_html(self, analysis_data: Dict[str, Any], advisor: str, mode: str) -> str:
        """Generate iOS-compatible dark theme HTML for detailed analysis"""
        
        # Extract data from the expected JSON structure
        image_description = analysis_data.get('image_description', 'Image analysis')
        dimensions = analysis_data.get('dimensions', [])
        overall_score = analysis_data.get('overall_score', 'N/A')
        technical_notes = analysis_data.get('technical_notes', '')
        
        def get_rating_style(score: int) -> tuple:
            """Return color and rating text based on score"""
            if score >= 8:
                return "#388e3c", "Excellent"  # Green
            elif score >= 6:
                return "#f57c00", "Good"       # Orange
            else:
                return "#d32f2f", "Needs Work" # Red
        
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
    </style>
</head>
<body>
<div class="advisor-section" data-advisor="{advisor}">
  <div class="analysis">
  <h2>Image Analysis</h2>
  <p>{image_description}</p>

  <h2>Detailed Dimensional Analysis & Improvement Guide</h2>
  <p style="color: #666; margin-bottom: 20px;">Each dimension is analyzed with specific feedback and actionable recommendations for improvement.</p>
'''
        
        # Add dimension cards
        for dim in dimensions:
            name = dim.get('name', 'Unknown')
            score = dim.get('score', 0)
            comment = dim.get('comment', 'No analysis available.')
            recommendation = dim.get('recommendation', 'No recommendation available.')
            color, rating = get_rating_style(score)
            
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
      <strong>💡 How to Improve:</strong>
      <p>{recommendation}</p>
    </div>
  </div>
'''
        
        html += f'''
  <h2>Overall Grade</h2>
  <p><strong>{overall_score}/10</strong></p>
  <p><strong>Grade Note:</strong> {technical_notes}</p>
</div>
</div>
</body>
</html>'''
        
        return html
    
    def _generate_summary_html(self, analysis_data: Dict[str, Any]) -> str:
        """Generate iOS-compatible summary HTML with Top 3 recommendations (lowest scoring dimensions)"""
        
        dimensions = analysis_data.get('dimensions', [])
        
        # Sort by score ascending to get lowest/weakest areas first
        sorted_dims = sorted(dimensions, key=lambda d: d.get('score', 10))[:3]
        
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
        
        html += '''</div>
<div class="disclaimer">
    <p><strong>Note:</strong> These recommendations are generated by AI and should be used as creative guidance. Individual artistic interpretation may vary.</p>
</div>
</body>
</html>'''
        
        return html
    
    def _generate_advisor_bio_html(self, advisor_data: Dict[str, Any]) -> str:
        """Generate iOS-compatible advisor bio HTML from database"""
        
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
    
    def _parse_response(self, response: str, advisor: str, mode: str, prompt: str) -> Dict[str, Any]:
        """Parse model response into structured format with iOS-compatible HTML"""
        
        # Try to extract JSON from response
        analysis_data = {}
        parse_success = False
        
        try:
            # Find JSON in response (handle both raw JSON and markdown-wrapped JSON)
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                analysis_data = json.loads(json_str)
                parse_success = True
                logger.info(f"Successfully parsed JSON response ({len(json_str)} chars)")
            else:
                logger.warning("No JSON object found in response")
                analysis_data = {
                    "image_description": "Unable to parse response",
                    "dimensions": [],
                    "overall_score": 0,
                    "raw_response": response
                }
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            analysis_data = {
                "image_description": "Unable to parse response",
                "dimensions": [],
                "overall_score": 0,
                "parse_error": str(e),
                "raw_response": response
            }
        
        # Load advisor data from database for bio
        advisor_data = get_advisor_from_db(DB_PATH, advisor)
        
        # Generate HTML outputs
        analysis_html = self._generate_ios_detailed_html(analysis_data, advisor, mode)
        summary_html = self._generate_summary_html(analysis_data)
        
        # Generate advisor bio HTML from database
        if advisor_data:
            advisor_bio_html = self._generate_advisor_bio_html(advisor_data)
            advisor_bio = advisor_data.get('bio', f"Analysis by {advisor.title()}")
        else:
            advisor_bio_html = f"<html><body><p>Analysis by {advisor.title()}</p></body></html>"
            advisor_bio = f"Analysis by {advisor.title()}"
        
        # Extract text summary from image_description
        summary = analysis_data.get('image_description', response[:500])
        
        # Calculate overall score if not provided
        overall_score = analysis_data.get('overall_score', None)
        if overall_score is None and 'dimensions' in analysis_data:
            dimensions = analysis_data.get('dimensions', [])
            if dimensions:
                scores = [d.get('score', 0) for d in dimensions]
                overall_score = sum(scores) / len(scores) if scores else 0
        
        # Wrap in standard response format matching expected job service fields
        result = {
            "advisor": advisor,
            "mode": mode,
            "model": self.model_name,
            "device": self.device,
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,  # System+advisor prompt sent to LLM
            "llm_prompt": prompt,  # For compatibility
            "full_response": response,  # Complete LLM response (JSON string)
            "llm_thinking": response,  # Complete response
            "analysis": analysis_data,  # Structured JSON data
            "analysis_html": analysis_html,  # Detailed HTML for iOS WebView
            "summary_html": summary_html,  # Top 3 recommendations HTML
            "advisor_bio_html": advisor_bio_html,  # Advisor biography HTML
            "summary": summary,  # Text summary
            "advisor_bio": advisor_bio,  # Text bio
            "overall_score": overall_score,  # Numeric score
            "parse_success": parse_success  # Whether JSON parsing succeeded
        }
        
        logger.info(f"Response parsed: {len(analysis_data.get('dimensions', []))} dimensions, score={overall_score}")
        
        return result


# Flask app setup
app = Flask(__name__)
CORS(app)

# Global advisor instance
advisor = None

# Loading status tracking
loading_status = {
    'started': False,
    'completed': False,
    'error': None,
    'progress': 0,
    'message': 'Not started'
}

def init_advisor(model_name: str, load_in_4bit: bool, adapter_path: Optional[str] = None):
    """Initialize the advisor service"""
    global advisor, loading_status
    try:
        loading_status['started'] = True
        loading_status['message'] = f'Loading model {model_name}...'
        loading_status['progress'] = 10
        
        advisor = QwenAdvisor(
            model_name=model_name,
            load_in_4bit=load_in_4bit,
            adapter_path=adapter_path
        )
        
        loading_status['completed'] = True
        loading_status['progress'] = 100
        loading_status['message'] = 'Model ready'
        logger.info("Advisor service initialized successfully")
    except Exception as e:
        loading_status['error'] = str(e)
        loading_status['completed'] = True
        logger.error(f"Failed to initialize advisor: {e}")
        raise


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint - returns status even while loading"""
    if advisor:
        return jsonify({
            "status": "healthy",
            "model": advisor.model_name,
            "device": advisor.device,
            "using_gpu": advisor.device == 'cuda',
            "loading": False,
            "timestamp": datetime.now().isoformat()
        }), 200
    elif loading_status['error']:
        return jsonify({
            "status": "error",
            "error": loading_status['error'],
            "loading": False,
            "timestamp": datetime.now().isoformat()
        }), 503
    else:
        # Still loading
        return jsonify({
            "status": "loading",
            "progress": loading_status['progress'],
            "message": loading_status['message'],
            "loading": True,
            "timestamp": datetime.now().isoformat()
        }), 202


@app.route('/model-status', methods=['GET'])
def model_status():
    """Get model and device status"""
    if loading_status['error']:
        return jsonify({
            "status": "error",
            "error": loading_status['error'],
            "progress": 0
        }), 503
    
    if not advisor:
        # Still loading
        return jsonify({
            "status": "loading",
            "progress": loading_status['progress'],
            "message": loading_status['message']
        }), 202
    
    return jsonify({
        "status": "ready",
        "model": advisor.model_name,
        "device": advisor.device,
        "using_gpu": advisor.device == 'cuda',
        "gpu_memory_total": torch.cuda.get_device_properties(0).total_memory / (1024**3) if advisor.device == 'cuda' else None,
        "gpu_memory_used": torch.cuda.memory_allocated(0) / (1024**3) if advisor.device == 'cuda' else None,
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze an image"""
    if not advisor:
        return jsonify({"error": "Service not initialized"}), 503
    
    try:
        # Get image from request
        if 'image' not in request.files:
            return jsonify({"error": "No image provided"}), 400
        
        image_file = request.files['image']
        
        # Save temporarily
        temp_path = f"/tmp/{image_file.filename}"
        image_file.save(temp_path)
        
        # Get parameters
        advisor_name = request.form.get('advisor', 'ansel')
        mode = request.form.get('enable_rag', 'false').lower() == 'true'
        mode_str = 'rag' if mode else 'baseline'
        
        # Run analysis
        logger.info(f"Analyzing image with advisor={advisor_name}, mode={mode_str}")
        result = advisor.analyze_image(temp_path, advisor=advisor_name, mode=mode_str)
        
        # Clean up
        Path(temp_path).unlink()
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


@app.errorhandler(500)
def handle_error(e):
    """Handle internal server errors"""
    logger.error(f"Server error: {e}")
    return jsonify({"error": "Internal server error"}), 500


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='AI Advisor Service for Linux CUDA')
    parser.add_argument('--port', type=int, default=5100, help='Service port')
    parser.add_argument('--model', default='Qwen/Qwen3-VL-4B-Instruct', help='Model to use')
    parser.add_argument('--adapter', default='adapters/ansel/epoch_10', help='Path to LoRA adapter')
    parser.add_argument('--load_in_4bit', action='store_true', help='Use 4-bit quantization')
    parser.add_argument('--load_in_8bit', action='store_true', help='Use 8-bit quantization')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    # Log startup info
    logger.info("Starting AI Advisor Service")
    logger.info(f"Port: {args.port}")
    logger.info(f"Model: {args.model}")
    logger.info(f"Adapter: {args.adapter}")
    logger.info(f"4-bit quantization: {args.load_in_4bit}")
    
    # Start Flask server in a background thread BEFORE loading the model
    # This ensures the service responds to health checks while loading
    def run_flask():
        logger.info(f"Flask server starting on {args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Give Flask a moment to start listening
    time.sleep(2)
    
    # NOW load the model in the main thread
    try:
        logger.info("Loading model (this may take several minutes)...")
        init_advisor(args.model, args.load_in_4bit, adapter_path=args.adapter)
        
        # Keep the main thread alive
        flask_thread.join()
    except Exception as e:
        logger.error(f"Fatal error during initialization: {e}")
        logger.error(traceback.format_exc())
        # Flask will still respond with error status
        flask_thread.join()


if __name__ == '__main__':
    main()
