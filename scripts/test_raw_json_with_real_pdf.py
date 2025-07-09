#!/usr/bin/env python3
"""
Test Raw JSON extraction with real SKILL PDF files
Tests the enhanced skill_pdf_html_parser.py with actual Cadence SKILL manuals
"""

import os
import sys
import json
import subprocess
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skill_pdf_html_parser import SkillPDFHTMLParser

def check_dependencies():
    """Check if required tools are available"""
    try:
        result = subprocess.run(['pdftotext', '-v'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ pdftotext not found. Installing poppler-utils...")
            # Try to install poppler-utils
            subprocess.run(['sudo', 'apt-get', 'update'], check=False)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'poppler-utils'], check=False)
            
            # Check again
            result = subprocess.run(['pdftotext', '-v'], capture_output=True, text=True)
            if result.returncode != 0:
                print("❌ Failed to install pdftotext. Please install manually:")
                print("   sudo apt-get install poppler-utils")
                return False
        
        print("✅ pdftotext is available")
        return True
    except FileNotFoundError:
        print("❌ pdftotext not found. Please install poppler-utils:")
        print("   sudo apt-get install poppler-utils")
        return False

def test_raw_json_with_real_pdf():
    """Test raw JSON extraction with sklangref.pdf"""
    
    # Configuration
    pdf_source_dir = "/mnt/d/git/skillRef"
    test_pdf = os.path.join(pdf_source_dir, "sklangref.pdf")
    output_dir = "/mnt/d/git/VSCodeExtension-SKILL/docs/raw_extraction"
    
    # Ensure directories exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if source PDF exists
    if not os.path.exists(test_pdf):
        print(f"❌ Source PDF not found: {test_pdf}")
        print("Please ensure SKILL PDF files are available in /mnt/d/git/skillRef/")
        return False
    
    print("🚀 Testing Raw JSON Extraction with Real SKILL PDF")
    print(f"📄 Source PDF: {test_pdf}")
    print(f"📁 Output Directory: {output_dir}")
    print(f"📊 PDF Size: {os.path.getsize(test_pdf)/1024/1024:.1f} MB")
    print("-" * 60)
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Initialize parser
    parser = SkillPDFHTMLParser()
    
    # Step 1: Convert PDF to HTML
    html_file = os.path.join(output_dir, "sklangref.html")
    print("🔄 Converting PDF to HTML (this may take a few minutes)...")
    
    if not parser.convert_pdf_to_html(test_pdf, html_file):
        print("❌ Failed to convert PDF to HTML")
        return False
    
    html_size = os.path.getsize(html_file) / 1024 / 1024
    print(f"✅ HTML file created: {html_file} ({html_size:.1f} MB)")
    
    # Step 2: Extract raw document data
    print("🔄 Extracting raw document data...")
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    raw_data = parser.extract_raw_document_data(
        html_content=html_content,
        document_name="Cadence SKILL Language Reference",
        pdf_path=test_pdf
    )
    
    print(f"✅ Raw data extracted:")
    print(f"   📊 Total pages: {raw_data.metadata['total_pages']}")
    print(f"   🔧 Total functions: {raw_data.metadata['total_functions']}")
    print(f"   📂 Total categories: {raw_data.metadata['total_categories']}")
    
    # Step 3: Save raw data to JSON
    raw_json_file = os.path.join(output_dir, "sklangref_raw.json")
    print(f"🔄 Saving raw data to: {raw_json_file}")
    
    parser.save_raw_document_data(raw_data, raw_json_file)
    
    json_size = os.path.getsize(raw_json_file) / 1024 / 1024
    print(f"✅ Raw JSON saved ({json_size:.1f} MB)")
    
    # Step 4: Validate and analyze
    print("🔄 Analyzing raw JSON content...")
    analyze_raw_json_quality(raw_json_file, detailed=True)
    
    print(f"\n🎉 Raw JSON extraction completed successfully!")
    print(f"📁 Files saved in: {output_dir}")
    print(f"   📄 HTML: sklangref.html ({html_size:.1f} MB)")
    print(f"   📊 Raw JSON: sklangref_raw.json ({json_size:.1f} MB)")
    
    return True

def analyze_raw_json_quality(json_file: str, detailed: bool = False):
    """Analyze the quality and completeness of raw JSON data"""
    
    print(f"\n🔍 Analyzing Raw JSON Quality: {os.path.basename(json_file)}")
    print("-" * 50)
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Metadata analysis
    metadata = data['metadata']
    print(f"📊 Metadata Analysis:")
    print(f"   Source: {os.path.basename(metadata.get('source_file', 'N/A'))}")
    print(f"   Document: {metadata.get('document_name', 'N/A')}")
    print(f"   Pages: {metadata.get('total_pages', 0)}")
    print(f"   Functions: {metadata.get('total_functions', 0)}")
    print(f"   Categories: {metadata.get('total_categories', 0)}")
    print(f"   Parser Version: {metadata.get('parser_version', 'N/A')}")
    
    # Functions analysis
    functions = data['functions']
    if functions:
        complete_functions = [f for f in functions if f['raw_description'] and f['raw_signature']]
        with_examples = [f for f in functions if f['raw_examples'].strip()]
        with_parameters = [f for f in functions if f['raw_parameters'].strip()]
        with_return_info = [f for f in functions if f['raw_return_info'].strip()]
        with_context = [f for f in functions if f['context_after'].strip()]
        
        print(f"\n🔧 Functions Analysis:")
        print(f"   Total functions: {len(functions)}")
        print(f"   Complete functions (desc+sig): {len(complete_functions)} ({len(complete_functions)/len(functions)*100:.1f}%)")
        print(f"   Functions with examples: {len(with_examples)} ({len(with_examples)/len(functions)*100:.1f}%)")
        print(f"   Functions with parameters: {len(with_parameters)} ({len(with_parameters)/len(functions)*100:.1f}%)")
        print(f"   Functions with return info: {len(with_return_info)} ({len(with_return_info)/len(functions)*100:.1f}%)")
        print(f"   Functions with context: {len(with_context)} ({len(with_context)/len(functions)*100:.1f}%)")
        
        if detailed and functions:
            print(f"\n📝 Sample Functions:")
            for i, func in enumerate(functions[:3]):
                print(f"   {i+1}. {func['name']} (Page {func['page_number']})")
                print(f"      Signature: {func['raw_signature'][:60]}...")
                print(f"      Description: {func['raw_description'][:80]}...")
                if func['category_context']:
                    print(f"      Category: {func['category_context']}")
    
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
        
        if detailed and categories:
            print(f"   Sample categories:")
            for i, cat in enumerate(categories[:5]):
                print(f"     {i+1}. '{cat['text']}' (Level {cat['level']}, Page {cat['page_number']})")
    
    # Content preservation analysis
    raw_text_length = len(data.get('raw_text', ''))
    html_content_length = len(data.get('html_content', ''))
    
    print(f"\n📝 Content Preservation:")
    print(f"   Raw text length: {raw_text_length:,} characters")
    print(f"   HTML content length: {html_content_length:,} characters")
    print(f"   Compression ratio: {html_content_length/raw_text_length:.1f}x")
    
    # Pages analysis
    pages = data.get('pages', [])
    if pages:
        total_words = sum(page.get('word_count', 0) for page in pages)
        avg_words_per_page = total_words / len(pages) if pages else 0
        
        print(f"\n📄 Pages Analysis:")
        print(f"   Total pages: {len(pages)}")
        print(f"   Total words: {total_words:,}")
        print(f"   Average words per page: {avg_words_per_page:.0f}")
    
    return True

def show_extraction_summary(output_dir: str):
    """Show summary of extracted files"""
    
    print(f"\n📋 Extraction Summary")
    print("=" * 40)
    
    files = {
        'HTML': 'sklangref.html',
        'Raw JSON': 'sklangref_raw.json'
    }
    
    for file_type, filename in files.items():
        filepath = os.path.join(output_dir, filename)
        if os.path.exists(filepath):
            size_mb = os.path.getsize(filepath) / 1024 / 1024
            print(f"✅ {file_type}: {filename} ({size_mb:.1f} MB)")
        else:
            print(f"❌ {file_type}: {filename} (not found)")

if __name__ == "__main__":
    print("🧪 Raw JSON Extraction Test with Real SKILL PDF")
    print("=" * 60)
    
    # Run test
    success = test_raw_json_with_real_pdf()
    
    if success:
        output_dir = "/mnt/d/git/VSCodeExtension-SKILL/docs/raw_extraction"
        show_extraction_summary(output_dir)
        
        print("\n✅ Raw JSON extraction test completed successfully!")
        print("📋 Next steps:")
        print("   1. Review the generated sklangref_raw.json file")
        print("   2. Confirm the data structure and content quality")
        print("   3. If satisfied, proceed to Phase 2 (Raw → Structured conversion)")
        print("\n🔍 To review the raw JSON:")
        print(f"   less {output_dir}/sklangref_raw.json")
        print(f"   jq '.metadata' {output_dir}/sklangref_raw.json")
    else:
        print("❌ Raw JSON extraction test failed.")
        print("Please check the error messages above and resolve any issues.")