#!/usr/bin/env python3
"""
Train LoRA adapter for a photography advisor using MLX-VLM.

This script loads the prepared dataset and fine-tunes a LoRA adapter
on top of the Qwen3-VL vision-language model.

Usage:
    python training/train_lora.py --advisor ansel
    python training/train_lora.py --advisor ansel --epochs 10 --lr 1e-4
    python training/train_lora.py --advisor ansel --model mlx-community/Qwen3-VL-8B-Instruct-4bit
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import config for default model path
from mondrian.config import DEFAULT_MODEL_PATH

# Default hyperparameters optimized for small datasets (< 20 images)
DEFAULT_CONFIG = {
    "model_path": DEFAULT_MODEL_PATH,  # Uses Qwen3-VL-8B by default
    "rank": 8,           # Low rank for small dataset
    "alpha": 0.1,        # Scaling factor
    "dropout": 0.1,      # Higher dropout to prevent overfitting
    "learning_rate": 5e-5,
    "epochs": 5,
    "batch_size": 1,     # Small batch for memory efficiency
    "save_after_epoch": True
}


def train_lora(
    advisor_id: str,
    dataset_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    model_path: str = DEFAULT_CONFIG["model_path"],
    rank: int = DEFAULT_CONFIG["rank"],
    alpha: float = DEFAULT_CONFIG["alpha"],
    dropout: float = DEFAULT_CONFIG["dropout"],
    learning_rate: float = DEFAULT_CONFIG["learning_rate"],
    epochs: int = DEFAULT_CONFIG["epochs"],
    batch_size: int = DEFAULT_CONFIG["batch_size"],
    dry_run: bool = False,
    resume_from: Optional[Path] = None
):
    """
    Train a LoRA adapter for the specified advisor.

    Args:
        advisor_id: Advisor identifier (e.g., 'ansel')
        dataset_path: Path to training dataset
        output_path: Where to save the adapter
        model_path: HuggingFace model path or local path
        rank: LoRA rank (lower = fewer parameters, less overfitting)
        alpha: LoRA alpha scaling factor
        dropout: Dropout rate for regularization
        learning_rate: Learning rate
        epochs: Number of training epochs
        batch_size: Batch size (1 recommended for small datasets)
        dry_run: If True, validate setup without training
        resume_from: Path to existing adapter to resume training from
    """
    # Set default paths - use combined dataset (images + text) by default
    if dataset_path is None:
        dataset_path = PROJECT_ROOT / "training" / "datasets" / f"{advisor_id}_combined_train.jsonl"
        # Fall back to image-only dataset if combined doesn't exist
        if not dataset_path.exists():
            dataset_path = PROJECT_ROOT / "training" / "datasets" / f"{advisor_id}_train.jsonl"

    if output_path is None:
        output_path = PROJECT_ROOT / "adapters" / advisor_id

    print("=" * 60)
    print(f"LoRA Training Configuration")
    print("=" * 60)
    print(f"Advisor:        {advisor_id}")
    print(f"Dataset:        {dataset_path}")
    print(f"Output:         {output_path}")
    print(f"Model:          {model_path}")
    print(f"Rank:           {rank}")
    print(f"Alpha:          {alpha}")
    print(f"Dropout:        {dropout}")
    print(f"Learning Rate:  {learning_rate}")
    print(f"Epochs:         {epochs}")
    print(f"Batch Size:     {batch_size}")
    print(f"Resume From:    {resume_from or 'None (fresh start)'}")
    print("=" * 60)

    # Validate dataset exists
    if not dataset_path.exists():
        print(f"\nError: Dataset not found at {dataset_path}")
        print("Run prepare_dataset.py first:")
        print(f"  python training/prepare_dataset.py --advisor {advisor_id}")
        sys.exit(1)

    # Count training examples
    with open(dataset_path) as f:
        num_examples = sum(1 for _ in f)
    print(f"\nTraining examples: {num_examples}")

    if num_examples < 5:
        print("Warning: Very few training examples. Consider data augmentation.")

    if dry_run:
        print("\n[DRY RUN] Would train with above configuration.")
        print("Run without --dry-run to start training.")
        return

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Import MLX-VLM components
    try:
        import mlx.core as mx
        import mlx.nn as nn
        import mlx.optimizers as optim
        from mlx_vlm import load
        from mlx_vlm.trainer.trainer import save_adapter
        from mlx_vlm.trainer.utils import get_peft_model
    except ImportError as e:
        print(f"\nError: Required packages not installed: {e}")
        print("Install with:")
        print("  pip install mlx mlx-vlm")
        sys.exit(1)

    print("\nLoading base model...")
    model, processor = load(model_path)

    print("Applying LoRA layers...")
    # Target the attention projection layers in the language model
    # These are the standard layers for LoRA fine-tuning on transformer models
    linear_layers = ["q_proj", "v_proj", "k_proj", "o_proj"]

    model = get_peft_model(
        model,
        linear_layers=linear_layers,
        rank=rank,
        alpha=alpha,
        dropout=dropout,
        verbose=True
    )

    # Load existing adapter weights if resuming
    if resume_from is not None:
        adapter_file = resume_from / "adapters.safetensors"
        if adapter_file.exists():
            print(f"\nLoading existing adapter from {adapter_file}...")
            from mlx_vlm.trainer.trainer import load_adapter
            model = load_adapter(model, str(adapter_file))
            print("Adapter weights loaded successfully!")
        else:
            print(f"\nWarning: No adapter found at {adapter_file}, starting fresh.")

    print("Loading dataset...")
    from PIL import Image
    from mlx_vlm.utils import prepare_inputs

    def convert_message_format(messages):
        """Convert <image> placeholder to structured content format for Qwen3-VL."""
        converted = []
        for msg in messages:
            content = msg["content"]
            # Check if this message contains an image placeholder
            if "<image>" in content:
                # Replace <image> with structured content format
                text_content = content.replace("<image>", "").strip()
                converted.append({
                    "role": msg["role"],
                    "content": [
                        {"type": "image"},
                        {"type": "text", "text": text_content}
                    ]
                })
            else:
                converted.append(msg)
        return converted

    def load_training_data(path: Path):
        """Load dataset directly as list of dicts for manual iteration.

        Supports both image+text and text-only examples.
        """
        examples = []
        with open(path) as f:
            for line in f:
                record = json.loads(line)
                messages = convert_message_format(record["messages"])

                # Check if this is an image example or text-only
                if "image_path" in record and record["image_path"]:
                    img = Image.open(record["image_path"]).convert("RGB")
                    examples.append({
                        "messages": messages,
                        "image": img,
                        "has_image": True
                    })
                else:
                    # Text-only example
                    examples.append({
                        "messages": messages,
                        "image": None,
                        "has_image": False
                    })
        return examples

    training_data = load_training_data(dataset_path)

    # Get config dict for image token index
    config_dict = model.config.to_dict() if hasattr(model.config, 'to_dict') else vars(model.config)
    image_token_index = config_dict.get("image_token_index", config_dict.get("image_token_id"))

    def prepare_batch(item):
        """Prepare a single training example.

        Handles both image+text and text-only examples.
        """
        messages = item["messages"]
        has_image = item.get("has_image", False)
        image = item.get("image")

        # Apply chat template to get the prompt
        prompt = processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False
        )

        if has_image and image is not None:
            # Image + text example
            inputs = prepare_inputs(
                processor=processor,
                images=[image],
                audio=None,
                prompts=[prompt],
                image_token_index=image_token_index,
            )
            return {
                "input_ids": inputs["input_ids"],
                "pixel_values": inputs["pixel_values"],
                "attention_mask": inputs["attention_mask"],
                "has_image": True,
                **{k: v for k, v in inputs.items()
                   if k not in ["input_ids", "pixel_values", "attention_mask"]}
            }
        else:
            # Text-only example - use tokenizer directly
            tokenized = processor.tokenizer(
                prompt,
                return_tensors="np",
                padding=True,
                truncation=True,
                max_length=2048
            )
            return {
                "input_ids": mx.array(tokenized["input_ids"]),
                "attention_mask": mx.array(tokenized["attention_mask"]),
                "pixel_values": None,
                "has_image": False
            }

    print("Setting up optimizer...")
    optimizer = optim.AdamW(learning_rate=learning_rate)

    # Custom loss function for Qwen3-VL (fixes attention_mask shape mismatch)
    def loss_fn(model, batch):
        input_ids = batch["input_ids"]
        pixel_values = batch["pixel_values"]
        attention_mask = batch["attention_mask"]

        # Get labels (shifted by 1)
        labels = input_ids[:, 1:]

        # Slice input_ids AND attention_mask together to avoid shape mismatch
        input_ids_sliced = input_ids[:, :-1]
        attention_mask_sliced = attention_mask[:, :-1]

        # Get extra kwargs (like image_grid_thw)
        kwargs = {
            k: v for k, v in batch.items()
            if k not in ["input_ids", "pixel_values", "attention_mask"]
        }

        # Forward pass with properly sliced mask
        outputs = model(input_ids_sliced, pixel_values, mask=attention_mask_sliced, **kwargs)
        logits = outputs.logits.astype(mx.float32)

        # Compute cross-entropy loss
        vocab_size = logits.shape[-1]
        logits_flat = logits.reshape(-1, vocab_size)
        labels_flat = labels.reshape(-1)

        # Create mask for valid positions
        mask = (labels_flat != -100).astype(mx.float32)

        # Cross entropy (compute log_softmax manually: log(softmax(x)) = x - logsumexp(x))
        log_probs = logits_flat - mx.logsumexp(logits_flat, axis=-1, keepdims=True)
        target_log_probs = mx.take_along_axis(
            log_probs, labels_flat[:, None], axis=-1
        ).squeeze(-1)

        loss = -mx.sum(target_log_probs * mask) / mx.maximum(mx.sum(mask), 1)
        return loss

    print("\n" + "=" * 60)
    print("Starting training...")
    print("=" * 60)

    # Training loop
    num_examples = len(training_data)
    for epoch in range(epochs):
        print(f"\nEpoch {epoch + 1}/{epochs}")
        total_loss = 0.0

        for i, item in enumerate(training_data):
            batch = prepare_batch(item)

            # Create loss function that captures the batch
            def batch_loss_fn(model):
                return loss_fn(model, batch)

            # Create value_and_grad for this batch and compute
            loss_and_grad_fn = nn.value_and_grad(model, batch_loss_fn)
            loss, grads = loss_and_grad_fn(model)

            # Clip gradients
            grads, _ = optim.clip_grad_norm(grads, max_norm=1.0)

            # Update model
            optimizer.update(model, grads)
            mx.eval(model.parameters(), optimizer.state)

            total_loss += loss.item()

            if (i + 1) % 5 == 0 or i == num_examples - 1:
                avg_loss = total_loss / (i + 1)
                print(f"  Step {i + 1}/{num_examples}, Loss: {loss.item():.4f}, Avg: {avg_loss:.4f}")

        # Evaluate after each epoch
        mx.eval(model.parameters())

        # Save checkpoint after each epoch
        epoch_path = output_path / f"epoch_{epoch + 1}"
        epoch_path.mkdir(exist_ok=True)
        save_adapter(model, str(epoch_path / "adapters.safetensors"))
        print(f"  Saved checkpoint to {epoch_path}")

    # Save final adapter
    print("\n" + "=" * 60)
    print("Saving final adapter...")
    save_adapter(model, str(output_path / "adapters.safetensors"))

    # Save training config
    config_data = {
        "advisor_id": advisor_id,
        "model_path": model_path,
        "rank": rank,
        "alpha": alpha,
        "dropout": dropout,
        "learning_rate": learning_rate,
        "epochs": epochs,
        "batch_size": batch_size,
        "num_examples": num_examples
    }
    with open(output_path / "training_config.json", "w") as f:
        json.dump(config_data, f, indent=2)

    print(f"\nTraining complete!")
    print(f"Adapter saved to: {output_path}")
    print(f"\nTo use this adapter:")
    print(f"  export ANALYSIS_MODE=lora")
    print(f"  # Or set mode=lora in API request")


def main():
    parser = argparse.ArgumentParser(
        description="Train LoRA adapter for photography advisor"
    )
    parser.add_argument(
        "--advisor", "-a",
        type=str,
        default="ansel",
        help="Advisor ID to train (default: ansel)"
    )
    parser.add_argument(
        "--dataset", "-d",
        type=str,
        default=None,
        help="Path to training dataset JSONL"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output directory for adapter"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_CONFIG["model_path"],
        help=f"Base model path (default: {DEFAULT_CONFIG['model_path']})"
    )
    parser.add_argument(
        "--rank", "-r",
        type=int,
        default=DEFAULT_CONFIG["rank"],
        help=f"LoRA rank (default: {DEFAULT_CONFIG['rank']})"
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=DEFAULT_CONFIG["alpha"],
        help=f"LoRA alpha (default: {DEFAULT_CONFIG['alpha']})"
    )
    parser.add_argument(
        "--dropout",
        type=float,
        default=DEFAULT_CONFIG["dropout"],
        help=f"LoRA dropout (default: {DEFAULT_CONFIG['dropout']})"
    )
    parser.add_argument(
        "--lr", "--learning-rate",
        type=float,
        default=DEFAULT_CONFIG["learning_rate"],
        help=f"Learning rate (default: {DEFAULT_CONFIG['learning_rate']})"
    )
    parser.add_argument(
        "--epochs", "-e",
        type=int,
        default=DEFAULT_CONFIG["epochs"],
        help=f"Number of epochs (default: {DEFAULT_CONFIG['epochs']})"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=DEFAULT_CONFIG["batch_size"],
        help=f"Batch size (default: {DEFAULT_CONFIG['batch_size']})"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration without training"
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Path to existing adapter directory to resume training from"
    )

    args = parser.parse_args()

    dataset_path = Path(args.dataset) if args.dataset else None
    output_path = Path(args.output) if args.output else None
    resume_from = Path(args.resume) if args.resume else None

    train_lora(
        advisor_id=args.advisor,
        dataset_path=dataset_path,
        output_path=output_path,
        model_path=args.model,
        rank=args.rank,
        alpha=args.alpha,
        dropout=args.dropout,
        learning_rate=args.lr,
        epochs=args.epochs,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        resume_from=resume_from
    )


if __name__ == "__main__":
    main()
