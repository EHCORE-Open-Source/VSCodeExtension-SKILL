#!/usr/bin/env python3
"""
Analyze the comparison between pdftotext and pdftohtml conversion results
"""

import os
import re
import json
from bs4 import BeautifulSoup

def analyze_pdftotext_format():
    """Analyze pdftotext -bbox format"""
    file_path = "/mnt/d/git/VSCodeExtension-SKILL/docs/conversion_comparison/test_pdftotext.html"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # Extract structure information
    pages = soup.find_all('page')
    words = soup.find_all('word')
    
    # Sample word structure
    sample_words = []
    for word in words[:5]:
        sample_words.append({
            'text': word.get_text(),
            'xMin': word.get('xmin'),
            'yMin': word.get('ymin'),
            'xMax': word.get('xmax'),
            'yMax': word.get('ymax')
        })
    
    return {
        'format': 'pdftotext -bbox',
        'file_size_mb': os.path.getsize(file_path) / 1024 / 1024,
        'total_pages': len(pages),
        'total_words': len(words),
        'positioning': 'Bounding boxes (xmin, ymin, xmax, ymax)',
        'sample_words': sample_words,
        'advantages': [
            'Precise word-level bounding boxes',
            'Individual word positioning',
            'Easy to extract exact coordinates',
            'Word-by-word granularity'
        ],
        'disadvantages': [
            'Larger file size',
            'No font information',
            'No text styling information',
            'No layout structure preservation'
        ]
    }

def analyze_pdftohtml_format():
    """Analyze pdftohtml -xml format"""
    file_path = "/mnt/d/git/VSCodeExtension-SKILL/docs/conversion_comparison/test_pdftohtml_direct.xml"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'xml')
    
    # Extract structure information
    pages = soup.find_all('page')
    texts = soup.find_all('text')
    fontspecs = soup.find_all('fontspec')
    
    # Sample text structure
    sample_texts = []
    for text in texts[:5]:
        sample_texts.append({
            'text': text.get_text(),
            'top': text.get('top'),
            'left': text.get('left'),
            'width': text.get('width'),
            'height': text.get('height'),
            'font': text.get('font')
        })
    
    # Sample font information
    sample_fonts = []
    for font in fontspecs[:3]:
        sample_fonts.append({
            'id': font.get('id'),
            'size': font.get('size'),
            'family': font.get('family'),
            'color': font.get('color')
        })
    
    return {
        'format': 'pdftohtml -xml',
        'file_size_mb': os.path.getsize(file_path) / 1024 / 1024,
        'total_pages': len(pages),
        'total_texts': len(texts),
        'total_fonts': len(fontspecs),
        'positioning': 'Top-left coordinates with width/height',
        'sample_texts': sample_texts,
        'sample_fonts': sample_fonts,
        'advantages': [
            'Smaller file size',
            'Font information preserved',
            'Text styling information',
            'Layout structure better preserved',
            'Line-level text grouping'
        ],
        'disadvantages': [
            'Less precise positioning',
            'Text grouped in lines/blocks',
            'Different coordinate system',
            'May lose word boundaries'
        ]
    }

def compare_function_extraction_suitability():
    """Compare suitability for function extraction"""
    
    # Test function pattern recognition
    pdftotext_path = "/mnt/d/git/VSCodeExtension-SKILL/docs/conversion_comparison/test_pdftotext.html"
    pdftohtml_path = "/mnt/d/git/VSCodeExtension-SKILL/docs/conversion_comparison/test_pdftohtml_direct.xml"
    
    with open(pdftotext_path, 'r', encoding='utf-8') as f:
        pdftotext_content = f.read()
    
    with open(pdftohtml_path, 'r', encoding='utf-8') as f:
        pdftohtml_content = f.read()
    
    # Look for function-like patterns
    function_pattern = r'[a-zA-Z][a-zA-Z0-9_]*\s*\('
    
    pdftotext_functions = re.findall(function_pattern, pdftotext_content)
    pdftohtml_functions = re.findall(function_pattern, pdftohtml_content)
    
    # Look for specific SKILL functions
    skill_functions = ['append', 'car', 'cdr', 'cons', 'list', 'length', 'reverse']
    
    pdftotext_skill_found = []
    pdftohtml_skill_found = []
    
    for func in skill_functions:
        if func in pdftotext_content:
            pdftotext_skill_found.append(func)
        if func in pdftohtml_content:
            pdftohtml_skill_found.append(func)
    
    return {
        'pdftotext': {
            'function_patterns_found': len(pdftotext_functions),
            'sample_patterns': pdftotext_functions[:10],
            'skill_functions_found': pdftotext_skill_found
        },
        'pdftohtml': {
            'function_patterns_found': len(pdftohtml_functions),
            'sample_patterns': pdftohtml_functions[:10],
            'skill_functions_found': pdftohtml_skill_found
        }
    }

def analyze_parser_adaptation_needed():
    """Analyze what parser changes would be needed for each format"""
    
    return {
        'pdftotext_adaptation': {
            'current_parser': 'Already implemented',
            'changes_needed': [
                'None - current parser works well',
                'Already extracts word-level positioning',
                'Good for precise function signature extraction'
            ],
            'effort_level': 'Low (already done)'
        },
        'pdftohtml_adaptation': {
            'current_parser': 'Would need significant changes',
            'changes_needed': [
                'Change from <word> to <text> parsing',
                'Adapt coordinate system (top/left vs min/max)',
                'Handle font information integration',
                'Modify positioning calculations',
                'Handle line-level text grouping'
            ],
            'effort_level': 'High (major refactoring needed)'
        }
    }

def generate_recommendation():
    """Generate final recommendation based on analysis"""
    
    pdftotext_analysis = analyze_pdftotext_format()
    pdftohtml_analysis = analyze_pdftohtml_format()
    function_comparison = compare_function_extraction_suitability()
    parser_adaptation = analyze_parser_adaptation_needed()
    
    # Calculate scores
    pdftotext_score = 0
    pdftohtml_score = 0
    
    # File size (smaller is better)
    if pdftotext_analysis['file_size_mb'] < pdftohtml_analysis['file_size_mb']:
        pdftohtml_score += 1
    else:
        pdftotext_score += 1
    
    # Positioning precision (more precise is better)
    pdftotext_score += 2  # Word-level bounding boxes
    pdftohtml_score += 1  # Line-level positioning
    
    # Font information (having it is better)
    pdftohtml_score += 1  # Has font info
    
    # Parser adaptation effort (less effort is better)
    pdftotext_score += 3  # Already implemented
    pdftohtml_score += 0  # Would need major changes
    
    # Function extraction suitability
    pdftotext_funcs = function_comparison['pdftotext']['function_patterns_found']
    pdftohtml_funcs = function_comparison['pdftohtml']['function_patterns_found']
    
    if pdftotext_funcs > pdftohtml_funcs:
        pdftotext_score += 1
    elif pdftohtml_funcs > pdftotext_funcs:
        pdftohtml_score += 1
    
    recommendation = {
        'scores': {
            'pdftotext': pdftotext_score,
            'pdftohtml': pdftohtml_score
        },
        'recommended_method': 'pdftotext -bbox' if pdftotext_score > pdftohtml_score else 'pdftohtml -xml',
        'reasoning': [],
        'trade_offs': {}
    }
    
    if pdftotext_score > pdftohtml_score:
        recommendation['reasoning'] = [
            'pdftotext -bbox provides more precise word-level positioning',
            'Parser is already fully implemented and tested',
            'Better suited for function signature extraction',
            'No significant development effort required'
        ]
        recommendation['trade_offs'] = {
            'benefits': ['Precise positioning', 'No parser changes needed', 'Better function extraction'],
            'costs': ['Larger file size', 'No font information', 'No styling']
        }
    else:
        recommendation['reasoning'] = [
            'pdftohtml -xml provides smaller file size',
            'Includes font and styling information',
            'Better layout preservation'
        ]
        recommendation['trade_offs'] = {
            'benefits': ['Smaller files', 'Font info', 'Layout structure'],
            'costs': ['Major parser rewrite needed', 'Less precise positioning', 'Development effort']
        }
    
    return recommendation

def main():
    """Main analysis function"""
    print("📊 PDF Conversion Methods Detailed Analysis")
    print("=" * 60)
    
    # Analyze both formats
    pdftotext_analysis = analyze_pdftotext_format()
    pdftohtml_analysis = analyze_pdftohtml_format()
    
    print(f"\n🔹 {pdftotext_analysis['format']} Analysis:")
    print(f"   File size: {pdftotext_analysis['file_size_mb']:.1f} MB")
    print(f"   Pages: {pdftotext_analysis['total_pages']}")
    print(f"   Words: {pdftotext_analysis['total_words']:,}")
    print(f"   Positioning: {pdftotext_analysis['positioning']}")
    print(f"   Sample word: {pdftotext_analysis['sample_words'][0]}")
    
    print(f"\n🔹 {pdftohtml_analysis['format']} Analysis:")
    print(f"   File size: {pdftohtml_analysis['file_size_mb']:.1f} MB")
    print(f"   Pages: {pdftohtml_analysis['total_pages']}")
    print(f"   Text elements: {pdftohtml_analysis['total_texts']:,}")
    print(f"   Font specs: {pdftohtml_analysis['total_fonts']}")
    print(f"   Positioning: {pdftohtml_analysis['positioning']}")
    print(f"   Sample text: {pdftohtml_analysis['sample_texts'][0]}")
    print(f"   Sample font: {pdftohtml_analysis['sample_fonts'][0]}")
    
    # Function extraction comparison
    function_comparison = compare_function_extraction_suitability()
    print(f"\n🔧 Function Extraction Comparison:")
    print(f"   pdftotext patterns found: {function_comparison['pdftotext']['function_patterns_found']}")
    print(f"   pdftohtml patterns found: {function_comparison['pdftohtml']['function_patterns_found']}")
    print(f"   pdftotext SKILL functions: {function_comparison['pdftotext']['skill_functions_found']}")
    print(f"   pdftohtml SKILL functions: {function_comparison['pdftohtml']['skill_functions_found']}")
    
    # Parser adaptation analysis
    parser_adaptation = analyze_parser_adaptation_needed()
    print(f"\n🔧 Parser Adaptation Required:")
    print(f"   pdftotext: {parser_adaptation['pdftotext_adaptation']['effort_level']}")
    print(f"   pdftohtml: {parser_adaptation['pdftohtml_adaptation']['effort_level']}")
    
    # Generate recommendation
    recommendation = generate_recommendation()
    print(f"\n🎯 Final Recommendation:")
    print(f"   Recommended method: {recommendation['recommended_method']}")
    print(f"   Score: pdftotext={recommendation['scores']['pdftotext']}, pdftohtml={recommendation['scores']['pdftohtml']}")
    print(f"   Reasoning:")
    for reason in recommendation['reasoning']:
        print(f"     • {reason}")
    
    print(f"\n📋 Trade-offs:")
    print(f"   Benefits: {recommendation['trade_offs']['benefits']}")
    print(f"   Costs: {recommendation['trade_offs']['costs']}")
    
    return recommendation

if __name__ == "__main__":
    main()