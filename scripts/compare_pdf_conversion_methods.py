#!/usr/bin/env python3
"""
Compare pdftohtml vs pdftotext conversion methods for SKILL PDF processing
Tests both methods and analyzes their effectiveness for Raw JSON extraction
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_pdftotext_conversion(pdf_path: str, output_dir: str):
    """Test pdftotext -bbox conversion"""
    print("🔄 Testing pdftotext -bbox conversion...")
    
    html_file = os.path.join(output_dir, "test_pdftotext.html")
    start_time = time.time()
    
    try:
        cmd = ['pdftotext', '-bbox', pdf_path, html_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ pdftotext failed: {result.stderr}")
            return None
        
        end_time = time.time()
        file_size = os.path.getsize(html_file) / 1024 / 1024  # MB
        
        # Read and analyze content
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            'method': 'pdftotext -bbox',
            'file_path': html_file,
            'file_size_mb': file_size,
            'processing_time': end_time - start_time,
            'content_length': len(content),
            'has_positioning': '<word' in content,
            'has_pages': '<page' in content,
            'word_count': content.count('<word'),
            'page_count': content.count('<page')
        }
        
    except Exception as e:
        print(f"❌ pdftotext error: {e}")
        return None

def test_pdftohtml_conversion(pdf_path: str, output_dir: str):
    """Test pdftohtml conversion with various options"""
    print("🔄 Testing pdftohtml conversion...")
    
    html_file = os.path.join(output_dir, "test_pdftohtml.html")
    start_time = time.time()
    
    try:
        # Test different pdftohtml options
        cmd = ['pdftohtml', '-xml', '-stdout', pdf_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ pdftohtml failed: {result.stderr}")
            return None
        
        # Save output
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        
        end_time = time.time()
        file_size = os.path.getsize(html_file) / 1024 / 1024  # MB
        
        content = result.stdout
        
        return {
            'method': 'pdftohtml -xml',
            'file_path': html_file,
            'file_size_mb': file_size,
            'processing_time': end_time - start_time,
            'content_length': len(content),
            'has_positioning': any(attr in content for attr in ['top=', 'left=', 'width=', 'height=']),
            'has_pages': '<page' in content,
            'word_count': content.count('<text'),
            'page_count': content.count('<page')
        }
        
    except Exception as e:
        print(f"❌ pdftohtml error: {e}")
        return None

def test_pdftohtml_complex_conversion(pdf_path: str, output_dir: str):
    """Test pdftohtml with complex layout preservation"""
    print("🔄 Testing pdftohtml -c (complex layout) conversion...")
    
    html_file = os.path.join(output_dir, "test_pdftohtml_complex.html")
    start_time = time.time()
    
    try:
        cmd = ['pdftohtml', '-c', '-xml', '-stdout', pdf_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ pdftohtml -c failed: {result.stderr}")
            return None
        
        # Save output
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(result.stdout)
        
        end_time = time.time()
        file_size = os.path.getsize(html_file) / 1024 / 1024  # MB
        
        content = result.stdout
        
        return {
            'method': 'pdftohtml -c -xml',
            'file_path': html_file,
            'file_size_mb': file_size,
            'processing_time': end_time - start_time,
            'content_length': len(content),
            'has_positioning': any(attr in content for attr in ['top=', 'left=', 'width=', 'height=']),
            'has_pages': '<page' in content,
            'word_count': content.count('<text'),
            'page_count': content.count('<page')
        }
        
    except Exception as e:
        print(f"❌ pdftohtml -c error: {e}")
        return None

def analyze_content_structure(result: dict):
    """Analyze content structure for function extraction suitability"""
    if not result:
        return None
    
    file_path = result['file_path']
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Analyze structure
        analysis = {
            'has_font_info': any(attr in content for attr in ['font', 'size']),
            'has_coordinates': any(attr in content for attr in ['x=', 'y=', 'top=', 'left=']),
            'has_bounding_boxes': any(attr in content for attr in ['xmin=', 'ymin=', 'xmax=', 'ymax=']),
            'line_count': content.count('\n'),
            'avg_line_length': len(content) / content.count('\n') if content.count('\n') > 0 else 0,
            'contains_function_patterns': bool(re.search(r'[a-zA-Z][a-zA-Z0-9_]*\s*\(.*?\)', content)),
            'contains_skill_keywords': any(keyword in content.lower() for keyword in ['skill', 'cadence', 'function', 'procedure']),
            'xml_structure_quality': 'good' if '<' in content and '>' in content else 'poor'
        }
        
        # Look for sample function signatures
        import re
        function_patterns = re.findall(r'[a-zA-Z][a-zA-Z0-9_]*\s*\([^)]*\)', content[:10000])
        analysis['sample_functions'] = function_patterns[:5]  # First 5 matches
        
        return analysis
        
    except Exception as e:
        print(f"❌ Content analysis error: {e}")
        return None

def compare_parsing_effectiveness(results: list):
    """Compare parsing effectiveness for different methods"""
    print("\n📊 Parsing Effectiveness Comparison:")
    print("=" * 60)
    
    for i, result in enumerate(results):
        if not result:
            continue
            
        print(f"\n🔹 Method {i+1}: {result['method']}")
        print(f"   File size: {result['file_size_mb']:.1f} MB")
        print(f"   Processing time: {result['processing_time']:.2f} seconds")
        print(f"   Content length: {result['content_length']:,} characters")
        print(f"   Has positioning: {'✅' if result['has_positioning'] else '❌'}")
        print(f"   Word/Text count: {result['word_count']:,}")
        print(f"   Page count: {result['page_count']}")
        
        # Analyze content structure
        analysis = analyze_content_structure(result)
        if analysis:
            print(f"   Font info: {'✅' if analysis['has_font_info'] else '❌'}")
            print(f"   Coordinates: {'✅' if analysis['has_coordinates'] else '❌'}")
            print(f"   Bounding boxes: {'✅' if analysis['has_bounding_boxes'] else '❌'}")
            print(f"   Function patterns: {'✅' if analysis['contains_function_patterns'] else '❌'}")
            print(f"   SKILL keywords: {'✅' if analysis['contains_skill_keywords'] else '❌'}")
            
            if analysis['sample_functions']:
                print(f"   Sample functions: {analysis['sample_functions'][:2]}")

def show_content_samples(results: list):
    """Show content samples from different methods"""
    print("\n📋 Content Structure Samples:")
    print("=" * 60)
    
    for i, result in enumerate(results):
        if not result:
            continue
            
        print(f"\n🔹 {result['method']} Sample:")
        print("-" * 40)
        
        try:
            with open(result['file_path'], 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Show first 500 characters
            sample = content[:500]
            print(sample)
            if len(content) > 500:
                print("... (truncated)")
                
        except Exception as e:
            print(f"❌ Error reading sample: {e}")

def main():
    """Main comparison test"""
    print("🧪 PDF Conversion Methods Comparison Test")
    print("=" * 60)
    
    # Test configuration
    pdf_path = "/mnt/d/git/skillRef/sklangref.pdf"
    output_dir = "/mnt/d/git/VSCodeExtension-SKILL/docs/conversion_comparison"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Check if test PDF exists
    if not os.path.exists(pdf_path):
        print(f"❌ Test PDF not found: {pdf_path}")
        return 1
    
    pdf_size = os.path.getsize(pdf_path) / 1024 / 1024
    print(f"📄 Test PDF: {pdf_path} ({pdf_size:.1f} MB)")
    print(f"📁 Output Directory: {output_dir}")
    print("-" * 60)
    
    # Test all methods
    results = []
    
    # Method 1: pdftotext -bbox
    result1 = test_pdftotext_conversion(pdf_path, output_dir)
    results.append(result1)
    
    # Method 2: pdftohtml -xml
    result2 = test_pdftohtml_conversion(pdf_path, output_dir)
    results.append(result2)
    
    # Method 3: pdftohtml -c -xml
    result3 = test_pdftohtml_complex_conversion(pdf_path, output_dir)
    results.append(result3)
    
    # Compare results
    compare_parsing_effectiveness(results)
    
    # Show content samples
    show_content_samples(results)
    
    # Recommendations
    print("\n🎯 Recommendations:")
    print("=" * 60)
    
    successful_results = [r for r in results if r is not None]
    if successful_results:
        # Find best method based on criteria
        best_for_positioning = max(successful_results, key=lambda x: x['has_positioning'])
        smallest_file = min(successful_results, key=lambda x: x['file_size_mb'])
        fastest_processing = min(successful_results, key=lambda x: x['processing_time'])
        
        print(f"🏆 Best for positioning info: {best_for_positioning['method']}")
        print(f"📦 Smallest file size: {smallest_file['method']} ({smallest_file['file_size_mb']:.1f} MB)")
        print(f"⚡ Fastest processing: {fastest_processing['method']} ({fastest_processing['processing_time']:.2f}s)")
        
        # Overall recommendation
        print(f"\n💡 Overall Recommendation:")
        if any(r['has_positioning'] and r['method'].startswith('pdftohtml') for r in successful_results):
            print("   Consider switching to pdftohtml for better layout preservation")
        else:
            print("   pdftotext -bbox provides good positioning info for current needs")
    
    return 0

if __name__ == "__main__":
    import re
    sys.exit(main())