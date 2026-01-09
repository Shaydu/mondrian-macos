#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Investigate MLX-VLM Capabilities
Examines mlx-vlm package to understand LoRA support and training capabilities

This script helps answer:
1. Does mlx-vlm have built-in LoRA support?
2. What training utilities are available?
3. What is the model structure?
4. How can we implement LoRA fine-tuning?
"""

import sys
import os
import inspect
import importlib

def investigate_package(package_name):
    """Investigate a Python package's structure and capabilities"""
    print(f"\n{'='*80}")
    print(f"Investigating: {package_name}")
    print(f"{'='*80}\n")
    
    try:
        module = importlib.import_module(package_name)
        print(f"✓ Successfully imported {package_name}")
        print(f"  Location: {module.__file__ if hasattr(module, '__file__') else 'Built-in'}")
        
        # List all attributes
        print(f"\n📦 Package Contents:")
        attrs = [attr for attr in dir(module) if not attr.startswith('_')]
        for attr in sorted(attrs):
            obj = getattr(module, attr)
            obj_type = type(obj).__name__
            if inspect.ismodule(obj):
                print(f"  📁 {attr} (module)")
            elif inspect.isclass(obj):
                print(f"  🏛️  {attr} (class)")
            elif inspect.isfunction(obj):
                print(f"  ⚙️  {attr} (function)")
            else:
                print(f"  📄 {attr} ({obj_type})")
        
        return module
    except ImportError as e:
        print(f"✗ Failed to import {package_name}: {e}")
        return None
    except Exception as e:
        print(f"✗ Error investigating {package_name}: {e}")
        return None


def examine_function(func, name):
    """Examine a function's signature and docstring"""
    print(f"\n🔍 Function: {name}")
    print(f"   Signature: {inspect.signature(func)}")
    if func.__doc__:
        doc = func.__doc__.strip().split('\n')[0]
        print(f"   Doc: {doc}")
    else:
        print(f"   (No documentation)")


def examine_class(cls, name):
    """Examine a class's methods and attributes"""
    print(f"\n🏛️  Class: {name}")
    if cls.__doc__:
        doc = cls.__doc__.strip().split('\n')[0]
        print(f"   Doc: {doc}")
    
    # List methods
    methods = [m for m in dir(cls) if not m.startswith('_') and callable(getattr(cls, m))]
    if methods:
        print(f"   Methods: {', '.join(methods[:10])}")
        if len(methods) > 10:
            print(f"   ... and {len(methods) - 10} more")


def search_for_lora(module, depth=0, max_depth=2):
    """Recursively search for LoRA-related functionality"""
    if depth > max_depth:
        return []
    
    lora_items = []
    for attr_name in dir(module):
        if attr_name.startswith('_'):
            continue
        
        attr_lower = attr_name.lower()
        if 'lora' in attr_lower or 'adapter' in attr_lower or 'fine' in attr_lower or 'train' in attr_lower:
            try:
                obj = getattr(module, attr_name)
                lora_items.append((attr_name, obj, type(obj).__name__))
            except:
                pass
    
    return lora_items


def main():
    print("="*80)
    print("MLX-VLM Capability Investigation")
    print("="*80)
    
    # Check if mlx-vlm is installed
    try:
        import mlx_vlm
        print("\n✓ mlx-vlm is installed")
    except ImportError:
        print("\n✗ mlx-vlm is not installed")
        print("  Install with: pip install mlx-vlm")
        return
    except Exception as e:
        print(f"\n⚠ mlx-vlm import failed (may be Metal GPU issue): {e}")
        print("  Continuing with limited investigation...")
        # Try to continue without full MLX initialization
    
    # Investigate main package
    mlx_vlm_module = investigate_package("mlx_vlm")
    if not mlx_vlm_module:
        return
    
    # Check for submodules
    print(f"\n{'='*80}")
    print("Checking Submodules")
    print(f"{'='*80}\n")
    
    submodules = [
        "mlx_vlm.models",
        "mlx_vlm.utils",
        "mlx_vlm.prompt_utils",
        "mlx_vlm.training",  # May not exist
        "mlx_vlm.lora",      # May not exist
    ]
    
    for submodule_name in submodules:
        try:
            submodule = importlib.import_module(submodule_name)
            print(f"✓ Found submodule: {submodule_name}")
            
            # Search for LoRA/training related items
            lora_items = search_for_lora(submodule)
            if lora_items:
                print(f"  🎯 Found {len(lora_items)} potentially relevant items:")
                for name, obj, obj_type in lora_items:
                    print(f"     - {name} ({obj_type})")
        except ImportError:
            print(f"✗ Submodule not found: {submodule_name}")
    
    # Examine key functions
    print(f"\n{'='*80}")
    print("Key Functions")
    print(f"{'='*80}\n")
    
    key_functions = ['load', 'generate', 'train', 'fine_tune', 'apply_lora']
    for func_name in key_functions:
        if hasattr(mlx_vlm_module, func_name):
            func = getattr(mlx_vlm_module, func_name)
            examine_function(func, func_name)
    
    # Check for training-related classes
    print(f"\n{'='*80}")
    print("Training-Related Classes")
    print(f"{'='*80}\n")
    
    all_classes = [name for name in dir(mlx_vlm_module) 
                   if inspect.isclass(getattr(mlx_vlm_module, name, None))]
    
    training_keywords = ['train', 'lora', 'adapter', 'fine', 'optim', 'loss']
    training_classes = [name for name in all_classes 
                       if any(kw in name.lower() for kw in training_keywords)]
    
    if training_classes:
        print(f"Found {len(training_classes)} potentially relevant classes:")
        for cls_name in training_classes:
            cls = getattr(mlx_vlm_module, cls_name)
            examine_class(cls, cls_name)
    else:
        print("No obvious training-related classes found in main module")
    
    # Check MLX core for training utilities
    print(f"\n{'='*80}")
    print("MLX Core Training Utilities")
    print(f"{'='*80}\n")
    
    try:
        # Try to import without triggering Metal initialization
        import os
        # Temporarily disable Metal to avoid crashes
        os.environ['MLX_USE_CPU'] = '1'
        
        import mlx.core as mx
        import mlx.nn as nn
        import mlx.optimizers as optim
        
        print("✓ MLX core modules available")
        
        # Check for key training functions
        training_functions = {
            'mx.value_and_grad': hasattr(mx, 'value_and_grad'),
            'mx.grad': hasattr(mx, 'grad'),
            'mx.eval': hasattr(mx, 'eval'),
            'optim.Adam': hasattr(optim, 'Adam'),
            'optim.SGD': hasattr(optim, 'SGD'),
            'optim.AdamW': hasattr(optim, 'AdamW'),
        }
        
        print("\nTraining utilities:")
        for name, available in training_functions.items():
            status = "✓" if available else "✗"
            print(f"  {status} {name}")
        
    except ImportError as e:
        print(f"✗ MLX core not available: {e}")
    except Exception as e:
        print(f"⚠ MLX core check failed (Metal GPU issue): {e}")
        print("  This is expected in some environments. MLX should work fine when actually training.")
    
    # Check model structure
    print(f"\n{'='*80}")
    print("Model Structure Investigation")
    print(f"{'='*80}\n")
    
    try:
        # Try to load a small model to examine structure
        print("Attempting to examine model structure...")
        print("(This may download a model if not cached)")
        
        # We'll just check what load() returns, not actually load
        load_func = getattr(mlx_vlm_module, 'load', None)
        if load_func:
            print(f"  load() function signature: {inspect.signature(load_func)}")
            if load_func.__doc__:
                print(f"  Documentation preview:")
                doc_lines = load_func.__doc__.strip().split('\n')[:5]
                for line in doc_lines:
                    print(f"    {line}")
        
    except Exception as e:
        print(f"  Could not examine model structure: {e}")
    
    # Summary
    print(f"\n{'='*80}")
    print("Investigation Summary")
    print(f"{'='*80}\n")
    
    print("Next steps:")
    print("1. Review the findings above")
    print("2. Check mlx-vlm GitHub repository for examples")
    print("3. Look for training scripts in mlx-vlm examples")
    print("4. Examine model architecture to identify LoRA target modules")
    print("5. Plan implementation based on available utilities")


if __name__ == "__main__":
    main()

