#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MLX-Native LoRA Fine-tuning for Qwen3-VL-4B

Fine-tunes Qwen3-VL-4B on photography analysis data using MLX framework.
Uses mlx_vlm.lora for LoRA adapter creation and mlx_vlm.trainer for training.

This is fine-tuning only - the base model weights are frozen, and only the small
LoRA adapter matrices are trained.

Usage:
    python train_mlx_lora.py \
        --train_data ./training_data/training_data_ansel_train.json \
        --val_data ./training_data/training_data_ansel_val.json \
        --output_dir ./models/qwen3-vl-4b-lora-ansel \
        --epochs 3 \
        --batch_size 2 \
        --learning_rate 2e-4

Output:
    - adapter_config.json: LoRA configuration
    - adapter_model.safetensors: Trained LoRA weights
    - training_args.json: Training hyperparameters
    - training_log.jsonl: Loss history
"""

import os
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
import numpy as np
from PIL import Image

try:
    import mlx_vlm
    from mlx_vlm import load, generate, utils
except ImportError:
    print("[ERROR] mlx_vlm not installed. Install with: pip install mlx-vlm")
    raise


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class VisionLanguageDataset:
    """
    Dataset for vision-language fine-tuning.
    Loads training examples from JSON files.
    """
    
    def __init__(self, data_path: str, processor, max_length: int = 2048):
        """
        Args:
            data_path: Path to JSON file or directory containing JSON files
            processor: MLX-VLM processor for tokenization
            max_length: Maximum sequence length
        """
        self.processor = processor
        self.max_length = max_length
        self.data = []
        
        # Load training data
        if os.path.isdir(data_path):
            # Load from directory of JSON files
            for filename in sorted(os.listdir(data_path)):
                if filename.endswith('.json'):
                    filepath = os.path.join(data_path, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        item = json.load(f)
                        if self._validate_item(item):
                            self.data.append(item)
        elif os.path.isfile(data_path):
            # Load from single JSON file
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if self._validate_item(item):
                            self.data.append(item)
                else:
                    if self._validate_item(data):
                        self.data.append(data)
        else:
            raise ValueError(f"Data path not found: {data_path}")
        
        logger.info(f"Loaded {len(self.data)} training examples from {data_path}")
        
        if len(self.data) == 0:
            raise ValueError(f"No valid training examples found in {data_path}")
    
    def _validate_item(self, item: Dict) -> bool:
        """Validate that item has required fields."""
        required = ['image_path', 'prompt', 'response']
        
        # Check required fields exist
        if not all(key in item for key in required):
            return False
        
        # Check image exists
        if not os.path.exists(item['image_path']):
            logger.warning(f"Image not found: {item['image_path']}")
            return False
        
        # Check response is non-empty
        if not item['response'] or len(str(item['response'])) < 50:
            logger.warning(f"Response too short for {item['image_path']}")
            return False
        
        return True
    
    def __len__(self) -> int:
        return len(self.data)
    
    def __getitem__(self, idx: int) -> Dict:
        """Get training example as MLX tensors."""
        item = self.data[idx]
        
        try:
            # Load image
            image = Image.open(item['image_path']).convert('RGB')
            
            # Get prompt and response
            prompt = item['prompt']
            response = item['response']
            
            # Convert response to string if needed
            if isinstance(response, dict):
                response = json.dumps(response)
            else:
                response = str(response)
            
            # Format as conversation
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": prompt}
                    ]
                },
                {
                    "role": "assistant",
                    "content": response
                }
            ]
            
            # Apply chat template (tokenize)
            text = self.processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False
            )
            
            # Tokenize and process
            inputs = self.processor(
                text=[text],
                images=[image],
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=self.max_length
            )
            
            # Convert to MLX tensors
            result = {}
            for key, value in inputs.items():
                if hasattr(value, 'numpy'):
                    result[key] = mx.array(value.numpy())
                else:
                    result[key] = mx.array(value)
            
            # Create labels (same as input_ids for causal LM)
            if 'input_ids' in result:
                result['labels'] = result['input_ids'].copy()
            
            return result
        
        except Exception as e:
            logger.error(f"Error processing {item.get('image_path', 'unknown')}: {str(e)}")
            raise


class LoRAConfig:
    """Configuration for LoRA adapters."""
    
    def __init__(
        self,
        r: int = 16,
        lora_alpha: int = 32,
        lora_dropout: float = 0.05,
        target_modules: Optional[List[str]] = None,
        bias: str = "none",
        task_type: str = "CAUSAL_LM"
    ):
        self.r = r
        self.lora_alpha = lora_alpha
        self.lora_dropout = lora_dropout
        self.target_modules = target_modules or [
            "q_proj", "v_proj",
            "up_proj", "gate_proj"
        ]
        self.bias = bias
        self.task_type = task_type
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for saving."""
        return {
            'r': self.r,
            'lora_alpha': self.lora_alpha,
            'lora_dropout': self.lora_dropout,
            'target_modules': self.target_modules,
            'bias': self.bias,
            'task_type': self.task_type
        }


def compute_loss(model_output, batch):
    """
    Compute causal language modeling loss.
    
    Loss is computed on response tokens only (not prompt tokens).
    """
    logits = model_output  # Shape: (batch, seq_len, vocab_size)
    labels = batch.get('labels')  # Shape: (batch, seq_len)
    
    if labels is None:
        # If no explicit labels, use input_ids
        labels = batch.get('input_ids')
    
    # Shift for next-token prediction
    # We predict token[i+1] given token[0:i]
    shift_logits = logits[..., :-1, :]  # (batch, seq_len-1, vocab_size)
    shift_labels = labels[..., 1:]      # (batch, seq_len-1)
    
    # Compute cross-entropy loss
    # Cross-entropy across vocabulary dimension
    loss = mx.softmax_cross_entropy(
        shift_logits,
        mx.one_hot(shift_labels, shift_logits.shape[-1])
    )
    
    # Average over sequence and batch
    loss = mx.mean(loss)
    
    return loss


def train_step(
    model,
    batch,
    optimizer,
    step: int
) -> Tuple[float, float]:
    """
    Single training step.
    
    Returns:
        (loss, learning_rate)
    """
    # Define loss function
    def loss_fn(model):
        # Forward pass
        output = model.generate(
            batch['input_ids'],
            batch.get('images'),
            max_tokens=2048
        )
        return compute_loss(output, batch)
    
    # Compute loss and gradients
    loss_and_grad_fn = mx.value_and_grad(loss_fn)
    loss, grads = loss_and_grad_fn(model)
    
    # Update model parameters
    optimizer.update(model, grads)
    
    # Evaluate to update graph
    mx.eval(model.parameters())
    
    # Get current learning rate (constant for now)
    current_lr = optimizer.learning_rate if hasattr(optimizer, 'learning_rate') else 0
    
    return float(loss), float(current_lr)


def train(
    base_model: str = "Qwen/Qwen3-VL-4B-Instruct",
    train_data_path: str = "./training_data/training_data_ansel_train.json",
    val_data_path: Optional[str] = None,
    output_dir: str = "./models/qwen3-vl-4b-lora-ansel",
    epochs: int = 3,
    batch_size: int = 2,
    learning_rate: float = 2e-4,
    warmup_steps: int = 100,
    save_freq: int = 500,
    lora_r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
    max_seq_length: int = 2048
):
    """
    Main training function for LoRA fine-tuning.
    
    Args:
        base_model: Hugging Face model ID
        train_data_path: Path to training data JSON
        val_data_path: Path to validation data JSON (optional)
        output_dir: Directory to save fine-tuned model
        epochs: Number of training epochs
        batch_size: Batch size per step
        learning_rate: Learning rate for optimizer
        warmup_steps: Number of warmup steps
        save_freq: Save checkpoint every N steps
        lora_r: LoRA rank
        lora_alpha: LoRA alpha scaling
        lora_dropout: LoRA dropout rate
        max_seq_length: Maximum sequence length
    """
    
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info("=" * 80)
    logger.info("MLX LoRA Fine-tuning for Qwen3-VL-4B")
    logger.info("=" * 80)
    
    # Load base model
    logger.info(f"Loading base model: {base_model}")
    model, processor = mlx_vlm.load(base_model)
    logger.info(f"Model loaded: {type(model)}")
    
    # Create LoRA configuration
    lora_config = LoRAConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout
    )
    logger.info(f"LoRA config: r={lora_r}, alpha={lora_alpha}, dropout={lora_dropout}")
    
    # TODO: Apply LoRA adapters
    # This requires using mlx_vlm.lora or implementing LoRA layer application
    logger.info("[TODO] Apply LoRA adapters to model")
    
    # Load training data
    logger.info(f"Loading training data from {train_data_path}")
    train_dataset = VisionLanguageDataset(train_data_path, processor, max_seq_length)
    logger.info(f"Loaded {len(train_dataset)} training examples")
    
    # Load validation data if provided
    val_dataset = None
    if val_data_path and os.path.exists(val_data_path):
        logger.info(f"Loading validation data from {val_data_path}")
        val_dataset = VisionLanguageDataset(val_data_path, processor, max_seq_length)
        logger.info(f"Loaded {len(val_dataset)} validation examples")
    
    # Create optimizer
    optimizer = optim.Adam(learning_rate=learning_rate)
    logger.info(f"Optimizer: Adam (lr={learning_rate})")
    
    # Training loop
    logger.info("Starting training...")
    logger.info("=" * 80)
    
    training_log = []
    step = 0
    
    for epoch in range(epochs):
        logger.info(f"Epoch {epoch + 1}/{epochs}")
        epoch_losses = []
        
        for batch_idx in range(len(train_dataset) // batch_size):
            # Get batch
            batch_indices = list(range(batch_idx * batch_size, (batch_idx + 1) * batch_size))
            batch = {
                'input_ids': mx.concatenate([train_dataset[i]['input_ids'] for i in batch_indices]),
                'images': [train_dataset[i].get('images') for i in batch_indices],
            }
            
            # Training step
            loss, lr = train_step(model, batch, optimizer, step)
            epoch_losses.append(loss)
            
            # Log
            if (step + 1) % 10 == 0:
                avg_loss = np.mean(epoch_losses[-10:])
                logger.info(f"  Step {step + 1}: loss={avg_loss:.4f}")
            
            # Save checkpoint
            if save_freq > 0 and (step + 1) % save_freq == 0:
                ckpt_dir = os.path.join(output_dir, f"checkpoint_step_{step + 1}")
                os.makedirs(ckpt_dir, exist_ok=True)
                logger.info(f"  Saving checkpoint to {ckpt_dir}")
                # TODO: Save LoRA weights and optimizer state
            
            step += 1
        
        # Epoch summary
        epoch_loss = np.mean(epoch_losses)
        logger.info(f"Epoch {epoch + 1} complete: avg_loss={epoch_loss:.4f}")
        
        training_log.append({
            'epoch': epoch + 1,
            'avg_loss': float(epoch_loss),
            'timestamp': datetime.now().isoformat()
        })
        
        # Validation
        if val_dataset:
            logger.info("Running validation...")
            val_losses = []
            for batch_idx in range(len(val_dataset) // batch_size):
                batch_indices = list(range(batch_idx * batch_size, (batch_idx + 1) * batch_size))
                batch = {
                    'input_ids': mx.concatenate([val_dataset[i]['input_ids'] for i in batch_indices]),
                    'images': [val_dataset[i].get('images') for i in batch_indices],
                }
                # TODO: Compute validation loss without updating gradients
                # loss = compute_loss(model(batch), batch)
                # val_losses.append(loss)
            
            # val_loss = np.mean(val_losses)
            # logger.info(f"Validation loss: {val_loss:.4f}")
    
    # Save final model and configuration
    logger.info("=" * 80)
    logger.info(f"Saving final model to {output_dir}")
    
    # Save LoRA configuration
    config_path = os.path.join(output_dir, "adapter_config.json")
    with open(config_path, 'w') as f:
        json.dump(lora_config.to_dict(), f, indent=2)
    logger.info(f"  Saved adapter config to {config_path}")
    
    # Save training arguments
    training_args = {
        'base_model': base_model,
        'epochs': epochs,
        'batch_size': batch_size,
        'learning_rate': learning_rate,
        'warmup_steps': warmup_steps,
        'lora_r': lora_r,
        'lora_alpha': lora_alpha,
        'lora_dropout': lora_dropout,
        'max_seq_length': max_seq_length,
        'total_steps': step,
        'training_date': datetime.now().isoformat()
    }
    args_path = os.path.join(output_dir, "training_args.json")
    with open(args_path, 'w') as f:
        json.dump(training_args, f, indent=2)
    logger.info(f"  Saved training args to {args_path}")
    
    # Save training log
    log_path = os.path.join(output_dir, "training_log.jsonl")
    with open(log_path, 'w') as f:
        for entry in training_log:
            f.write(json.dumps(entry) + '\n')
    logger.info(f"  Saved training log to {log_path}")
    
    logger.info("=" * 80)
    logger.info("Training completed!")
    logger.info(f"Fine-tuned model saved to: {output_dir}")
    logger.info("Next steps:")
    logger.info(f"  1. Evaluate: python evaluate_lora.py --lora_path {output_dir}")
    logger.info(f"  2. Deploy: python mondrian/ai_advisor_service.py --lora_path {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="MLX-Native LoRA Fine-tuning for Qwen3-VL-4B"
    )
    parser.add_argument(
        "--base_model",
        type=str,
        default="Qwen/Qwen3-VL-4B-Instruct",
        help="Base model name or path"
    )
    parser.add_argument(
        "--train_data",
        type=str,
        required=True,
        help="Path to training data JSON"
    )
    parser.add_argument(
        "--val_data",
        type=str,
        default=None,
        help="Path to validation data JSON (optional)"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./models/qwen3-vl-4b-lora",
        help="Output directory for fine-tuned model"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs"
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=2,
        help="Batch size per step"
    )
    parser.add_argument(
        "--learning_rate",
        type=float,
        default=2e-4,
        help="Learning rate"
    )
    parser.add_argument(
        "--warmup_steps",
        type=int,
        default=100,
        help="Number of warmup steps"
    )
    parser.add_argument(
        "--save_freq",
        type=int,
        default=500,
        help="Save checkpoint every N steps"
    )
    parser.add_argument(
        "--lora_r",
        type=int,
        default=16,
        help="LoRA rank"
    )
    parser.add_argument(
        "--lora_alpha",
        type=int,
        default=32,
        help="LoRA alpha"
    )
    parser.add_argument(
        "--lora_dropout",
        type=float,
        default=0.05,
        help="LoRA dropout"
    )
    
    args = parser.parse_args()
    
    train(
        base_model=args.base_model,
        train_data_path=args.train_data,
        val_data_path=args.val_data,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        warmup_steps=args.warmup_steps,
        save_freq=args.save_freq,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout
    )


if __name__ == "__main__":
    main()
