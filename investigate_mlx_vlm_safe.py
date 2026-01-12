#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Safe MLX-VLM Investigation (without importing MLX)
Examines mlx-vlm package structure without triggering Metal initialization
"""

import sys
import os
import inspect
import importlib
import pkgutil

def safe_import(module_name):
    """Safely import a module, catching all exceptions"""
    try:
        return importlib.import_module(module_name)
    except Exception as e:
        return None, str(e)

def examine_package_structure(package_name):
    """Examine package structure without importing"""
    print(f"\n{'='*80}")
    print(f"Package Structure: {package_name}")
    print(f"{'='*80}\n")
    
    try:
        # Try to find package location
        spec = importlib.util.find_spec(package_name)
        if spec and spec.origin:
            print(f"✓ Package found at: {spec.origin}")
            
            # Get package directory
            if spec.submodule_search_locations:
                pkg_dir = spec.submodule_search_locations[0]
                print(f"  Package directory: {pkg_dir}")
                
                # List files in package
                if os.path.exists(pkg_dir):
                    files = [f for f in os.listdir(pkg_dir) 
                            if f.endswith('.py') and not f.startswith('__')]
                    if files:
                        print(f"\n  Python modules found:")
                        for f in sorted(files):
                            print(f"    - {f[:-3]}")
        else:
            print(f"✗ Could not locate package")
    except Exception as e:
        print(f"✗ Error examining structure: {e}")

def check_file_for_keywords(filepath, keywords):
    """Check a file for specific keywords"""
    if not os.path.exists(filepath):
        return []
    
    found = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()
            for keyword in keywords:
                if keyword.lower() in content:
                    found.append(keyword)
    except:
        pass
    return found

def main():
    print("="*80)
    print("MLX-VLM Safe Investigation (No MLX Import)")
    print("="*80)
    
    # Check if mlx-vlm package exists
    try:
        import importlib.util
        spec = importlib.util.find_spec("mlx_vlm")
        if spec is None:
            print("\n✗ mlx-vlm is not installed")
            print("  Install with: pip install mlx-vlm")
            return
        
        print("\n✓ mlx-vlm package found")
        print(f"  Location: {spec.origin if spec.origin else 'Unknown'}")
        
        # Get package directory
        if spec.submodule_search_locations:
            pkg_dir = spec.submodule_search_locations[0]
            print(f"  Package directory: {pkg_dir}")
            
            # List submodules
            print(f"\n📦 Package Structure:")
            try:
                for importer, modname, ispkg in pkgutil.iter_modules([pkg_dir]):
                    mod_type = "package" if ispkg else "module"
                    print(f"  📁 {modname} ({mod_type})")
            except:
                pass
            
            # Check for key files
            print(f"\n🔍 Key Files:")
            key_files = [
                '__init__.py',
                'models.py',
                'utils.py',
                'prompt_utils.py',
                'training.py',
                'lora.py',
            ]
            
            for key_file in key_files:
                filepath = os.path.join(pkg_dir, key_file)
                exists = os.path.exists(filepath)
                status = "✓" if exists else "✗"
                print(f"  {status} {key_file}")
                
                # Check for LoRA/training keywords
                if exists:
                    keywords = ['lora', 'adapter', 'train', 'fine', 'tune', 'gradient', 'optimizer']
                    found = check_file_for_keywords(filepath, keywords)
                    if found:
                        print(f"      → Found keywords: {', '.join(found)}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Check __init__.py for exports
    print(f"\n{'='*80}")
    print("Package Exports (from __init__.py)")
    print(f"{'='*80}\n")
    
    try:
        if spec.submodule_search_locations:
            init_file = os.path.join(spec.submodule_search_locations[0], '__init__.py')
            if os.path.exists(init_file):
                with open(init_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Look for imports/exports
                    imports = []
                    if '__all__' in content:
                        # Extract __all__ list
                        import re
                        all_match = re.search(r'__all__\s*=\s*\[(.*?)\]', content, re.DOTALL)
                        if all_match:
                            items = [item.strip().strip('"\'') 
                                    for item in all_match.group(1).split(',')]
                            imports.extend(items)
                    
                    # Look for common function/class names
                    common_names = ['load', 'generate', 'train', 'fine_tune', 'apply_lora']
                    for name in common_names:
                        if name in content:
                            imports.append(name)
                    
                    if imports:
                        print("  Exported items found:")
                        for item in sorted(set(imports)):
                            print(f"    - {item}")
                    else:
                        print("  (Could not determine exports)")
    except Exception as e:
        print(f"  Error reading __init__.py: {e}")
    
    # Summary
    print(f"\n{'='*80}")
    print("Investigation Summary")
    print(f"{'='*80}\n")
    
    print("Next steps:")
    print("1. Review package structure above")
    print("2. Check mlx-vlm GitHub: https://github.com/Blaizzy/mlx-vlm")
    print("3. Look for training examples in repository")
    print("4. Examine source code for LoRA support")
    print("5. Test actual imports in a proper environment (not sandboxed)")

if __name__ == "__main__":
    main()





