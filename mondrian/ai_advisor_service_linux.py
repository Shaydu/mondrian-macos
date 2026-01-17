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
import base64
import io

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
            
            # Enable Flash Attention if available (RTX 3060+ supports it)
            try:
                if self.device == 'cuda':
                    # For PyTorch 2.0+, enable scaled_dot_product_attention with Flash Attention backend
                    self.model.config.attn_implementation = "flash_attention_2"
                    logger.info("Flash Attention 2 enabled for faster inference")
            except (AttributeError, ImportError):
                # Flash Attention not available, fall back to standard attention
                logger.debug("Flash Attention 2 not available, using standard attention")
            
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
    
    def _get_similar_images_from_db(self, advisor_id: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve similar reference images from the dimensional_profiles table.
        This provides RAG context by finding reference images with similar dimensional scores.
        
        Args:
            advisor_id: Advisor to search (e.g., 'ansel')
            top_k: Number of similar images to return
            
        Returns:
            List of similar image records with their dimensional scores
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get reference images for this advisor
            # For now, just get the best-rated images as context
            query = """
                SELECT id, image_path, composition_score, lighting_score, 
                       focus_sharpness_score, color_harmony_score, overall_grade,
                       image_description, image_title, date_taken,
                       subject_isolation_score, depth_perspective_score,
                       visual_balance_score, emotional_impact_score
                FROM dimensional_profiles
                WHERE advisor_id = ?
                  AND composition_score IS NOT NULL
                ORDER BY (
                    composition_score + lighting_score + focus_sharpness_score + 
                    color_harmony_score
                ) / 4.0 DESC
                LIMIT ?
            """
            
            cursor.execute(query, (advisor_id, top_k))
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                logger.warning(f"No reference images found for advisor: {advisor_id}")
                return []
            
            result_images = []
            for row in rows:
                img_dict = dict(row)
                image_path = img_dict.get('image_path')
                
                # Serve image via endpoint instead of base64
                if image_path and os.path.exists(image_path):
                    try:
                        img_filename = os.path.basename(image_path)
                        img_dict['image_url'] = f"/api/reference-image/{img_filename}"
                        img_dict['image_filename'] = img_filename
                        result_images.append(img_dict)
                    except Exception as e:
                        logger.warning(f"Failed to process image {image_path}: {e}")
                        continue
                else:
                    logger.warning(f"Image path not found: {image_path}")
            
            logger.info(f"Retrieved and prepared {len(result_images)} similar reference images for RAG context")
            
            return result_images
            
        except Exception as e:
            logger.error(f"Failed to retrieve similar images: {e}")
            return []
    
    def _get_images_for_weak_dimensions(self, advisor_id: str, weak_dimensions: List[str], max_images: int = 4) -> List[Dict[str, Any]]:
        """
        Retrieve reference images that excel in the user's weakest dimensions.
        This provides targeted improvement guidance by showing mastery in areas needing work.
        
        Args:
            advisor_id: Advisor to search (e.g., 'ansel')
            weak_dimensions: List of dimension names where user needs improvement (e.g., ['composition', 'lighting'])
            max_images: Maximum number of reference images to return (default 4)
            
        Returns:
            List of reference images that excel in the specified dimensions
        """
        try:
            if not weak_dimensions:
                return []
            
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Map dimension names to database columns
            dimension_map = {
                'composition': 'composition_score',
                'lighting': 'lighting_score',
                'focus_sharpness': 'focus_sharpness_score',
                'focus': 'focus_sharpness_score',
                'sharpness': 'focus_sharpness_score',
                'color_harmony': 'color_harmony_score',
                'color': 'color_harmony_score',
                'subject_isolation': 'subject_isolation_score',
                'isolation': 'subject_isolation_score',
                'depth_perspective': 'depth_perspective_score',
                'depth': 'depth_perspective_score',
                'perspective': 'depth_perspective_score',
                'visual_balance': 'visual_balance_score',
                'balance': 'visual_balance_score',
                'emotional_impact': 'emotional_impact_score',
                'emotion': 'emotional_impact_score',
                'impact': 'emotional_impact_score'
            }
            
            # Build query to find images that excel in the weak dimensions
            score_columns = []
            for dim in weak_dimensions[:3]:  # Limit to top 3 weak dimensions
                dim_col = dimension_map.get(dim.lower().replace(' ', '_').replace('&', ''))
                if dim_col:
                    score_columns.append(dim_col)
            
            if not score_columns:
                logger.warning(f"Could not map weak dimensions {weak_dimensions} to database columns")
                return []
            
            # Calculate average score across weak dimensions and get images that excel
            avg_calc = " + ".join(score_columns)
            query = f"""
                SELECT id, image_path, composition_score, lighting_score, 
                       focus_sharpness_score, color_harmony_score,
                       subject_isolation_score, depth_perspective_score,
                       visual_balance_score, emotional_impact_score,
                       overall_grade, image_description, image_title, date_taken
                FROM dimensional_profiles
                WHERE advisor_id = ?
                  AND composition_score IS NOT NULL
                  AND ({" AND ".join([f"{col} >= 8.0" for col in score_columns])})
                ORDER BY ({avg_calc}) / {len(score_columns)} DESC
                LIMIT ?
            """
            
            cursor.execute(query, (advisor_id, max_images))
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                logger.info(f"No reference images found with high scores in dimensions: {weak_dimensions}")
                return []
            
            result_images = [dict(row) for row in rows]
            logger.info(f"Retrieved {len(result_images)} reference images that excel in weak dimensions: {weak_dimensions}")
            
            return result_images
            
        except Exception as e:
            logger.error(f"Failed to retrieve images for weak dimensions: {e}")
            return []
    
    def _get_images_for_weak_dimensions(self, advisor_id: str, weak_dimensions: List[str], max_images: int = 4) -> List[Dict[str, Any]]:
        """
        Retrieve reference images that excel in the user's weakest dimensions.
        This helps provide specific examples showing how to improve in areas where the user needs the most help.
        
        Args:
            advisor_id: Advisor to search (e.g., 'ansel')
            weak_dimensions: List of dimension names where user needs improvement (e.g., ['composition', 'lighting'])
            max_images: Maximum number of reference images to return (default 4)
            
        Returns:
            List of reference images that excel in the specified dimensions
        """
        try:
            if not weak_dimensions:
                return []
            
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Map dimension names to database columns
            dimension_map = {
                'composition': 'composition_score',
                'lighting': 'lighting_score',
                'focus_sharpness': 'focus_sharpness_score',
                'focus': 'focus_sharpness_score',
                'sharpness': 'focus_sharpness_score',
                'color_harmony': 'color_harmony_score',
                'color': 'color_harmony_score',
                'subject_isolation': 'subject_isolation_score',
                'depth_perspective': 'depth_perspective_score',
                'depth': 'depth_perspective_score',
                'perspective': 'depth_perspective_score',
                'visual_balance': 'visual_balance_score',
                'balance': 'visual_balance_score',
                'emotional_impact': 'emotional_impact_score',
                'emotion': 'emotional_impact_score',
                'impact': 'emotional_impact_score'
            }
            
            # Build query to find images that excel in the weak dimensions
            score_columns = []
            for dim in weak_dimensions[:3]:  # Limit to top 3 weak dimensions
                dim_col = dimension_map.get(dim.lower().replace(' ', '_').replace('&', ''))
                if dim_col:
                    score_columns.append(dim_col)
            
            if not score_columns:
                logger.warning(f"Could not map weak dimensions {weak_dimensions} to database columns")
                return []
            
            # Calculate average score across weak dimensions and get images that excel
            avg_calc = " + ".join(score_columns)
            query = f"""
                SELECT id, image_path, composition_score, lighting_score, 
                       focus_sharpness_score, color_harmony_score,
                       subject_isolation_score, depth_perspective_score,
                       visual_balance_score, emotional_impact_score,
                       overall_grade, image_description, image_title, date_taken
                FROM dimensional_profiles
                WHERE advisor_id = ?
                  AND composition_score IS NOT NULL
                  AND ({" AND ".join([f"{col} >= 8.0" for col in score_columns])})
                ORDER BY ({avg_calc}) / {len(score_columns)} DESC
                LIMIT ?
            """
            
            cursor.execute(query, (advisor_id, max_images))
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                logger.info(f"No reference images found with high scores in dimensions: {weak_dimensions}")
                return []
            
            result_images = []
            for row in rows:
                img_dict = dict(row)
                image_path = img_dict.get('image_path')
                
                # Construct image URL if image_path exists
                if image_path and os.path.exists(image_path):
                    try:
                        img_filename = os.path.basename(image_path)
                        img_dict['image_url'] = f"/api/reference-image/{img_filename}"
                        img_dict['image_filename'] = img_filename
                        result_images.append(img_dict)
                    except Exception as e:
                        logger.warning(f"Failed to process image {image_path}: {e}")
                        continue
                else:
                    # If image doesn't exist but we have the dict, still add it (without image_url)
                    result_images.append(img_dict)
            
            logger.info(f"Retrieved {len(result_images)} reference images that excel in weak dimensions: {weak_dimensions}")
            
            return result_images
            
        except Exception as e:
            logger.error(f"Failed to retrieve images for weak dimensions: {e}")
            return []
    
    def _deduplicate_reference_images(self, images: List[Dict[str, Any]], used_paths: set, min_images: int = 1) -> List[Dict[str, Any]]:
        """
        Remove duplicate images based on image_path to ensure each reference is used only once.
        
        Args:
            images: List of reference image dictionaries
            used_paths: Set of already used image paths
            min_images: Minimum number of images to return (will add back best images if needed)
            
        Returns:
            List of unique reference images
        """
        deduplicated = []
        for img in images:
            img_path = img.get('image_path')
            if img_path and img_path not in used_paths:
                used_paths.add(img_path)
                deduplicated.append(img)
                logger.debug(f"Added unique reference: {img.get('image_title', img_path.split('/')[-1])}")
            else:
                logger.debug(f"Skipped duplicate reference: {img.get('image_title', img_path.split('/')[-1] if img_path else 'Unknown')}")
        
        # If we have too few unique images, add back the best duplicates
        if len(deduplicated) < min_images and len(images) > len(deduplicated):
            logger.info(f"Only {len(deduplicated)} unique images found, adding back best duplicates to reach minimum of {min_images}")
            for img in images:
                if len(deduplicated) >= min_images:
                    break
                img_path = img.get('image_path')
                if img_path and img_path in used_paths:
                    # Add it back but mark it as a duplicate in the log
                    deduplicated.append(img)
                    logger.debug(f"Re-added duplicate reference: {img.get('image_title', img_path.split('/')[-1])}")
        
        return deduplicated

    def _get_user_dimensional_profile(self, image_path: str) -> Dict[str, float]:
        """
        Retrieve user's dimensional profile from database if it exists.
        This allows us to do gap analysis on re-analysis or second-pass RAG.
        
        Args:
            image_path: Path to the user's image
            
        Returns:
            Dictionary of dimensional scores, or None if not found
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get most recent profile for this image
            cursor.execute("""
                SELECT composition_score, lighting_score, focus_sharpness_score,
                       color_harmony_score, subject_isolation_score, depth_perspective_score,
                       visual_balance_score, emotional_impact_score
                FROM dimensional_profiles
                WHERE image_path = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (image_path,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # Convert to dictionary
            user_dims = dict(row)
            logger.info(f"Retrieved user dimensional profile for {image_path}")
            return user_dims
            
        except Exception as e:
            logger.error(f"Failed to retrieve user dimensional profile: {e}")
            return None
    
    def _get_images_with_embedding_retrieval(self, advisor_id: str, user_image_path: str, 
                                              weak_dimensions: List[str] = None, 
                                              user_scores: Dict[str, float] = None,
                                              max_images: int = 4) -> List[Dict[str, Any]]:
        """
        Retrieve reference images using CLIP visual embeddings for semantic similarity.
        Falls back to score-based retrieval if embeddings are not available.
        
        Args:
            advisor_id: Advisor to search
            user_image_path: Path to user's image for visual similarity
            weak_dimensions: User's weak dimensions for filtering
            user_scores: User's dimensional scores for gap calculation
            max_images: Maximum number of images to return
            
        Returns:
            List of reference images with base64 encoded thumbnails
        """
        try:
            # Try embedding-based retrieval first
            from mondrian.embedding_retrieval import get_images_hybrid_retrieval, get_similar_images_by_visual_embedding
            
            if user_scores and weak_dimensions:
                # Hybrid retrieval: visual similarity + dimensional gaps
                logger.info("Using hybrid embedding retrieval (visual + gap scores)")
                results = get_images_hybrid_retrieval(
                    DB_PATH, user_image_path, advisor_id,
                    weak_dimensions, user_scores, top_k=max_images
                )
            else:
                # Pure visual similarity
                logger.info("Using visual embedding retrieval")
                results = get_similar_images_by_visual_embedding(
                    DB_PATH, user_image_path, advisor_id,
                    weak_dimensions, top_k=max_images
                )
            
            if not results:
                logger.info("No embedding results, falling back to score-based retrieval")
                return self._get_images_for_weak_dimensions(advisor_id, weak_dimensions, max_images)
            
            # Encode images as URLs instead of base64
            encoded_results = []
            for img in results:
                image_path = img.get('image_path')
                if image_path and os.path.exists(image_path):
                    try:
                        img_filename = os.path.basename(image_path)
                        img['image_url'] = f"/api/reference-image/{img_filename}"
                        img['image_filename'] = img_filename
                        encoded_results.append(img)
                    except Exception as e:
                        logger.warning(f"Failed to process image {image_path}: {e}")
            
            logger.info(f"Retrieved {len(encoded_results)} images via embedding retrieval with URLs")
            return encoded_results
            
        except ImportError as e:
            logger.warning(f"Embedding retrieval not available: {e}")
            logger.info("Falling back to score-based retrieval")
            return self._get_images_for_weak_dimensions(advisor_id, weak_dimensions, max_images)
        except Exception as e:
            logger.error(f"Embedding retrieval failed: {e}")
            return self._get_images_for_weak_dimensions(advisor_id, weak_dimensions, max_images)
    
    def _augment_prompt_with_rag_context(self, prompt: str, advisor_id: str, user_dimensions: Dict[str, float] = None, user_image_path: str = None) -> str:
        """
        Augment the prompt with RAG context from reference images.
        If user_dimensions are provided, finds images that excel in the user's weakest areas.
        Otherwise, uses top-rated reference images.
        
        Args:
            prompt: Original prompt
            advisor_id: Advisor to search for reference images
            user_dimensions: Optional dict of user's dimensional scores for gap analysis
            
        Returns:
            Augmented prompt with RAG context
        """
        
        # Track used images to prevent duplicates
        used_image_paths = set()
        
        # If user dimensions are provided, do gap-based analysis
        if user_dimensions:
            # Find the user's 3 weakest dimensions
            dimension_scores = []
            for dim_name, score in user_dimensions.items():
                if score is not None and dim_name.endswith('_score'):
                    clean_name = dim_name.replace('_score', '')
                    dimension_scores.append((clean_name, score))
            
            # Sort by score ascending (weakest first)
            dimension_scores.sort(key=lambda x: x[1])
            weak_dimensions = [name for name, score in dimension_scores[:3]]
            
            logger.info(f"User's weakest dimensions: {weak_dimensions}")
            
            # Try embedding-based retrieval if user image path is available
            if user_image_path:
                logger.info("Using embedding-based retrieval for visually similar references")
                reference_images = self._get_images_with_embedding_retrieval(
                    advisor_id, user_image_path, weak_dimensions, user_dimensions, max_images=4
                )
            else:
                # Fall back to score-based retrieval
                reference_images = self._get_images_for_weak_dimensions(advisor_id, weak_dimensions, max_images=4)
            
            # Deduplicate images
            reference_images = self._deduplicate_reference_images(reference_images, used_image_paths, min_images=2)
            
            if not reference_images:
                logger.info("No targeted reference images found for weak dimensions - skipping RAG augmentation")
                return prompt, []
            
            # Build targeted RAG context
            rag_context = "\n\n### TARGETED REFERENCE IMAGES FOR IMPROVEMENT:\n"
            rag_context += f"Based on the analysis, here are reference images that excel in the weakest areas ({', '.join(weak_dimensions)}).\n"
            
            # Add note about visual similarity if embedding retrieval was used
            if user_image_path and any('visual_similarity' in img or 'hybrid_score' in img for img in reference_images):
                rag_context += "These images are also visually similar to your photograph, making them excellent study references.\n"
            else:
                rag_context += "Study how these master works demonstrate excellence in the dimensions where improvement is most needed.\n"
            
        else:
            # No user dimensions yet - try visual embedding retrieval first
            if user_image_path:
                logger.info("Using visual embedding retrieval for first-time analysis")
                reference_images = self._get_images_with_embedding_retrieval(
                    advisor_id, user_image_path, weak_dimensions=None, 
                    user_scores=None, max_images=3
                )
            
            # Fall back to score-based if no embedding results
            if not reference_images:
                reference_images = self._get_similar_images_from_db(advisor_id, top_k=3)
            
            # Deduplicate images
            reference_images = self._deduplicate_reference_images(reference_images, used_image_paths, min_images=2)
            
            if not reference_images:
                logger.info("No unique reference images found after deduplication - skipping RAG augmentation")
                return prompt, []
            
            # Build RAG context with reference image names and dimensional comparisons
            rag_context = "\n\n### REFERENCE IMAGES FOR COMPARATIVE ANALYSIS:\n"
            if user_image_path and any('visual_similarity' in img for img in reference_images):
                rag_context += "These master works are visually similar to your photograph and provide dimensional benchmarks.\n"
            else:
                rag_context += "These master works from the advisor's portfolio provide dimensional benchmarks.\n"
        
        # Add reference image details with case study containers
        for i, img in enumerate(reference_images, 1):
            # Use image_title (metadata name) if available, otherwise extract filename
            img_title = img.get('image_title')
            if not img_title:
                img_path = img.get('image_path', '')
                img_title = img_path.split('/')[-1] if img_path else f"Reference {i}"
            
            # Add year if available
            year = img.get('date_taken')
            if year and str(year).strip():
                img_title_with_year = f"{img_title} ({year})"
            else:
                img_title_with_year = img_title
            
            # Get image URL for inline display
            img_filename = os.path.basename(img.get('image_path', ''))
            img_url = f"/api/reference-image/{img_filename}" if img_filename else ""
            
            # Build case study container with inline image
            rag_context += f"""
<div class="case-study-container" style="
    background: #1c1c1e; 
    border-radius: 12px; 
    padding: 20px; 
    margin: 20px 0;
    border-left: 4px solid #30b0c0;
">
    <h3 style="color: #ffffff; margin-top: 0; margin-bottom: 16px; font-size: 18px;">
        Case Study #{i}: {img_title_with_year}
    </h3>
    
    <div style="display: flex; flex-direction: column; gap: 16px;">
"""
            
            # Add image if available
            if img_url:
                rag_context += f"""
        <img src="{img_url}" style="
            width: 100%; 
            max-width: 100%; 
            height: auto; 
            border-radius: 8px; 
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        " alt="{img_title}" />
"""
            
            rag_context += """
        <div style="color: #d1d1d6; line-height: 1.6;">
"""
            
            # Add description
            if img.get('image_description'):
                rag_context += f"<p style='margin: 0 0 12px 0;'><strong>Description:</strong> {img['image_description']}</p>"
            
            # Add dimensional profile with ALL 8 dimensions
            all_dims = ['composition_score', 'lighting_score', 'focus_sharpness_score', 
                       'color_harmony_score', 'subject_isolation_score', 'depth_perspective_score',
                       'visual_balance_score', 'emotional_impact_score']
            
            if any(img.get(k) is not None for k in all_dims):
                rag_context += "<p style='margin: 0;'><strong>Technical Excellence:</strong> "
                scores = []
                
                dim_labels = {
                    'composition_score': 'Composition',
                    'lighting_score': 'Lighting',
                    'focus_sharpness_score': 'Focus & Sharpness',
                    'color_harmony_score': 'Color Harmony',
                    'subject_isolation_score': 'Subject Isolation',
                    'depth_perspective_score': 'Depth & Perspective',
                    'visual_balance_score': 'Visual Balance',
                    'emotional_impact_score': 'Emotional Impact'
                }
                
                for dim_key, dim_label in dim_labels.items():
                    if img.get(dim_key) is not None:
                        scores.append(f"{dim_label} {img[dim_key]}/10")
                
                rag_context += ", ".join(scores)
                if img.get('overall_grade'):
                    rag_context += f" (Grade: {img['overall_grade']})"
                rag_context += "</p>"
            
            rag_context += """
        </div>
    </div>
</div>
"""
            rag_context += "\n"
        
        if user_dimensions:
            rag_context += "\n**CRITICAL - In your dimensional recommendations:** "
            rag_context += "**ALL OUTPUT MUST BE IN ENGLISH ONLY.** "
            rag_context += "You MUST cite these reference images by their exact title when providing improvement guidance. "
            rag_context += "For each dimension's recommendation, reference specific images like: 'Increase contrast by shooting in brighter light like Moon and Half Dome, Yosemite National Park (1960)'. "
            rag_context += "Explain how each reference demonstrates mastery in the specific dimensions where the user has the widest gaps. "
            rag_context += "Calculate dimensional deltas and provide actionable guidance on how to close those gaps.\n"
        else:
            rag_context += "\n**CRITICAL - In your dimensional recommendations:** "
            rag_context += "**ALL OUTPUT MUST BE IN ENGLISH ONLY.** "
            rag_context += "You MUST cite these reference images by their exact title when providing improvement guidance. "
            rag_context += "When analyzing the user's image, compare their dimensional scores to these references. "
            rag_context += "For each dimension's recommendation, cite specific reference images like: 'Improve lighting by studying the zone system technique in Old Faithful Geyser (1944)'. "
            rag_context += "Calculate the delta (difference) for each dimension and cite which reference image demonstrates the best practice for areas needing improvement.\n"
        
        # Augment prompt
        augmented_prompt = f"{prompt}\n{rag_context}"
        logger.info(f"Augmented prompt with RAG context ({len(rag_context)} chars, {len(reference_images)} unique references)")
        
        # Log image titles for debugging duplication
        if reference_images:
            image_titles = [img.get('image_title', img.get('image_path', '').split('/')[-1]) for img in reference_images]
            logger.info(f"Reference images used: {image_titles}")
        
        return augmented_prompt, reference_images
    
    def analyze_image(self, image_path: str, advisor: str = "ansel", 
                     mode: str = "baseline") -> Dict[str, Any]:
        """
        Analyze an image and return structured insights
        
        Args:
            image_path: Path to image file
            advisor: Photography advisor persona (e.g., 'ansel')
            mode: Analysis mode ('baseline', 'rag', 'lora', 'lora+rag', 'rag_lora')
        
        Returns:
            Dictionary with analysis results
        """
        try:
            # Load and validate image
            image = Image.open(image_path).convert('RGB')
            logger.info(f"Loaded image: {image_path} ({image.size})")
            
            # Create analysis prompt
            prompt = self._create_prompt(advisor, mode)
            
            # Apply RAG augmentation if requested
            reference_images = []
            if mode in ('rag', 'rag_lora', 'lora+rag', 'lora_rag'):
                logger.info(f"Augmenting prompt with RAG context for mode={mode}")
                
                # Try to get user's existing dimensional profile for gap-based RAG
                user_dims = self._get_user_dimensional_profile(image_path)
                if user_dims:
                    logger.info("Using gap-based RAG with user's existing dimensional profile and visual embeddings")
                    prompt, reference_images = self._augment_prompt_with_rag_context(
                        prompt, advisor, user_dimensions=user_dims, user_image_path=image_path
                    )
                else:
                    logger.info("No existing user profile found, using standard RAG with visual embeddings")
                    prompt, reference_images = self._augment_prompt_with_rag_context(
                        prompt, advisor, user_image_path=image_path
                    )
            
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
                    max_new_tokens=1200,
                    repetition_penalty=1.0,
                    do_sample=False,
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
            analysis = self._parse_response(response, advisor, mode, prompt, reference_images=reference_images)
            
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
        return """You are a photography analysis assistant. **ALL OUTPUT MUST BE IN ENGLISH ONLY.** Output valid JSON only.
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
    
    def _generate_ios_detailed_html(self, analysis_data: Dict[str, Any], advisor: str, mode: str, reference_images: List[Dict[str, Any]] = None) -> str:
        """Generate iOS-compatible dark theme HTML for detailed analysis"""
        
        if reference_images is None:
            reference_images = []
        
        def format_dimension_name(name: str) -> str:
            """Format dimension names to have proper spacing (e.g., ColorHarmony -> Color Harmony)"""
            import re
            # Insert space before uppercase letters that follow lowercase letters
            formatted = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
            return formatted
        
        # Extract data from the expected JSON structure
        image_description = analysis_data.get('image_description', 'Image analysis')
        dimensions = analysis_data.get('dimensions', [])
        overall_score = analysis_data.get('overall_score', 'N/A')
        technical_notes = analysis_data.get('technical_notes', '')
        
        # Format dimension names
        for dim in dimensions:
            if 'name' in dim and dim['name']:
                dim['name'] = format_dimension_name(dim['name'])
        
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
        
        # Map dimension names to database column names for reference lookup
        dimension_to_column = {
            'composition': 'composition_score',
            'lighting': 'lighting_score',
            'focus': 'focus_sharpness_score',
            'focus & sharpness': 'focus_sharpness_score',
            'focus and sharpness': 'focus_sharpness_score',
            'focus_sharpness': 'focus_sharpness_score',
            'color': 'color_harmony_score',
            'color harmony': 'color_harmony_score',
            'color_harmony': 'color_harmony_score',
            'subject isolation': 'subject_isolation_score',
            'subject_isolation': 'subject_isolation_score',
            'depth': 'depth_perspective_score',
            'depth & perspective': 'depth_perspective_score',
            'depth and perspective': 'depth_perspective_score',
            'depth_perspective': 'depth_perspective_score',
            'visual balance': 'visual_balance_score',
            'visual_balance': 'visual_balance_score',
            'balance': 'visual_balance_score',
            'emotional impact': 'emotional_impact_score',
            'emotional_impact': 'emotional_impact_score',
            'emotion': 'emotional_impact_score',
        }
        
        # Add dimension cards
        for dim in dimensions:
            name = dim.get('name', 'Unknown')
            score = dim.get('score', 0)
            comment = dim.get('comment', 'No analysis available.')
            recommendation = dim.get('recommendation', 'No recommendation available.')
            color, rating = get_rating_style(score)
            
            # Find the best reference image for this dimension based on largest gap
            reference_citation = ""
            if reference_images and len(reference_images) > 0:
                dim_key = name.lower().strip()
                db_column = dimension_to_column.get(dim_key)
                
                if db_column:
                    # Find reference image with highest score in this dimension
                    best_ref = None
                    best_gap = 0
                    
                    for ref in reference_images:
                        ref_score = ref.get(db_column)
                        if ref_score is not None:
                            gap = ref_score - score
                            if gap > best_gap and ref_score >= 8.0:
                                best_gap = gap
                                best_ref = ref
                    
                    # Only show citation if gap is meaningful (>= 2 points)
                    if best_ref and best_gap >= 2:
                        ref_title = best_ref.get('image_title', 'Reference Image')
                        ref_year = best_ref.get('date_taken', '')
                        ref_score_val = best_ref.get(db_column, 0)
                        
                        # Format title with year if available
                        if ref_year and str(ref_year).strip():
                            title_with_year = f"{ref_title} ({ref_year})"
                        else:
                            title_with_year = ref_title
                        
                        # Get image URL - construct it from image_path if not already present
                        ref_image_url = best_ref.get('image_url', '')
                        if not ref_image_url and best_ref.get('image_path'):
                            img_filename = os.path.basename(best_ref.get('image_path', ''))
                            if img_filename:
                                ref_image_url = f"/api/reference-image/{img_filename}"
                        
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
                        
                        reference_citation += f'<div class="case-study-metadata">' + '<br/>'.join(metadata_parts) + '</div>'
                        reference_citation += '</div></div>'
            
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
    
    def _generate_summary_html(self, analysis_data: Dict[str, Any], advisor_id: str = None, reference_images: List[Dict[str, Any]] = None) -> str:
        """Generate iOS-compatible summary HTML with Top 3 recommendations with case study images"""
        
        def format_dimension_name(name: str) -> str:
            """Format dimension names to have proper spacing (e.g., ColorHarmony -> Color Harmony)"""
            import re
            # Insert space before uppercase letters that follow lowercase letters
            formatted = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
            return formatted
        
        dimensions = analysis_data.get('dimensions', [])
        
        # Format dimension names
        for dim in dimensions:
            if 'name' in dim and dim['name']:
                dim['name'] = format_dimension_name(dim['name'])
        
        # Sort by score ascending to get lowest/weakest areas first
        sorted_dims = sorted(dimensions, key=lambda d: d.get('score', 10))[:3]
        
        # Map dimension names to database columns
        dimension_to_column = {
            'composition': 'composition_score',
            'lighting': 'lighting_score',
            'focus & sharpness': 'focus_sharpness_score',
            'focus': 'focus_sharpness_score',
            'focus sharpness': 'focus_sharpness_score',
            'color harmony': 'color_harmony_score',
            'color': 'color_harmony_score',
            'subject isolation': 'subject_isolation_score',
            'depth & perspective': 'depth_perspective_score',
            'depth perspective': 'depth_perspective_score',
            'visual balance': 'visual_balance_score',
            'emotional impact': 'emotional_impact_score',
        }
        
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
        .summary-header { margin-bottom: 16px; padding-bottom: 12px; }
        .summary-header h1 { font-size: 24px; font-weight: 600; margin: 0; }
        .recommendations-list { display: flex; flex-direction: column; gap: 12px; }
        .recommendation-item {
            display: flex;
            flex-direction: column;
            padding: 10px;
            background: #1c1c1e;
            border-radius: 6px;
            border-left: 3px solid #30b0c0;
        }
        .rec-header {
            display: flex;
            gap: 12px;
            align-items: flex-start;
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
        .rec-text { font-size: 14px; line-height: 1.4; color: #e0e0e0; margin: 0; }
        .case-study-box {
            margin-top: 8px;
            padding: 8px;
            background: #0d0d0f;
            border-radius: 6px;
            border: 1px solid #424245;
        }
        .case-study-title {
            font-size: 12px;
            font-weight: 600;
            color: #30b0c0;
            margin-bottom: 6px;
        }
        .case-study-image {
            width: 100%;
            height: auto;
            max-height: 120px;
            border-radius: 4px;
            margin-bottom: 6px;
            display: block;
        }
        .case-study-metadata {
            font-size: 11px;
            line-height: 1.3;
            color: #a0a0a6;
        }
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
            
            # Find best reference image for this dimension
            case_study_html = ''
            if reference_images:
                dim_key = name.lower().strip()
                db_column = dimension_to_column.get(dim_key)
                
                if db_column:
                    best_ref = None
                    best_gap = 0
                    
                    for ref in reference_images:
                        ref_score = ref.get(db_column)
                        if ref_score is not None:
                            gap = ref_score - score
                            if gap > best_gap and ref_score >= 8.0:
                                best_gap = gap
                                best_ref = ref
                    
                    if best_ref and best_gap >= 2:
                        ref_title = best_ref.get('image_title', 'Reference Image')
                        ref_year = best_ref.get('date_taken', '')
                        ref_score_val = best_ref.get(db_column, 0)
                        
                        # Format title with year
                        if ref_year and str(ref_year).strip():
                            title_with_year = f"{ref_title} ({ref_year})"
                        else:
                            title_with_year = ref_title
                        
                        # Get image URL from image path
                        ref_image_url = best_ref.get('image_url', '')
                        if not ref_image_url and best_ref.get('image_path'):
                            img_filename = os.path.basename(best_ref.get('image_path', ''))
                            if img_filename:
                                ref_image_url = f"/api/reference-image/{img_filename}"
                        
                        if ref_image_url:
                            case_study_html = f'''<div class="case-study-box">
                <div class="case-study-title">Case Study: {title_with_year}</div>
                <img src="{ref_image_url}" alt="{title_with_year}" class="case-study-image" />
                <div class="case-study-metadata"><strong>Score:</strong> {ref_score_val}/10 in {name}</div>
            </div>'''
            
            html += f'''  <div class="recommendation-item">
    <div class="rec-header">
        <div class="rec-number">{i}</div>
        <div class="rec-content">
            <p class="rec-text"><strong>{name}</strong> ({score}/10): {recommendation}</p>
        </div>
    </div>{case_study_html}
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
    
    def _parse_response(self, response: str, advisor: str, mode: str, prompt: str, reference_images: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Parse model response into structured format with iOS-compatible HTML"""

        import re
        
        if reference_images is None:
            reference_images = []

        # Extract thinking if present (for thinking models like Qwen3-VL-4B-Thinking)
        thinking_text = ""

        # Check for <thinking> tags (Qwen thinking model format)
        thinking_match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
        if thinking_match:
            thinking_text = thinking_match.group(1).strip()
            logger.info(f"✓ Extracted extended thinking ({len(thinking_text)} chars)")
            # Remove thinking tags from response before JSON parsing
            response = re.sub(r'<thinking>.*?</thinking>', '', response, flags=re.DOTALL).strip()

        # Try to extract JSON from response
        analysis_data = {}
        parse_success = False

        # Warn if response is too long (likely runaway generation in LoRA mode)
        if len(response) > 5000:
            logger.warning(f"⚠️  Response is unusually long ({len(response)} chars) - may indicate runaway generation. Truncating...")
            response = response[:5000]

        try:
            # Find JSON in response (handle both raw JSON and markdown-wrapped JSON)
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]

                # Validate JSON isn't too truncated
                if len(json_str) < 100:
                    logger.warning("⚠️  JSON response too short - likely incomplete or malformed")

                analysis_data = json.loads(json_str)
                parse_success = True
                
                # CRITICAL: Check if thinking leaked into image_description
                image_desc = analysis_data.get('image_description', '')
                if any(phrase in image_desc.lower() for phrase in [
                    'okay, let me', 'step by step', 'first,', 'let me analyze', 
                    'i need to', 'the user wants', 'let\'s check', 'wait', 'hold up'
                ]):
                    logger.warning("⚠️  Detected thinking contamination in image_description - this indicates prompt/model issue")
                    # If thinking leaked into description, try to extract actual description after reasoning
                    # or mark as unparseable
                    analysis_data['image_description'] = "Unable to parse response - thinking model contaminated output"
                    analysis_data['contamination_detected'] = True
                
                logger.info(f"✓ Successfully parsed JSON response ({len(json_str)} chars)")
            else:
                logger.warning("No JSON object found in response")
                analysis_data = {
                    "image_description": "Unable to parse response",
                    "dimensions": [],
                    "overall_score": 0,
                    "raw_response": response
                }
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing failed: {e} at position {e.pos}")
            logger.warning(f"   Response length: {len(response)}, Error context: ...{response[max(0,e.pos-50):min(len(response),e.pos+50)]}...")
            analysis_data = {
                "image_description": "Unable to parse response",
                "dimensions": [],
                "overall_score": 0,
                "parse_error": str(e),
                "raw_response": response[:500]  # Keep only first 500 chars of raw response
            }
        
        # Load advisor data from database for bio
        advisor_data = get_advisor_from_db(DB_PATH, advisor)
        
        # Extract weak dimensions from analysis and retrieve targeted reference images
        weak_dimensions = []
        dimensions = analysis_data.get('dimensions', [])
        if dimensions and len(dimensions) > 0:
            # Sort by score (ascending) to find weakest
            sorted_dims = sorted(dimensions, key=lambda d: d.get('score', 10))
            # Get the 3 weakest dimensions
            weak_dimensions = [d.get('name', '').lower().replace(' ', '_') for d in sorted_dims[:3]]
            
            if weak_dimensions:
                logger.info(f"User's weakest dimensions: {weak_dimensions}")
                # Retrieve reference images that excel in these weak areas
                targeted_refs = self._get_images_for_weak_dimensions(advisor, weak_dimensions, max_images=4)
                if targeted_refs:
                    reference_images = targeted_refs
                    logger.info(f"Retrieved {len(reference_images)} targeted reference images for weak dimensions")
        
        # Generate HTML outputs
        analysis_html = self._generate_ios_detailed_html(analysis_data, advisor, mode, reference_images=reference_images)
        summary_html = self._generate_summary_html(analysis_data, advisor_id=advisor, reference_images=reference_images)
        
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
            "adapter": self.adapter_path if self.adapter_path else None,
            "device": self.device,
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,  # System+advisor prompt sent to LLM
            "llm_prompt": prompt,  # For compatibility
            "full_response": response,  # Complete LLM response (with thinking tags if present)
            "llm_thinking": thinking_text,  # Extracted thinking from thinking models (empty if not present)
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
        health_response = {
            "status": "UP",
            "model": advisor.model_name,
            "device": advisor.device,
            "using_gpu": advisor.device == 'cuda',
            "loading": False,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add LoRA adapter info if loaded
        if advisor.adapter_path:
            from pathlib import Path
            adapter_path = Path(advisor.adapter_path)
            health_response["fine_tuned"] = True
            health_response["lora_path"] = str(advisor.adapter_path)
            health_response["adapter_exists"] = adapter_path.exists()
        else:
            health_response["fine_tuned"] = False
            health_response["lora_path"] = None
        
        return jsonify(health_response), 200
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
        mode_str = request.form.get('mode', 'baseline')
        
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


@app.route('/analyze_stream', methods=['POST'])
def analyze_stream():
    """Analyze an image with streaming output (Server-Sent Events)"""
    if not advisor:
        return jsonify({"error": "Service not initialized"}), 503
    
    try:
        from transformers import TextIteratorStreamer
        
        # Get image from request
        if 'image' not in request.files:
            return jsonify({"error": "No image provided"}), 400
        
        image_file = request.files['image']
        
        # Save temporarily
        temp_path = f"/tmp/{image_file.filename}"
        image_file.save(temp_path)
        
        # Get parameters
        advisor_name = request.form.get('advisor', 'ansel')
        mode_str = request.form.get('mode', 'baseline')
        
        logger.info(f"Starting STREAMING analysis with advisor={advisor_name}, mode={mode_str}")
        
        def generate():
            """Generator function for Server-Sent Events"""
            try:
                # Load and validate image
                image = Image.open(temp_path).convert('RGB')
                
                # Create analysis prompt
                prompt = advisor._create_prompt(advisor_name, mode_str)
                
                # Use chat template for proper image token handling
                messages = [
                    {"role": "user", "content": [
                        {"type": "image"},
                        {"type": "text", "text": prompt}
                    ]}
                ]
                
                # Prepare inputs
                text = advisor.processor.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
                
                inputs = advisor.processor(
                    text=text,
                    images=[image],
                    padding=True,
                    return_tensors="pt"
                )
                
                # Move to device
                if advisor.device == 'cuda':
                    inputs = {k: v.cuda() if hasattr(v, 'cuda') else v for k, v in inputs.items()}
                
                # Create streamer
                streamer = TextIteratorStreamer(
                    advisor.processor.tokenizer,
                    skip_special_tokens=True,
                    skip_prompt=True
                )
                
                # Generation parameters
                generation_kwargs = {
                    **inputs,
                    "streamer": streamer,
                    "max_new_tokens": 800,
                    "repetition_penalty": 1.5,
                    "do_sample": True,
                    "temperature": 0.5,
                    "top_p": 0.90,
                    "eos_token_id": advisor.processor.tokenizer.eos_token_id
                }
                
                # Start generation in background thread
                thread = threading.Thread(target=advisor.model.generate, kwargs=generation_kwargs)
                thread.start()
                
                # Send initial event
                yield f"data: {json.dumps({'type': 'start', 'advisor': advisor_name, 'mode': mode_str})}\n\n"
                
                # Stream tokens as they arrive WITH SEPARATION
                full_response = ""
                in_thinking = False
                in_json = False
                thinking_buffer = ""
                json_buffer = ""
                
                for new_text in streamer:
                    full_response += new_text
                    
                    # Detect thinking tags
                    if '<thinking>' in new_text:
                        in_thinking = True
                        yield f"data: {json.dumps({'type': 'thinking_start'})}\n\n"
                        # Remove tag from text
                        new_text = new_text.replace('<thinking>', '')
                    
                    if '</thinking>' in new_text:
                        in_thinking = False
                        yield f"data: {json.dumps({'type': 'thinking_end', 'full_thinking': thinking_buffer})}\n\n"
                        # Remove tag from text
                        new_text = new_text.replace('</thinking>', '')
                    
                    # Detect JSON start
                    if '{' in new_text and not in_thinking and not in_json:
                        in_json = True
                        yield f"data: {json.dumps({'type': 'json_start'})}\n\n"
                    
                    # Send appropriate event type based on current state
                    if new_text.strip():  # Only send non-empty tokens
                        if in_thinking:
                            thinking_buffer += new_text
                            yield f"data: {json.dumps({'type': 'thinking_token', 'text': new_text})}\n\n"
                        elif in_json:
                            json_buffer += new_text
                            yield f"data: {json.dumps({'type': 'json_token', 'text': new_text})}\n\n"
                        else:
                            # Unknown content (shouldn't happen with proper format)
                            yield f"data: {json.dumps({'type': 'token', 'text': new_text})}\n\n"
                
                thread.join()
                
                # Parse final response
                result = advisor._parse_response(full_response, advisor_name, mode_str, prompt)
                
                # Send complete event with parsed data
                yield f"data: {json.dumps({'type': 'complete', 'result': result})}\n\n"
                
                # Clean up
                Path(temp_path).unlink()
                
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        
        # Return SSE response
        return app.response_class(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        logger.error(f"Stream setup error: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


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
    parser.add_argument('--adapter', default='adapters/ansel_qwen3_4b_v2/epoch_20', help='Path to LoRA adapter')
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
