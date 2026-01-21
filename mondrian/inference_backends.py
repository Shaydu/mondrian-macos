#!/usr/bin/env python3
"""
Inference Backends for AI Advisor Service

Switchable backends for benchmarking different inference strategies:
- bnb: BitsAndBytes 4-bit quantization (default, current implementation)
- vllm: vLLM high-performance inference server
- awq: AutoAWQ quantization

Usage:
    ./mondrian.sh --restart --backend=bnb      # Default (BitsAndBytes 4-bit)
    ./mondrian.sh --restart --backend=vllm     # vLLM server
    ./mondrian.sh --restart --backend=awq      # AutoAWQ quantization
"""

import os
import sys
import time
import logging
import threading
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Generator
from pathlib import Path

import torch

logger = logging.getLogger(__name__)

# Load configuration for dynamic settings
def load_model_config():
    """Load model_config.json for dynamic settings"""
    config_path = Path(__file__).parent.parent / 'model_config.json'
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load model_config.json: {e}, using defaults")
        return {
            "runtime_config": {
                "token_limits": {"inference_backend_default": 2500}
            }
        }

MODEL_CONFIG = load_model_config()
DEFAULT_BACKEND_MAX_TOKENS = MODEL_CONFIG.get("runtime_config", {}).get("token_limits", {}).get("inference_backend_default", 2500)

# ============================================================================
# Backend Registry
# ============================================================================

AVAILABLE_BACKENDS = {
    'bnb': 'BitsAndBytesBackend',
    'vllm': 'VLLMBackend', 
    'awq': 'AWQBackend',
}

DEFAULT_BACKEND = 'bnb'


def get_backend(backend_name: str = None):
    """Get the appropriate backend class"""
    if backend_name is None:
        backend_name = DEFAULT_BACKEND
    
    backend_name = backend_name.lower()
    if backend_name not in AVAILABLE_BACKENDS:
        logger.warning(f"Unknown backend '{backend_name}', falling back to '{DEFAULT_BACKEND}'")
        backend_name = DEFAULT_BACKEND
    
    return backend_name


# ============================================================================
# Abstract Base Backend
# ============================================================================

class InferenceBackend(ABC):
    """Abstract base class for inference backends"""
    
    def __init__(self, model_name: str, adapter_path: Optional[str] = None, 
                 device: str = 'cuda', **kwargs):
        self.model_name = model_name
        self.adapter_path = adapter_path
        self.device = device
        self.model = None
        self.processor = None
        self.kwargs = kwargs
        self._benchmark_stats = {
            'total_tokens': 0,
            'total_time': 0.0,
            'inference_count': 0,
        }
    
    @abstractmethod
    def load(self) -> None:
        """Load the model and processor"""
        pass
    
    @abstractmethod
    def generate(self, inputs: Dict[str, Any], max_new_tokens: int = None,
                 **generation_kwargs) -> str:
        """Generate response from inputs"""
        pass
    
    @abstractmethod
    def get_backend_info(self) -> Dict[str, Any]:
        """Return information about this backend for benchmarking"""
        pass
    
    def get_benchmark_stats(self) -> Dict[str, Any]:
        """Return accumulated benchmark statistics"""
        stats = self._benchmark_stats.copy()
        if stats['total_time'] > 0:
            stats['avg_tokens_per_sec'] = stats['total_tokens'] / stats['total_time']
        else:
            stats['avg_tokens_per_sec'] = 0
        if stats['inference_count'] > 0:
            stats['avg_time_per_inference'] = stats['total_time'] / stats['inference_count']
        else:
            stats['avg_time_per_inference'] = 0
        return stats
    
    def reset_benchmark_stats(self):
        """Reset benchmark statistics"""
        self._benchmark_stats = {
            'total_tokens': 0,
            'total_time': 0.0,
            'inference_count': 0,
        }
    
    def _record_benchmark(self, tokens_generated: int, time_elapsed: float):
        """Record benchmark data point"""
        self._benchmark_stats['total_tokens'] += tokens_generated
        self._benchmark_stats['total_time'] += time_elapsed
        self._benchmark_stats['inference_count'] += 1


# ============================================================================
# BitsAndBytes Backend (Default - Current Implementation)
# ============================================================================

class BitsAndBytesBackend(InferenceBackend):
    """
    BitsAndBytes 4-bit quantization backend.
    This is the current/default implementation.
    """
    
    def __init__(self, model_name: str, adapter_path: Optional[str] = None,
                 device: str = 'cuda', load_in_4bit: bool = True, **kwargs):
        super().__init__(model_name, adapter_path, device, **kwargs)
        self.load_in_4bit = load_in_4bit
        self._offload_dir = None
    
    def load(self) -> None:
        """Load model with BitsAndBytes quantization"""
        from transformers import AutoProcessor, AutoModelForCausalLM
        
        logger.info(f"[BNB Backend] Loading model: {self.model_name}")
        logger.info(f"[BNB Backend] 4-bit quantization: {self.load_in_4bit}")
        
        # Load processor
        self.processor = AutoProcessor.from_pretrained(self.model_name)
        
        # Detect vision-language model
        is_vision_model = "VL" in self.model_name or "vision" in self.model_name.lower()
        
        if is_vision_model:
            try:
                from transformers import AutoModelForVision2Seq
                model_loader = AutoModelForVision2Seq
                logger.info("[BNB Backend] Using AutoModelForVision2Seq for VL model")
            except ImportError:
                model_loader = AutoModelForCausalLM
                logger.warning("[BNB Backend] Falling back to AutoModelForCausalLM")
        else:
            model_loader = AutoModelForCausalLM
        
        # Load with BitsAndBytes config
        if self.load_in_4bit and self.device == 'cuda':
            from transformers import BitsAndBytesConfig
            
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
            
            # Try Flash Attention 2
            try:
                self.model = model_loader.from_pretrained(
                    self.model_name,
                    quantization_config=quantization_config,
                    device_map="auto",
                    low_cpu_mem_usage=True,
                    trust_remote_code=True,
                    attn_implementation="flash_attention_2"
                )
                logger.info("[BNB Backend] Flash Attention 2 enabled")
            except Exception as fa_error:
                logger.warning(f"[BNB Backend] Flash Attention 2 not available: {fa_error}")
                self.model = model_loader.from_pretrained(
                    self.model_name,
                    quantization_config=quantization_config,
                    device_map="auto",
                    low_cpu_mem_usage=True,
                    trust_remote_code=True
                )
        else:
            self.model = model_loader.from_pretrained(
                self.model_name,
                torch_dtype=torch.bfloat16 if self.device == 'cuda' else torch.float32,
                device_map="auto" if self.device == 'cuda' else None,
                low_cpu_mem_usage=True,
                trust_remote_code=True
            )
        
        logger.info("[BNB Backend] Model loaded successfully")
        
        # Load LoRA adapter if provided
        if self.adapter_path:
            self._load_lora_adapter()
    
    def _load_lora_adapter(self):
        """Load LoRA adapter"""
        try:
            from peft import PeftModel
            import tempfile
            
            adapter_path = Path(self.adapter_path)
            if not adapter_path.exists():
                logger.warning(f"[BNB Backend] Adapter not found: {self.adapter_path}")
                return
            
            logger.info(f"[BNB Backend] Loading LoRA adapter: {self.adapter_path}")
            
            offload_dir = tempfile.mkdtemp(prefix="mondrian_offload_")
            
            self.model = PeftModel.from_pretrained(
                self.model,
                str(adapter_path),
                offload_dir=offload_dir
            )
            self.model.eval()
            self._offload_dir = offload_dir
            
            logger.info("[BNB Backend] LoRA adapter loaded successfully")
            
        except Exception as e:
            logger.error(f"[BNB Backend] Failed to load LoRA adapter: {e}")
            raise
    
    def generate(self, inputs: Dict[str, Any], max_new_tokens: int = None,
                 **generation_kwargs) -> str:
        """Generate response using BitsAndBytes quantized model"""
        # Use config default if not specified
        if max_new_tokens is None:
            max_new_tokens = DEFAULT_BACKEND_MAX_TOKENS
        
        start_time = time.time()
        
        # Move inputs to CUDA
        if self.device == 'cuda':
            inputs = {k: v.cuda(non_blocking=True) if hasattr(v, 'cuda') else v 
                     for k, v in inputs.items()}
        
        # Generate with optimized settings
        with torch.no_grad(), torch.cuda.amp.autocast(dtype=torch.bfloat16):
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                repetition_penalty=1.0,
                do_sample=False,
                use_cache=True,
                num_beams=1,
                pad_token_id=self.processor.tokenizer.pad_token_id,
                eos_token_id=self.processor.tokenizer.eos_token_id,
                **generation_kwargs
            )
        
        # Decode
        input_length = inputs['input_ids'].shape[1]
        generated_ids = output_ids[:, input_length:]
        
        response = self.processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]
        
        # Record benchmark
        elapsed = time.time() - start_time
        tokens_generated = generated_ids.shape[1]
        self._record_benchmark(tokens_generated, elapsed)
        
        logger.info(f"[BNB Backend] Generated {tokens_generated} tokens in {elapsed:.2f}s "
                   f"({tokens_generated/elapsed:.1f} tok/s)")
        
        return response
    
    def get_backend_info(self) -> Dict[str, Any]:
        return {
            'name': 'BitsAndBytes',
            'type': 'bnb',
            'quantization': '4-bit NF4' if self.load_in_4bit else 'none',
            'compute_dtype': 'bfloat16',
            'flash_attention': True,
            'model': self.model_name,
            'adapter': self.adapter_path,
        }


# ============================================================================
# vLLM Backend (High Performance)
# ============================================================================

class VLLMBackend(InferenceBackend):
    """
    vLLM backend for high-performance inference.
    Uses PagedAttention and continuous batching for much faster throughput.
    
    Requirements:
        pip install vllm
    """
    
    def __init__(self, model_name: str, adapter_path: Optional[str] = None,
                 device: str = 'cuda', tensor_parallel_size: int = 1,
                 gpu_memory_utilization: float = 0.85, **kwargs):
        super().__init__(model_name, adapter_path, device, **kwargs)
        self.tensor_parallel_size = tensor_parallel_size
        self.gpu_memory_utilization = gpu_memory_utilization
        self.llm = None
        self.sampling_params = None
    
    def load(self) -> None:
        """Load model using vLLM"""
        try:
            from vllm import LLM, SamplingParams
            from transformers import AutoProcessor
        except ImportError:
            raise ImportError(
                "[vLLM Backend] vLLM not installed. Install with:\n"
                "  pip install vllm\n"
                "Note: vLLM requires CUDA and may need specific PyTorch version."
            )
        
        logger.info(f"[vLLM Backend] Loading model: {self.model_name}")
        logger.info(f"[vLLM Backend] GPU memory utilization: {self.gpu_memory_utilization}")
        
        # Load processor for tokenization
        self.processor = AutoProcessor.from_pretrained(self.model_name)
        
        # vLLM engine configuration
        engine_args = {
            'model': self.model_name,
            'trust_remote_code': True,
            'tensor_parallel_size': self.tensor_parallel_size,
            'gpu_memory_utilization': self.gpu_memory_utilization,
            'dtype': 'bfloat16',
            'max_model_len': 8192,  # Adjust based on your needs
        }
        
        # Add LoRA adapter if specified
        if self.adapter_path:
            adapter_path = Path(self.adapter_path)
            if adapter_path.exists():
                engine_args['enable_lora'] = True
                logger.info(f"[vLLM Backend] LoRA enabled: {self.adapter_path}")
            else:
                logger.warning(f"[vLLM Backend] Adapter not found: {self.adapter_path}")
        
        # Initialize vLLM
        self.llm = LLM(**engine_args)
        
        # Default sampling params (greedy)
        self.sampling_params = SamplingParams(
            temperature=0,
            max_tokens=2500,
            repetition_penalty=1.0,
        )
        
        logger.info("[vLLM Backend] Model loaded successfully")
    
    def generate(self, inputs: Dict[str, Any], max_new_tokens: int = None,
                 **generation_kwargs) -> str:
        """Generate response using vLLM"""
        # Use config default if not specified
        if max_new_tokens is None:
            max_new_tokens = DEFAULT_BACKEND_MAX_TOKENS
        
        from vllm import SamplingParams
        
        start_time = time.time()
        
        # vLLM uses text input, not tokenized
        # For VL models, we need to handle images specially
        # This is a simplified implementation - full VL support requires vLLM-specific handling
        
        # Update sampling params
        sampling_params = SamplingParams(
            temperature=generation_kwargs.get('temperature', 0),
            max_tokens=max_new_tokens,
            repetition_penalty=generation_kwargs.get('repetition_penalty', 1.0),
        )
        
        # For now, decode input_ids back to text (vLLM prefers text input)
        if 'input_ids' in inputs:
            prompt = self.processor.tokenizer.decode(inputs['input_ids'][0], skip_special_tokens=False)
        else:
            raise ValueError("[vLLM Backend] input_ids required in inputs")
        
        # Generate
        outputs = self.llm.generate([prompt], sampling_params)
        
        response = outputs[0].outputs[0].text
        
        # Record benchmark
        elapsed = time.time() - start_time
        tokens_generated = len(outputs[0].outputs[0].token_ids)
        self._record_benchmark(tokens_generated, elapsed)
        
        logger.info(f"[vLLM Backend] Generated {tokens_generated} tokens in {elapsed:.2f}s "
                   f"({tokens_generated/elapsed:.1f} tok/s)")
        
        return response
    
    def get_backend_info(self) -> Dict[str, Any]:
        return {
            'name': 'vLLM',
            'type': 'vllm',
            'features': ['PagedAttention', 'ContinuousBatching', 'CUDAGraph'],
            'tensor_parallel': self.tensor_parallel_size,
            'gpu_memory_utilization': self.gpu_memory_utilization,
            'model': self.model_name,
            'adapter': self.adapter_path,
        }


# ============================================================================
# AWQ Backend (AutoAWQ Quantization)
# ============================================================================

class AWQBackend(InferenceBackend):
    """
    AutoAWQ backend for efficient 4-bit quantization.
    AWQ (Activation-aware Weight Quantization) often provides better speed
    than BitsAndBytes while maintaining quality.
    
    Requirements:
        pip install autoawq
    
    Note: Requires AWQ-quantized model (e.g., from TheBloke on HuggingFace)
    """
    
    def __init__(self, model_name: str, adapter_path: Optional[str] = None,
                 device: str = 'cuda', **kwargs):
        super().__init__(model_name, adapter_path, device, **kwargs)
        self._check_awq_model()
    
    def _check_awq_model(self):
        """Check if model is AWQ-quantized or needs conversion"""
        # AWQ models typically have 'AWQ' or 'awq' in the name
        if 'awq' not in self.model_name.lower():
            logger.warning(
                f"[AWQ Backend] Model '{self.model_name}' may not be AWQ-quantized.\n"
                "For best results, use an AWQ-quantized model like:\n"
                "  - Qwen/Qwen2-VL-7B-Instruct-AWQ\n"
                "  - TheBloke/Qwen-VL-Chat-AWQ\n"
                "Or quantize your model first with: autoawq quantize"
            )
    
    def load(self) -> None:
        """Load model using AutoAWQ"""
        try:
            from awq import AutoAWQForCausalLM
            from transformers import AutoProcessor, AutoTokenizer
        except ImportError:
            raise ImportError(
                "[AWQ Backend] AutoAWQ not installed. Install with:\n"
                "  pip install autoawq\n"
                "Note: Requires CUDA support."
            )
        
        logger.info(f"[AWQ Backend] Loading model: {self.model_name}")
        
        # Load processor/tokenizer
        try:
            self.processor = AutoProcessor.from_pretrained(self.model_name)
        except Exception:
            # Some AWQ models only have tokenizer
            self.processor = AutoTokenizer.from_pretrained(self.model_name)
            logger.info("[AWQ Backend] Using tokenizer instead of processor")
        
        # Check if model is vision-language
        is_vision_model = "VL" in self.model_name or "vision" in self.model_name.lower()
        
        if is_vision_model:
            logger.warning(
                "[AWQ Backend] Vision-language models have limited AWQ support.\n"
                "Consider using BNB backend for VL models, or find an AWQ-compatible VL model."
            )
        
        # Load AWQ model
        try:
            self.model = AutoAWQForCausalLM.from_quantized(
                self.model_name,
                fuse_layers=True,  # Fuse layers for faster inference
                trust_remote_code=True,
                safetensors=True,
            )
            logger.info("[AWQ Backend] Model loaded with fused layers")
        except Exception as e:
            logger.warning(f"[AWQ Backend] Fused loading failed ({e}), trying standard load")
            self.model = AutoAWQForCausalLM.from_quantized(
                self.model_name,
                fuse_layers=False,
                trust_remote_code=True,
            )
        
        # AWQ + LoRA is experimental
        if self.adapter_path:
            logger.warning(
                "[AWQ Backend] LoRA with AWQ is experimental and may not work.\n"
                "Consider using BNB backend if LoRA is required."
            )
            self._load_lora_adapter()
        
        logger.info("[AWQ Backend] Model loaded successfully")
    
    def _load_lora_adapter(self):
        """Attempt to load LoRA adapter (experimental with AWQ)"""
        try:
            from peft import PeftModel
            
            adapter_path = Path(self.adapter_path)
            if not adapter_path.exists():
                logger.warning(f"[AWQ Backend] Adapter not found: {self.adapter_path}")
                return
            
            logger.info(f"[AWQ Backend] Attempting LoRA load: {self.adapter_path}")
            self.model = PeftModel.from_pretrained(self.model, str(adapter_path))
            self.model.eval()
            logger.info("[AWQ Backend] LoRA adapter loaded (experimental)")
            
        except Exception as e:
            logger.error(f"[AWQ Backend] LoRA loading failed: {e}")
            logger.warning("[AWQ Backend] Continuing without LoRA adapter")
    
    def generate(self, inputs: Dict[str, Any], max_new_tokens: int = None,
                 **generation_kwargs) -> str:
        """Generate response using AWQ-quantized model"""
        # Use config default if not specified
        if max_new_tokens is None:
            max_new_tokens = DEFAULT_BACKEND_MAX_TOKENS
        
        start_time = time.time()
        
        # Move inputs to CUDA
        if self.device == 'cuda':
            inputs = {k: v.cuda() if hasattr(v, 'cuda') else v for k, v in inputs.items()}
        
        # Generate
        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                use_cache=True,
                **generation_kwargs
            )
        
        # Decode
        input_length = inputs['input_ids'].shape[1]
        generated_ids = output_ids[:, input_length:]
        
        # Handle both processor and tokenizer
        if hasattr(self.processor, 'batch_decode'):
            response = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        else:
            response = self.processor.decode(generated_ids[0], skip_special_tokens=True)
        
        # Record benchmark
        elapsed = time.time() - start_time
        tokens_generated = generated_ids.shape[1]
        self._record_benchmark(tokens_generated, elapsed)
        
        logger.info(f"[AWQ Backend] Generated {tokens_generated} tokens in {elapsed:.2f}s "
                   f"({tokens_generated/elapsed:.1f} tok/s)")
        
        return response
    
    def get_backend_info(self) -> Dict[str, Any]:
        return {
            'name': 'AutoAWQ',
            'type': 'awq',
            'quantization': '4-bit AWQ',
            'fused_layers': True,
            'model': self.model_name,
            'adapter': self.adapter_path,
            'note': 'Best with AWQ-pretrained models',
        }


# ============================================================================
# Backend Factory
# ============================================================================

def create_backend(backend_name: str, model_name: str, adapter_path: Optional[str] = None,
                   device: str = 'cuda', **kwargs) -> InferenceBackend:
    """
    Factory function to create the appropriate backend.
    
    Args:
        backend_name: One of 'bnb', 'vllm', 'awq'
        model_name: HuggingFace model ID
        adapter_path: Path to LoRA adapter (optional)
        device: Compute device
        **kwargs: Additional backend-specific arguments
    
    Returns:
        Configured InferenceBackend instance
    """
    backend_name = get_backend(backend_name)
    
    logger.info(f"Creating inference backend: {backend_name}")
    
    if backend_name == 'bnb':
        return BitsAndBytesBackend(
            model_name=model_name,
            adapter_path=adapter_path,
            device=device,
            load_in_4bit=kwargs.get('load_in_4bit', True),
            **kwargs
        )
    
    elif backend_name == 'vllm':
        return VLLMBackend(
            model_name=model_name,
            adapter_path=adapter_path,
            device=device,
            tensor_parallel_size=kwargs.get('tensor_parallel_size', 1),
            gpu_memory_utilization=kwargs.get('gpu_memory_utilization', 0.85),
            **kwargs
        )
    
    elif backend_name == 'awq':
        return AWQBackend(
            model_name=model_name,
            adapter_path=adapter_path,
            device=device,
            **kwargs
        )
    
    else:
        raise ValueError(f"Unknown backend: {backend_name}")


# ============================================================================
# Benchmark Utilities
# ============================================================================

def compare_backends(model_name: str, test_prompt: str, adapter_path: Optional[str] = None,
                     backends_to_test: List[str] = None) -> Dict[str, Any]:
    """
    Run a comparison benchmark across multiple backends.
    
    Args:
        model_name: Model to test
        test_prompt: Test prompt for generation
        adapter_path: Optional LoRA adapter
        backends_to_test: List of backends to test (default: all available)
    
    Returns:
        Comparison results dictionary
    """
    if backends_to_test is None:
        backends_to_test = list(AVAILABLE_BACKENDS.keys())
    
    results = {
        'model': model_name,
        'adapter': adapter_path,
        'backends': {}
    }
    
    for backend_name in backends_to_test:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing backend: {backend_name}")
        logger.info('='*60)
        
        try:
            backend = create_backend(
                backend_name=backend_name,
                model_name=model_name,
                adapter_path=adapter_path
            )
            backend.load()
            
            # Run inference
            # Note: This is simplified - real test would use proper VL inputs
            from transformers import AutoProcessor
            processor = AutoProcessor.from_pretrained(model_name)
            inputs = processor(text=test_prompt, return_tensors="pt")
            
            response = backend.generate(inputs, max_new_tokens=500)
            
            results['backends'][backend_name] = {
                'success': True,
                'info': backend.get_backend_info(),
                'stats': backend.get_benchmark_stats(),
                'response_length': len(response),
            }
            
        except Exception as e:
            logger.error(f"Backend {backend_name} failed: {e}")
            results['backends'][backend_name] = {
                'success': False,
                'error': str(e),
            }
    
    return results


if __name__ == '__main__':
    # Quick test of available backends
    print("Available inference backends:")
    for name, cls in AVAILABLE_BACKENDS.items():
        print(f"  - {name}: {cls}")
    print(f"\nDefault backend: {DEFAULT_BACKEND}")
