#!/usr/bin/env python3
"""
Enhanced SKILL function extraction script integrating the PDF/HTML parser
Replaces extract_skill_functions.py with comprehensive parsing capabilities
"""

import os
import sys
import argparse
import json
import glob
from pathlib import Path
from typing import List, Dict, Set, Optional

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skill_pdf_html_parser import SkillPDFHTMLParser, SkillFunctionWithOverloads

class EnhancedSkillExtractor:
    """Enhanced SKILL function extractor using PDF/HTML parser"""
    
    def __init__(self, output_dir: str = "docs/skill_extraction"):
        self.output_dir = output_dir
        self.parser = SkillPDFHTMLParser()
        self.ensure_output_directory()
        
    def ensure_output_directory(self):
        """Ensure output directory exists"""
        os.makedirs(self.output_dir, exist_ok=True)
        
    def extract_from_pdf_directory(self, pdf_dir: str, force_reconvert: bool = False) -> Dict[str, List[SkillFunctionWithOverloads]]:
        """Extract functions from all PDFs in directory"""
        
        pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in {pdf_dir}")
            return {}
            
        print(f"Found {len(pdf_files)} PDF files to process")
        
        all_results = {}
        total_functions = 0
        
        for pdf_file in sorted(pdf_files):
            print(f"\nProcessing: {os.path.basename(pdf_file)}")
            
            # Convert PDF to HTML
            html_file = pdf_file.replace('.pdf', '.html')
            
            if force_reconvert or not os.path.exists(html_file):
                print(f"  Converting PDF to HTML...")
                if not self.parser.convert_pdf_to_html(pdf_file, html_file):
                    print(f"  ❌ Failed to convert {pdf_file}")
                    continue
                    
            # Parse HTML content
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                    
                document_name = self._extract_document_name(os.path.basename(pdf_file))
                functions = self.parser.parse_html_content(html_content, document_name)
                
                all_results[os.path.basename(pdf_file)] = functions
                total_functions += len(functions)
                
                print(f"  ✅ Extracted {len(functions)} functions")
                
                # Show breakdown by special types
                special_counts = self._count_special_functions(functions)
                if any(special_counts.values()):
                    print(f"     Special functions: {special_counts}")
                    
            except Exception as e:
                print(f"  ❌ Error parsing {html_file}: {e}")
                continue
                
        print(f"\n🎉 Total functions extracted: {total_functions}")
        return all_results
        
    def _extract_document_name(self, filename: str) -> str:
        """Extract readable document name from filename"""
        # Remove extension and clean up
        name = os.path.splitext(filename)[0]
        
        # Common SKILL document mappings
        name_mappings = {
            'sklangref': 'Cadence SKILL Language Reference',
            'skipcref': 'SKILL IPC Reference',
            'ocnxl': 'OCEAN XL Reference',
            'virtuoso': 'Virtuoso Reference',
            'dfii': 'Design Framework II Reference'
        }
        
        # Check for known mappings
        for key, display_name in name_mappings.items():
            if key in name.lower():
                return display_name
                
        # Default: capitalize and clean up
        return name.replace('_', ' ').replace('-', ' ').title()
        
    def _count_special_functions(self, functions: List[SkillFunctionWithOverloads]) -> Dict[str, int]:
        """Count special function types"""
        counts = {
            'car_cdr_series': 0,
            'vi_series': 0, 
            'template_functions': 0,
            'multi_overload': 0
        }
        
        for func in functions:
            if func.special_type == 'car_cdr_series':
                counts['car_cdr_series'] += 1
            elif func.special_type == 'vi_series':
                counts['vi_series'] += 1
            elif func.special_type == 'template_function':
                counts['template_functions'] += 1
                
            if len(func.overloads) > 1:
                counts['multi_overload'] += 1
                
        return counts
        
    def save_individual_results(self, all_results: Dict[str, List[SkillFunctionWithOverloads]]):
        """Save individual JSON files for each document"""
        
        for pdf_name, functions in all_results.items():
            output_file = os.path.join(self.output_dir, f"{os.path.splitext(pdf_name)[0]}_enhanced.json")
            self.parser.save_results(functions, output_file)
            print(f"Saved {len(functions)} functions to {output_file}")
            
    def create_combined_database(self, all_results: Dict[str, List[SkillFunctionWithOverloads]]) -> Dict:
        """Create combined function database"""
        
        combined_functions = []
        document_stats = {}
        
        for pdf_name, functions in all_results.items():
            combined_functions.extend(functions)
            
            # Document statistics
            special_counts = self._count_special_functions(functions)
            document_stats[pdf_name] = {
                'total_functions': len(functions),
                'functions_with_overloads': len([f for f in functions if len(f.overloads) > 1]),
                'functions_with_categories': len([f for f in functions if f.category]),
                'special_function_counts': special_counts
            }
            
        # Remove duplicates by function name (keep first occurrence)
        seen_names = set()
        unique_functions = []
        
        for func in combined_functions:
            if func.name not in seen_names:
                unique_functions.append(func)
                seen_names.add(func.name)
                
        # Create combined database structure
        combined_db = {
            'metadata': {
                'parser_version': '1.0.0',
                'total_documents': len(all_results),
                'total_functions': len(unique_functions),
                'unique_function_names': len(seen_names),
                'extraction_timestamp': __import__('datetime').datetime.now().isoformat(),
                'document_statistics': document_stats,
                'global_statistics': {
                    'functions_with_multiple_overloads': len([f for f in unique_functions if len(f.overloads) > 1]),
                    'functions_with_categories': len([f for f in unique_functions if f.category]),
                    'special_function_totals': self._count_special_functions(unique_functions)
                }
            },
            'functions': [self._serialize_function(func) for func in unique_functions]
        }
        
        return combined_db
        
    def _serialize_function(self, func: SkillFunctionWithOverloads) -> Dict:
        """Serialize function to dictionary format"""
        from dataclasses import asdict
        
        func_data = asdict(func)
        
        # Convert enums to strings
        for overload in func_data['overloads']:
            for param in overload['parameters']:
                if hasattr(param['param_type'], 'value'):
                    param['param_type'] = param['param_type'].value
                else:
                    param['param_type'] = str(param['param_type'])
                    
        return func_data
        
    def save_combined_database(self, combined_db: Dict, filename: str = "complete-skill-functions-enhanced.json"):
        """Save combined database to file"""
        
        output_file = os.path.join(self.output_dir, filename)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(combined_db, f, indent=2, ensure_ascii=False)
            
        print(f"\n📋 Combined database saved to: {output_file}")
        print(f"   Total unique functions: {combined_db['metadata']['total_functions']}")
        print(f"   Documents processed: {combined_db['metadata']['total_documents']}")
        
        # Print global statistics
        global_stats = combined_db['metadata']['global_statistics']
        print(f"   Functions with multiple overloads: {global_stats['functions_with_multiple_overloads']}")
        print(f"   Functions with categories: {global_stats['functions_with_categories']}")
        print(f"   Special function totals: {global_stats['special_function_totals']}")
        
    def create_quick_reference(self, combined_db: Dict):
        """Create quick reference markdown file"""
        
        functions = combined_db['functions']
        metadata = combined_db['metadata']
        
        # Sort functions by name
        functions.sort(key=lambda f: f['name'].lower())
        
        # Create quick reference content
        content = [
            "# SKILL Functions Quick Reference (Enhanced)",
            "",
            f"**Generated:** {metadata['extraction_timestamp'][:19]}",
            f"**Total Functions:** {metadata['total_functions']}",
            f"**Documents Processed:** {metadata['total_documents']}",
            "",
            "## Function Categories",
            ""
        ]
        
        # Group by categories
        categorized_functions = {}
        uncategorized_functions = []
        
        for func in functions:
            if func.get('category') and func['category'].get('full_path'):
                category_path = func['category']['full_path']
                if category_path not in categorized_functions:
                    categorized_functions[category_path] = []
                categorized_functions[category_path].append(func)
            else:
                uncategorized_functions.append(func)
                
        # Add categorized functions
        for category_path in sorted(categorized_functions.keys()):
            content.append(f"### {category_path}")
            content.append("")
            
            category_funcs = categorized_functions[category_path]
            for func in sorted(category_funcs, key=lambda f: f['name'].lower()):
                overload_count = len(func['overloads'])
                overload_text = f" ({overload_count} overloads)" if overload_count > 1 else ""
                special_text = f" *[{func['special_type']}]*" if func.get('special_type') else ""
                
                content.append(f"- **{func['name']}**{overload_text}{special_text}")
                if func.get('description'):
                    desc = func['description'][:100] + "..." if len(func['description']) > 100 else func['description']
                    content.append(f"  {desc}")
                content.append("")
                
        # Add uncategorized functions
        if uncategorized_functions:
            content.extend([
                "### Uncategorized Functions",
                ""
            ])
            
            for func in sorted(uncategorized_functions, key=lambda f: f['name'].lower()):
                overload_count = len(func['overloads'])
                overload_text = f" ({overload_count} overloads)" if overload_count > 1 else ""
                special_text = f" *[{func['special_type']}]*" if func.get('special_type') else ""
                
                content.append(f"- **{func['name']}**{overload_text}{special_text}")
                
        # Add statistics section
        content.extend([
            "",
            "## Statistics",
            "",
            f"- **Total Functions:** {metadata['total_functions']}",
            f"- **Functions with Multiple Overloads:** {metadata['global_statistics']['functions_with_multiple_overloads']}",
            f"- **Functions with Categories:** {metadata['global_statistics']['functions_with_categories']}",
            ""
        ])
        
        # Add special functions breakdown
        special_totals = metadata['global_statistics']['special_function_totals']
        if any(special_totals.values()):
            content.extend([
                "### Special Function Types",
                "",
                f"- **Car/CDR Series:** {special_totals['car_cdr_series']}",
                f"- **VI Series:** {special_totals['vi_series']}",
                f"- **Template Functions:** {special_totals['template_functions']}",
                ""
            ])
            
        # Save quick reference
        output_file = os.path.join(self.output_dir, "skill-quick-reference-enhanced.md")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
            
        print(f"📖 Quick reference saved to: {output_file}")

def main():
    """Main entry point for enhanced extraction"""
    
    parser = argparse.ArgumentParser(description='Enhanced SKILL Function Extractor')
    parser.add_argument('pdf_directory', help='Directory containing SKILL PDF files')
    parser.add_argument('-o', '--output-dir', default='docs/skill_extraction', 
                       help='Output directory for extracted data')
    parser.add_argument('--force-reconvert', action='store_true', 
                       help='Force reconversion of PDFs to HTML')
    parser.add_argument('--individual-only', action='store_true',
                       help='Only save individual JSON files, skip combined database')
    parser.add_argument('--no-quick-reference', action='store_true',
                       help='Skip creating quick reference markdown')
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.pdf_directory):
        print(f"Error: PDF directory '{args.pdf_directory}' does not exist")
        return 1
        
    # Initialize extractor
    extractor = EnhancedSkillExtractor(args.output_dir)
    
    # Extract from all PDFs
    print("🚀 Starting enhanced SKILL function extraction...")
    all_results = extractor.extract_from_pdf_directory(args.pdf_directory, args.force_reconvert)
    
    if not all_results:
        print("❌ No functions extracted from any documents")
        return 1
        
    # Save individual results
    print("\n💾 Saving individual document results...")
    extractor.save_individual_results(all_results)
    
    # Create and save combined database
    if not args.individual_only:
        print("\n🔗 Creating combined database...")
        combined_db = extractor.create_combined_database(all_results)
        extractor.save_combined_database(combined_db)
        
        # Create quick reference
        if not args.no_quick_reference:
            print("\n📚 Creating quick reference...")
            extractor.create_quick_reference(combined_db)
            
    print("\n✅ Enhanced extraction complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())