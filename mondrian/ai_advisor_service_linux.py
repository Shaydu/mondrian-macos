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

# Set PyTorch memory optimization to reduce fragmentation
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
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
    parser.add_argument('--model', default='Qwen/Qwen2-VL-7B-Instruct', help='Model to use')
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
