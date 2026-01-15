#!/usr/bin/env python3
"""
AI Advisor Service for Linux with NVIDIA CUDA Support
Uses PyTorch and HuggingFace Transformers for vision-language processing
Supports Qwen2-VL-7B-Instruct model with 4-bit quantization for RTX 3060
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import traceback

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

class QwenAdvisor:
    """AI Advisor using Qwen2-VL-7B-Instruct model"""
    
    def __init__(self, model_name: str = "Qwen/Qwen2-VL-7B-Instruct", 
                 load_in_4bit: bool = True, device: Optional[str] = None):
        """
        Initialize Qwen advisor with specified configuration
        
        Args:
            model_name: HuggingFace model ID
            load_in_4bit: Use 4-bit quantization (recommended for RTX 3060)
            device: Compute device ('cuda', 'cpu', or None for auto)
        """
        self.model_name = model_name
        self.load_in_4bit = load_in_4bit
        
        # Determine device
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        logger.info(f"Initializing Qwen advisor on {self.device}")
        logger.info(f"Model: {model_name}")
        logger.info(f"4-bit quantization: {load_in_4bit}")
        
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
        """Load the Qwen model and processor"""
        try:
            from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
            
            logger.info("Loading model...")
            
            # Load processor
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            
            # Load model with quantization if requested
            if self.load_in_4bit and self.device == 'cuda':
                from transformers import BitsAndBytesConfig
                
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                
                self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                    self.model_name,
                    quantization_config=quantization_config,
                    device_map="auto"
                )
            else:
                self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
                    device_map="auto" if self.device == 'cuda' else None
                )
                if self.device == 'cpu':
                    self.model = self.model.to('cpu')
            
            logger.info("Model loaded successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import required libraries: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
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
            
            # Prepare inputs
            inputs = self.processor(
                text=prompt,
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
                output_ids = self.model.generate(**inputs, max_new_tokens=2000)
            
            # Decode response
            response = self.processor.batch_decode(
                output_ids, 
                skip_special_tokens=True
            )[0]
            
            # Parse response into structured format
            analysis = self._parse_response(response, advisor, mode)
            
            return analysis
            
        except FileNotFoundError:
            logger.error(f"Image file not found: {image_path}")
            raise
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _create_prompt(self, advisor: str, mode: str) -> str:
        """Create analysis prompt based on advisor and mode"""
        
        base_prompt = """Analyze this photograph in detail. Provide a comprehensive assessment covering:

1. **Composition**: Discuss the framing, rule of thirds, leading lines, and visual balance
2. **Technical Excellence**: Evaluate focus, exposure, dynamic range, and sharpness
3. **Lighting**: Analyze the quality, direction, and mood created by light
4. **Color Palette**: Discuss dominant colors and their emotional impact
5. **Subject Matter**: Describe what the photograph depicts
6. **Emotional Impact**: What feeling or mood does this image convey?

Format your response as a JSON object with keys: composition, technical_excellence, lighting, color_palette, subject_matter, emotional_impact"""
        
        if advisor == "ansel":
            base_prompt = """As an expert photography advisor in the style of Ansel Adams, analyze this photograph.

Ansel Adams emphasizes: tonal ranges, technical mastery, landscape drama, and the relationship between light and shadow.

Provide analysis covering:
1. **Tonal Range and Contrast**: Evaluate blacks, whites, and midtones
2. **Technical Mastery**: Assess sharpness, exposure, and clarity
3. **Compositional Strength**: Analyze structure and visual hierarchy
4. **Light and Shadow**: Discuss how light creates drama and mood
5. **Emotional Resonance**: What does this image make you feel?

Format as JSON with keys: tonal_range, technical_mastery, composition, light_and_shadow, emotional_resonance"""
        
        return base_prompt
    
    def _parse_response(self, response: str, advisor: str, mode: str) -> Dict[str, Any]:
        """Parse model response into structured format"""
        
        # Try to extract JSON from response
        try:
            # Find JSON in response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                analysis_data = json.loads(json_str)
            else:
                # Fallback: create structured response from text
                analysis_data = {
                    "analysis": response,
                    "raw_response": True
                }
        except json.JSONDecodeError:
            analysis_data = {
                "analysis": response,
                "parse_error": True
            }
        
        # Wrap in standard response format
        result = {
            "advisor": advisor,
            "mode": mode,
            "model": self.model_name,
            "device": self.device,
            "timestamp": datetime.now().isoformat(),
            "analysis": analysis_data
        }
        
        return result


# Flask app setup
app = Flask(__name__)
CORS(app)

# Global advisor instance
advisor = None

def init_advisor(model_name: str, load_in_4bit: bool):
    """Initialize the advisor service"""
    global advisor
    try:
        advisor = QwenAdvisor(
            model_name=model_name,
            load_in_4bit=load_in_4bit
        )
        logger.info("Advisor service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize advisor: {e}")
        raise


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy" if advisor else "initializing",
        "model": advisor.model_name if advisor else None,
        "device": advisor.device if advisor else None,
        "using_gpu": advisor.device == 'cuda' if advisor else False,
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/model-status', methods=['GET'])
def model_status():
    """Get model and device status"""
    if not advisor:
        return jsonify({"error": "Service not initialized"}), 503
    
    return jsonify({
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
    parser.add_argument('--model', default='Qwen/Qwen2-VL-7B-Instruct', help='Model to use')
    parser.add_argument('--load_in_4bit', action='store_true', help='Use 4-bit quantization')
    parser.add_argument('--load_in_8bit', action='store_true', help='Use 8-bit quantization')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    args = parser.parse_args()
    
    # Initialize advisor
    logger.info("Starting AI Advisor Service")
    logger.info(f"Port: {args.port}")
    logger.info(f"Model: {args.model}")
    logger.info(f"4-bit quantization: {args.load_in_4bit}")
    
    init_advisor(args.model, args.load_in_4bit)
    
    # Start Flask server
    logger.info(f"Starting Flask server on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
