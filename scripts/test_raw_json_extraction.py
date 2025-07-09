#!/usr/bin/env python3
"""
Test script for Raw JSON extraction functionality
Tests the enhanced skill_pdf_html_parser.py with raw document data extraction
"""

import os
import sys
import json
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skill_pdf_html_parser import SkillPDFHTMLParser

def test_raw_json_extraction():
    """Test raw JSON extraction on a sample HTML file"""
    
    # Test configuration
    output_dir = "/mnt/d/git/VSCodeExtension-SKILL/docs/test_raw_extraction"
    html_file = os.path.join(output_dir, "test_sample.html")
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if test HTML exists
    if not os.path.exists(html_file):
        print(f"❌ Test HTML not found: {html_file}")
        print("Please ensure HTML test file is available")
        return False
    
    print("🚀 Testing Raw JSON Extraction...")
    print(f"📄 Test HTML: {html_file}")
    print(f"📁 Output Directory: {output_dir}")
    print("-" * 50)
    
    # Initialize parser
    parser = SkillPDFHTMLParser()
    
    print(f"✅ Using existing HTML file: {html_file}")
    
    # Step 2: Extract raw document data
    print("🔄 Extracting raw document data...")
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    raw_data = parser.extract_raw_document_data(
        html_content=html_content,
        document_name="Cadence SKILL Language Reference (Test)",
        pdf_path="test_sample.html"
    )
    
    print(f"✅ Raw data extracted:")
    print(f"   📊 Total pages: {raw_data.metadata['total_pages']}")
    print(f"   🔧 Total functions: {raw_data.metadata['total_functions']}")
    print(f"   📂 Total categories: {raw_data.metadata['total_categories']}")
    
    # Step 3: Save raw data to JSON
    raw_json_file = os.path.join(output_dir, "test_sample_raw.json")
    print(f"🔄 Saving raw data to: {raw_json_file}")
    
    parser.save_raw_document_data(raw_data, raw_json_file)
    print(f"✅ Raw JSON saved")
    
    # Step 4: Validate JSON structure
    print("🔄 Validating JSON structure...")
    
    with open(raw_json_file, 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
    
    # Check structure
    required_keys = ['metadata', 'pages', 'functions', 'categories', 'raw_text', 'html_content']
    missing_keys = [key for key in required_keys if key not in loaded_data]
    
    if missing_keys:
        print(f"❌ Missing required keys: {missing_keys}")
        return False
    
    print("✅ JSON structure validation passed")
    
    # Step 5: Display sample data
    print("\n📋 Sample Raw Data Structure:")
    print("-" * 30)
    
    print(f"🔹 Metadata Keys: {list(loaded_data['metadata'].keys())}")
    print(f"🔹 Pages Count: {len(loaded_data['pages'])}")
    print(f"🔹 Functions Count: {len(loaded_data['functions'])}")
    print(f"🔹 Categories Count: {len(loaded_data['categories'])}")
    
    # Show first function as example
    if loaded_data['functions']:
        first_func = loaded_data['functions'][0]
        print(f"\n📝 Sample Function:")
        print(f"   Name: {first_func['name']}")
        print(f"   Page: {first_func['page_number']}")
        print(f"   Signature: {first_func['raw_signature'][:50]}...")
        print(f"   Position: x={first_func['position']['x']}, y={first_func['position']['y']}")
    
    # Show first category as example
    if loaded_data['categories']:
        first_cat = loaded_data['categories'][0]
        print(f"\n📂 Sample Category:")
        print(f"   Text: {first_cat['text']}")
        print(f"   Level: {first_cat['level']}")
        print(f"   Font Size: {first_cat['font_size']}")
    
    print("\n🎉 Raw JSON extraction test completed successfully!")
    print(f"📁 Test files saved in: {output_dir}")
    
    return True

def analyze_raw_json_quality(json_file: str):
    """Analyze the quality and completeness of raw JSON data"""
    
    print(f"\n🔍 Analyzing Raw JSON Quality: {json_file}")
    print("-" * 40)
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Metadata analysis
    metadata = data['metadata']
    print(f"📊 Metadata Analysis:")
    print(f"   Source: {metadata.get('source_file', 'N/A')}")
    print(f"   Document: {metadata.get('document_name', 'N/A')}")
    print(f"   Pages: {metadata.get('total_pages', 0)}")
    print(f"   Functions: {metadata.get('total_functions', 0)}")
    print(f"   Categories: {metadata.get('total_categories', 0)}")
    
    # Functions analysis
    functions = data['functions']
    if functions:
        complete_functions = [f for f in functions if f['raw_description'] and f['raw_signature']]
        with_examples = [f for f in functions if f['raw_examples']]
        with_parameters = [f for f in functions if f['raw_parameters']]
        
        print(f"\n🔧 Functions Analysis:")
        print(f"   Total functions: {len(functions)}")
        print(f"   Complete functions (desc+sig): {len(complete_functions)}")
        print(f"   Functions with examples: {len(with_examples)}")
        print(f"   Functions with parameters: {len(with_parameters)}")
        print(f"   Completeness rate: {len(complete_functions)/len(functions)*100:.1f}%")
    
    # Categories analysis
    categories = data['categories']
    if categories:
        level_counts = {}
        for cat in categories:
            level = cat.get('level', 0)
            level_counts[level] = level_counts.get(level, 0) + 1
        
        print(f"\n📂 Categories Analysis:")
        print(f"   Total categories: {len(categories)}")
        print(f"   Level distribution: {level_counts}")
    
    # Content preservation analysis
    raw_text_length = len(data.get('raw_text', ''))
    html_content_length = len(data.get('html_content', ''))
    
    print(f"\n📝 Content Preservation:")
    print(f"   Raw text length: {raw_text_length:,} characters")
    print(f"   HTML content length: {html_content_length:,} characters")
    
    return True

if __name__ == "__main__":
    print("🧪 Raw JSON Extraction Test Suite")
    print("=" * 50)
    
    # Run test
    success = test_raw_json_extraction()
    
    if success:
        # Analyze results
        test_json = "/mnt/d/git/VSCodeExtension-SKILL/docs/test_raw_extraction/test_sample_raw.json"
        if os.path.exists(test_json):
            analyze_raw_json_quality(test_json)
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed! Raw JSON extraction is working correctly.")
        print("📋 Next steps:")
        print("   1. Review the generated raw JSON file")
        print("   2. Confirm the data structure meets requirements")
        print("   3. Proceed to Phase 2 (Raw → Structured conversion)")
    else:
        print("❌ Tests failed. Please check the error messages above.")