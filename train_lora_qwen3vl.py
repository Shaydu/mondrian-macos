#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LoRA Fine-tuning Script for Qwen3-VL-4B
Adapts the model for photography analysis with advisor-specific feedback

Usage:
    python train_lora_qwen3vl.py \
        --base_model Qwen/Qwen3-VL-4B-Instruct \
        --data_dir ./training_data \
        --output_dir ./models/qwen3-vl-4b-lora \
        --epochs 3 \
        --batch_size 2 \
        --learning_rate 2e-4
"""

import os
import json
import argparse
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoModelForCausalLM,
    AutoProcessor,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VisionLanguageDataset(Dataset):
    """Dataset for vision-language fine-tuning"""
    
    def __init__(self, data_path, processor, max_length=2048):
        self.processor = processor
        self.max_length = max_length
        
        # Load training data
        if os.path.isdir(data_path):
            # Load from directory of JSON files
            self.data = []
            for filename in os.listdir(data_path):
                if filename.endswith('.json'):
                    with open(os.path.join(data_path, filename), 'r') as f:
                        item = json.load(f)
                        if self._validate_item(item):
                            self.data.append(item)
        elif os.path.isfile(data_path):
            # Load from single JSON file
            with open(data_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.data = [item for item in data if self._validate_item(item)]
                else:
                    self.data = [data] if self._validate_item(data) else []
        else:
            raise ValueError(f"Data path not found: {data_path}")
        
        logger.info(f"Loaded {len(self.data)} training examples")
    
    def _validate_item(self, item):
        """Validate that item has required fields"""
        required = ['image_path', 'prompt', 'response']
        return all(key in item for key in required) and os.path.exists(item['image_path'])
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        
        # Load image
        from PIL import Image
        image = Image.open(item['image_path']).convert('RGB')
        
        # Format prompt and response
        prompt = item['prompt']
        response = item['response']
        
        # Create conversation format
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
        
        # Process with processor
        text = self.processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False
        )
        
        # Tokenize
        inputs = self.processor(
            text=[text],
            images=[image],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_length
        )
        
        # Move to device
        inputs = {k: v.squeeze(0) for k, v in inputs.items()}
        
        # Create labels (same as input_ids for causal LM)
        inputs['labels'] = inputs['input_ids'].clone()
        
        return inputs


def load_model_and_processor(model_name, use_4bit=True, device_map="auto"):
    """Load model with quantization if needed"""
    logger.info(f"Loading model: {model_name}")
    
    # Configure quantization for memory efficiency
    if use_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    else:
        bnb_config = None
    
    # Load processor
    processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
    
    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map=device_map,
        trust_remote_code=True,
        torch_dtype=torch.float16 if use_4bit else torch.float32
    )
    
    # Prepare for k-bit training
    if use_4bit:
        model = prepare_model_for_kbit_training(model)
    
    logger.info("Model loaded successfully")
    return model, processor


def setup_lora(model, r=16, lora_alpha=32, lora_dropout=0.05, target_modules=None):
    """Configure and apply LoRA"""
    if target_modules is None:
        # Default target modules for Qwen3-VL
        target_modules = [
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj"
        ]
    
    lora_config = LoraConfig(
        r=r,
        lora_alpha=lora_alpha,
        target_modules=target_modules,
        lora_dropout=lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    return model


def train(
    base_model,
    data_dir,
    output_dir,
    epochs=3,
    batch_size=2,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    warmup_steps=100,
    save_steps=500,
    logging_steps=50,
    use_4bit=True,
    lora_r=16,
    lora_alpha=32,
    lora_dropout=0.05,
):
    """Main training function"""
    
    # Load model and processor
    model, processor = load_model_and_processor(base_model, use_4bit=use_4bit)
    
    # Setup LoRA
    model = setup_lora(
        model,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout
    )
    
    # Load dataset
    dataset = VisionLanguageDataset(data_dir, processor)
    
    # Split dataset (80/20 train/val)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(
        dataset, [train_size, val_size]
    )
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        learning_rate=learning_rate,
        warmup_steps=warmup_steps,
        logging_steps=logging_steps,
        save_steps=save_steps,
        evaluation_strategy="steps",
        eval_steps=save_steps,
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="loss",
        greater_is_better=False,
        fp16=True,
        bf16=False,
        dataloader_pin_memory=False,
        report_to="tensorboard",
        logging_dir=f"{output_dir}/logs",
    )
    
    # Create trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
    )
    
    # Train
    logger.info("Starting training...")
    trainer.train()
    
    # Save final model
    logger.info(f"Saving model to {output_dir}")
    trainer.save_model()
    processor.save_pretrained(output_dir)
    
    # Save training config
    config = {
        "base_model": base_model,
        "lora_r": lora_r,
        "lora_alpha": lora_alpha,
        "lora_dropout": lora_dropout,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
    }
    with open(os.path.join(output_dir, "training_config.json"), "w") as f:
        json.dump(config, f, indent=2)
    
    logger.info("Training completed!")


def main():
    parser = argparse.ArgumentParser(description="LoRA Fine-tuning for Qwen3-VL-4B")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen3-VL-4B-Instruct",
                        help="Base model name or path")
    parser.add_argument("--data_dir", type=str, required=True,
                        help="Directory or file containing training data (JSON format)")
    parser.add_argument("--output_dir", type=str, default="./models/qwen3-vl-4b-lora",
                        help="Output directory for fine-tuned model")
    parser.add_argument("--epochs", type=int, default=3,
                        help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=2,
                        help="Batch size per device")
    parser.add_argument("--gradient_accumulation_steps", type=int, default=4,
                        help="Gradient accumulation steps")
    parser.add_argument("--learning_rate", type=float, default=2e-4,
                        help="Learning rate")
    parser.add_argument("--warmup_steps", type=int, default=100,
                        help="Warmup steps")
    parser.add_argument("--save_steps", type=int, default=500,
                        help="Save checkpoint every N steps")
    parser.add_argument("--logging_steps", type=int, default=50,
                        help="Log every N steps")
    parser.add_argument("--lora_r", type=int, default=16,
                        help="LoRA rank")
    parser.add_argument("--lora_alpha", type=int, default=32,
                        help="LoRA alpha")
    parser.add_argument("--lora_dropout", type=float, default=0.05,
                        help="LoRA dropout")
    parser.add_argument("--no_4bit", action="store_true",
                        help="Disable 4-bit quantization (requires more memory)")
    
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Train
    train(
        base_model=args.base_model,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        warmup_steps=args.warmup_steps,
        save_steps=args.save_steps,
        logging_steps=args.logging_steps,
        use_4bit=not args.no_4bit,
        lora_r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
    )


if __name__ == "__main__":
    main()


