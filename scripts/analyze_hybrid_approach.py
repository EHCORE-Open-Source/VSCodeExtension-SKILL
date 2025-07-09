#!/usr/bin/env python3
"""
Analyze hybrid approach: pdftotext (main) + pdftohtml (auxiliary) for SKILL PDF processing
Evaluate feasibility and implementation complexity
"""

import os
import sys
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional, Tuple

def analyze_coordinate_alignment():
    """Analyze if coordinates from both methods can be aligned"""
    
    pdftotext_file = "/mnt/d/git/VSCodeExtension-SKILL/docs/conversion_comparison/test_pdftotext.html"
    pdftohtml_file = "/mnt/d/git/VSCodeExtension-SKILL/docs/conversion_comparison/test_pdftohtml_direct.xml"
    
    print("🔍 Analyzing coordinate system alignment...")
    
    # Parse pdftotext format
    with open(pdftotext_file, 'r', encoding='utf-8') as f:
        pdftotext_content = f.read()
    
    pdftotext_soup = BeautifulSoup(pdftotext_content, 'html.parser')
    
    # Parse pdftohtml format  
    with open(pdftohtml_file, 'r', encoding='utf-8', errors='ignore') as f:
        pdftohtml_content = f.read()
    
    pdftohtml_soup = BeautifulSoup(pdftohtml_content, 'xml')
    
    # Get first page from both formats
    pdftotext_page1 = pdftotext_soup.find('page')
    pdftohtml_page1 = pdftohtml_soup.find('page')
    
    if not pdftotext_page1 or not pdftohtml_page1:
        return None
    
    # Extract page dimensions
    pdftotext_dims = {
        'width': float(pdftotext_page1.get('width', 612)),
        'height': float(pdftotext_page1.get('height', 792))
    }
    
    pdftohtml_dims = {
        'width': float(pdftohtml_page1.get('width', 918)),
        'height': float(pdftohtml_page1.get('height', 1188))
    }
    
    # Get sample elements from both
    pdftotext_words = pdftotext_page1.find_all('word')[:10]
    pdftohtml_texts = pdftohtml_page1.find_all('text')[:10]
    
    pdftotext_samples = []
    for word in pdftotext_words:
        pdftotext_samples.append({
            'text': word.get_text(),
            'x_min': float(word.get('xmin', 0)),
            'y_min': float(word.get('ymin', 0)),
            'x_max': float(word.get('xmax', 0)),
            'y_max': float(word.get('ymax', 0))
        })
    
    pdftohtml_samples = []
    for text in pdftohtml_texts:
        pdftohtml_samples.append({
            'text': text.get_text(),
            'top': float(text.get('top', 0)),
            'left': float(text.get('left', 0)),
            'width': float(text.get('width', 0)),
            'height': float(text.get('height', 0))
        })
    
    return {
        'pdftotext_dimensions': pdftotext_dims,
        'pdftohtml_dimensions': pdftohtml_dims,
        'scale_factor': {
            'x': pdftohtml_dims['width'] / pdftotext_dims['width'],
            'y': pdftohtml_dims['height'] / pdftotext_dims['height']
        },
        'pdftotext_samples': pdftotext_samples,
        'pdftohtml_samples': pdftohtml_samples
    }

def analyze_font_mapping_feasibility():
    """Analyze if font information can be mapped to word positions"""
    
    pdftohtml_file = "/mnt/d/git/VSCodeExtension-SKILL/docs/conversion_comparison/test_pdftohtml_direct.xml"
    
    print("🔍 Analyzing font mapping feasibility...")
    
    try:
        with open(pdftohtml_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'xml')
        
        # Extract font specifications
        fontspecs = soup.find_all('fontspec')
        font_map = {}
        
        for fontspec in fontspecs:
            font_id = fontspec.get('id')
            font_map[font_id] = {
                'size': float(fontspec.get('size', 12)),
                'family': fontspec.get('family', 'Unknown'),
                'color': fontspec.get('color', '#000000')
            }
        
        # Get sample texts with font information
        texts = soup.find_all('text')[:20]
        font_usage_samples = []
        
        for text in texts:
            font_id = text.get('font')
            if font_id and font_id in font_map:
                font_usage_samples.append({
                    'text': text.get_text()[:50],
                    'font_id': font_id,
                    'font_info': font_map[font_id],
                    'position': {
                        'top': float(text.get('top', 0)),
                        'left': float(text.get('left', 0)),
                        'width': float(text.get('width', 0)),
                        'height': float(text.get('height', 0))
                    }
                })
        
        return {
            'total_font_specs': len(fontspecs),
            'font_map': font_map,
            'font_usage_samples': font_usage_samples[:5],
            'feasible': len(font_map) > 0
        }
        
    except Exception as e:
        print(f"❌ Error analyzing font mapping: {e}")
        return None

def design_hybrid_architecture():
    """Design the hybrid processing architecture"""
    
    return {
        'approach': 'Dual-pass processing with coordinate alignment',
        'processing_steps': [
            '1. Extract precise word positions using pdftotext -bbox',
            '2. Extract font and layout information using pdftohtml -xml',
            '3. Align coordinate systems using scaling factors',
            '4. Map font information to word positions using spatial proximity',
            '5. Enhance word data with font and styling information',
            '6. Generate enriched Raw JSON with both positioning and styling'
        ],
        'data_structures': {
            'EnhancedWord': {
                'text': 'str',
                'position': 'BoundingBox (x_min, y_min, x_max, y_max)',
                'font_size': 'float',
                'font_family': 'str',
                'font_color': 'str',
                'style': 'Dict[str, Any]'
            },
            'LayoutRegion': {
                'boundary': 'BoundingBox',
                'font_spec': 'FontSpec',
                'text_elements': 'List[str]'
            }
        },
        'coordinate_alignment': {
            'method': 'Linear scaling transformation',
            'formula': 'pdftohtml_coord = pdftotext_coord * scale_factor',
            'validation': 'Cross-reference common text elements'
        }
    }

def estimate_implementation_complexity():
    """Estimate implementation complexity and effort"""
    
    return {
        'complexity_level': 'Medium to High',
        'implementation_phases': {
            'Phase 1': {
                'description': 'Coordinate system alignment',
                'effort': '2-3 days',
                'tasks': [
                    'Calculate scaling factors between coordinate systems',
                    'Implement coordinate transformation functions',
                    'Validate alignment accuracy'
                ]
            },
            'Phase 2': {
                'description': 'Font information extraction',
                'effort': '1-2 days',
                'tasks': [
                    'Parse pdftohtml font specifications',
                    'Create font mapping data structures',
                    'Handle font inheritance and defaults'
                ]
            },
            'Phase 3': {
                'description': 'Spatial font mapping',
                'effort': '3-4 days',
                'tasks': [
                    'Implement spatial proximity algorithms',
                    'Map font regions to word positions',
                    'Handle overlapping and edge cases'
                ]
            },
            'Phase 4': {
                'description': 'Enhanced Raw JSON generation',
                'effort': '2-3 days',
                'tasks': [
                    'Extend existing data structures',
                    'Integrate font information in Raw JSON',
                    'Update serialization functions'
                ]
            },
            'Phase 5': {
                'description': 'Testing and validation',
                'effort': '2-3 days',
                'tasks': [
                    'Test coordinate alignment accuracy',
                    'Validate font mapping correctness',
                    'Performance testing and optimization'
                ]
            }
        },
        'total_effort': '10-15 days',
        'risk_factors': [
            'Coordinate system alignment accuracy',
            'Font mapping precision in complex layouts',
            'Performance impact of dual-pass processing',
            'Handling edge cases in font inheritance'
        ]
    }

def analyze_benefits_vs_costs():
    """Analyze benefits vs implementation costs"""
    
    return {
        'benefits': {
            'enhanced_categorization': {
                'description': 'Better category detection using font size hierarchy',
                'impact': 'High',
                'use_cases': [
                    'More accurate chapter/section detection',
                    'Function vs description text differentiation',
                    'Header/footer identification'
                ]
            },
            'improved_layout_understanding': {
                'description': 'Better understanding of document structure',
                'impact': 'Medium',
                'use_cases': [
                    'Table detection and parsing',
                    'Code block identification',
                    'Sidebar content handling'
                ]
            },
            'enhanced_function_parsing': {
                'description': 'Better function signature vs description separation',
                'impact': 'Medium',
                'use_cases': [
                    'Function name identification using bold fonts',
                    'Parameter vs description text distinction',
                    'Example code block detection'
                ]
            },
            'styling_preservation': {
                'description': 'Preserve original document styling',
                'impact': 'Low to Medium',
                'use_cases': [
                    'Rich text output generation',
                    'Style-aware content processing',
                    'Visual hierarchy understanding'
                ]
            }
        },
        'costs': {
            'development_time': '10-15 days',
            'complexity_increase': 'Significant',
            'maintenance_burden': 'Higher',
            'performance_impact': 'Moderate (dual-pass processing)',
            'testing_complexity': 'Much higher'
        },
        'risk_assessment': {
            'technical_risks': [
                'Coordinate alignment accuracy issues',
                'Font mapping errors in complex layouts',
                'Performance degradation'
            ],
            'maintenance_risks': [
                'More complex debugging',
                'Increased test coverage requirements',
                'Dependency on two PDF tools'
            ]
        }
    }

def generate_recommendation():
    """Generate final recommendation for hybrid approach"""
    
    coord_analysis = analyze_coordinate_alignment()
    font_analysis = analyze_font_mapping_feasibility()
    architecture = design_hybrid_architecture()
    complexity = estimate_implementation_complexity()
    benefits_costs = analyze_benefits_vs_costs()
    
    # Calculate feasibility score
    feasibility_score = 0
    
    if coord_analysis and coord_analysis['scale_factor']:
        feasibility_score += 3  # Coordinate alignment is feasible
    
    if font_analysis and font_analysis['feasible']:
        feasibility_score += 2  # Font mapping is feasible
    
    # Calculate benefit/cost ratio
    benefit_impact = sum([
        3 if benefit['impact'] == 'High' else 2 if benefit['impact'] == 'Medium' else 1
        for benefit in benefits_costs['benefits'].values()
    ])
    
    cost_impact = 4  # High complexity and development effort
    
    benefit_cost_ratio = benefit_impact / cost_impact
    
    recommendation = {
        'feasibility_score': feasibility_score,
        'benefit_cost_ratio': benefit_cost_ratio,
        'recommendation': '',
        'reasoning': [],
        'alternative_approaches': []
    }
    
    if feasibility_score >= 4 and benefit_cost_ratio > 1.5:
        recommendation['recommendation'] = 'Implement hybrid approach'
        recommendation['reasoning'] = [
            'High feasibility score indicates technical viability',
            'Benefits significantly outweigh implementation costs',
            'Enhanced categorization capability would improve accuracy'
        ]
    elif feasibility_score >= 3 and benefit_cost_ratio > 1.0:
        recommendation['recommendation'] = 'Consider phased implementation'
        recommendation['reasoning'] = [
            'Moderate feasibility with positive benefit/cost ratio',
            'Implement basic font mapping first',
            'Evaluate results before full implementation'
        ]
    else:
        recommendation['recommendation'] = 'Stick with current pdftotext approach'
        recommendation['reasoning'] = [
            'Implementation complexity outweighs benefits',
            'Current approach already provides good results',
            'Focus efforts on improving existing parser'
        ]
    
    recommendation['alternative_approaches'] = [
        'Enhance current parser with heuristic font size detection',
        'Use machine learning for layout analysis',
        'Implement post-processing font size estimation',
        'Focus on improving function extraction accuracy with current method'
    ]
    
    return recommendation

def main():
    """Main analysis function"""
    print("🔬 Hybrid PDF Processing Approach Analysis")
    print("=" * 60)
    
    # Coordinate alignment analysis
    coord_analysis = analyze_coordinate_alignment()
    if coord_analysis:
        print(f"\n📐 Coordinate System Analysis:")
        print(f"   pdftotext dimensions: {coord_analysis['pdftotext_dimensions']}")
        print(f"   pdftohtml dimensions: {coord_analysis['pdftohtml_dimensions']}")
        print(f"   Scale factors: X={coord_analysis['scale_factor']['x']:.3f}, Y={coord_analysis['scale_factor']['y']:.3f}")
    
    # Font mapping analysis
    font_analysis = analyze_font_mapping_feasibility()
    if font_analysis:
        print(f"\n🎨 Font Mapping Analysis:")
        print(f"   Total font specifications: {font_analysis['total_font_specs']}")
        print(f"   Font mapping feasible: {'✅' if font_analysis['feasible'] else '❌'}")
        if font_analysis['font_usage_samples']:
            print(f"   Sample font usage: {font_analysis['font_usage_samples'][0]}")
    
    # Architecture design
    architecture = design_hybrid_architecture()
    print(f"\n🏗️ Hybrid Architecture Design:")
    print(f"   Approach: {architecture['approach']}")
    print(f"   Processing steps: {len(architecture['processing_steps'])} steps")
    print(f"   Coordinate alignment: {architecture['coordinate_alignment']['method']}")
    
    # Implementation complexity
    complexity = estimate_implementation_complexity()
    print(f"\n⚙️ Implementation Complexity:")
    print(f"   Complexity level: {complexity['complexity_level']}")
    print(f"   Total effort: {complexity['total_effort']}")
    print(f"   Risk factors: {len(complexity['risk_factors'])} identified")
    
    # Benefits vs costs
    benefits_costs = analyze_benefits_vs_costs()
    print(f"\n📊 Benefits vs Costs Analysis:")
    print(f"   Benefits: {len(benefits_costs['benefits'])} categories")
    print(f"   Development time: {benefits_costs['costs']['development_time']}")
    print(f"   Complexity increase: {benefits_costs['costs']['complexity_increase']}")
    
    # Final recommendation
    recommendation = generate_recommendation()
    print(f"\n🎯 Final Recommendation:")
    print(f"   Feasibility score: {recommendation['feasibility_score']}/5")
    print(f"   Benefit/cost ratio: {recommendation['benefit_cost_ratio']:.2f}")
    print(f"   Recommendation: {recommendation['recommendation']}")
    
    print(f"\n💡 Reasoning:")
    for reason in recommendation['reasoning']:
        print(f"     • {reason}")
    
    if recommendation['alternative_approaches']:
        print(f"\n🔄 Alternative Approaches:")
        for i, approach in enumerate(recommendation['alternative_approaches'], 1):
            print(f"     {i}. {approach}")
    
    return recommendation

if __name__ == "__main__":
    main()