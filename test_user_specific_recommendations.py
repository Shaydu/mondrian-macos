#!/usr/bin/env python3
"""
Test that recommendations are specific to the user's uploaded image
and don't reference mountains/rocks/landscapes for non-landscape images.
"""

import os
import sys
from mondrian.ai_advisor_service_linux import QwenAdvisor

def test_recommendations(image_path, expected_subject):
    """Test that recommendations match the actual image content"""
    print(f"\n{'='*80}")
    print(f"Testing: {os.path.basename(image_path)}")
    print(f"Expected subject: {expected_subject}")
    print(f"{'='*80}\n")
    
    advisor = QwenAdvisor()
    
    try:
        result = advisor.analyze_image(
            image_path=image_path,
            advisor='ansel',
            mode='rag',
            job_id='test_user_specific'
        )
        
        print(f"✓ Analysis completed successfully\n")
        print(f"Image Description: {result.get('image_description', 'N/A')}\n")
        
        # Check each dimension's recommendation
        inappropriate_keywords = ['mountain', 'mountains', 'rock', 'rocks', 'boulder', 
                                 'horizon', 'landscape', 'peak', 'valley', 'cliff']
        
        issues_found = []
        
        for dim in result.get('dimensions', []):
            name = dim.get('name', 'Unknown')
            recommendation = dim.get('recommendation', '')
            
            print(f"{name}:")
            print(f"  Score: {dim.get('score', 'N/A')}")
            print(f"  Comment: {dim.get('comment', 'N/A')[:100]}...")
            print(f"  Recommendation: {recommendation[:150]}...")
            
            # Check for inappropriate landscape-specific keywords
            if expected_subject.lower() != 'landscape':
                for keyword in inappropriate_keywords:
                    if keyword.lower() in recommendation.lower():
                        issues_found.append(f"{name}: Contains '{keyword}' in recommendation")
            
            print()
        
        # Report results
        if issues_found:
            print(f"\n⚠️  ISSUES FOUND:")
            for issue in issues_found:
                print(f"  - {issue}")
            return False
        else:
            print(f"✅ All recommendations are appropriate for {expected_subject}")
            return True
            
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # Find a test image in the dataset
    test_images = [
        # Add paths to test images here
        "data/reference_images/ansel/moonrise.jpg",  # landscape
        "data/user_uploads/portrait.jpg",  # portrait (if available)
    ]
    
    # Check what images are available
    available_images = []
    for img_path in test_images:
        if os.path.exists(img_path):
            available_images.append(img_path)
    
    if not available_images:
        print("No test images found. Please provide a test image path as argument.")
        print(f"Usage: python {sys.argv[0]} <image_path> <expected_subject>")
        print(f"Example: python {sys.argv[0]} test_portrait.jpg portrait")
        return
    
    # Test with available images
    for img_path in available_images:
        # Determine expected subject from path
        expected = 'landscape' if 'ansel' in img_path else 'unknown'
        test_recommendations(img_path, expected)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        expected_subject = sys.argv[2] if len(sys.argv) > 2 else 'unknown'
        test_recommendations(image_path, expected_subject)
    else:
        main()
