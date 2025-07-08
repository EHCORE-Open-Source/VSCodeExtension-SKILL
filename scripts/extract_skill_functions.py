#!/usr/bin/env python3
"""
SKILL Function Extractor
Extracts all SKILL functions from Cadence PDF manuals and creates
structured markdown and JSON references for Claude Code.

Usage: python3 extract_skill_functions.py
"""

import os
import re
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

@dataclass
class SkillFunction:
    """Represents a SKILL function with all its metadata"""
    name: str
    syntax: str
    purpose: str
    arguments: Dict[str, str]
    returns: Dict[str, str]
    examples: List[str]
    category: str
    source_file: str
    description: str = ""
    related_functions: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.related_functions is None:
            self.related_functions = []

class SkillFunctionExtractor:
    """Extracts SKILL functions from PDF manuals"""
    
    def __init__(self, pdf_dir: str, output_dir: str):
        self.pdf_dir = Path(pdf_dir)
        self.output_dir = Path(output_dir)
        self.temp_dir = self.output_dir / "skill_extraction"
        self.functions: Dict[str, SkillFunction] = {}
        self.categories = {
            "sklangref": "Core Language Functions",
            "sklayoutref": "Layout Functions", 
            "skuiref": "User Interface Functions",
            "oceanref": "OCEAN Script Functions",
            "skdevref": "Device Functions",
            "skdfref": "Database Functions",
            "skoopref": "Object-Oriented Programming",
            "skcompref": "Component Functions",
            "skipcref": "IPC Functions",
            "skpcellref": "P-Cell Functions",
            "sktechfile": "Technology File Functions",
            "sktransrefOA": "Translation Functions",
            "verifierSkillRef": "Verification Functions",
            "vivaxlskill": "Visualization Functions",
            "maeSKILLref": "MAE Functions",
            "caiskill": "CAI Functions",
            "rodskillref": "ROD Functions",
            "voltusFIL": "Voltus FIL Functions",
            "voltusFIXL": "Voltus FIXL Functions",
            "skillide": "IDE Functions",
            "sklanguser": "Language User Guide",
            "ocnxl": "Ocean XL Functions"
        }
        
    def setup_directories(self):
        """Create necessary directories"""
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def convert_pdfs_to_text(self) -> List[str]:
        """Convert all PDF files to text using pdftotext and clean artifacts"""
        print("Converting PDFs to text...")
        converted_files = []
        
        for pdf_file in self.pdf_dir.glob("*.pdf"):
            txt_file = self.temp_dir / f"{pdf_file.stem}.txt"
            try:
                result = subprocess.run([
                    "pdftotext", str(pdf_file), str(txt_file)
                ], capture_output=True, text=True, check=True)
                
                # Clean PDF artifacts immediately after conversion
                with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_content = f.read()
                
                cleaned_content = self.clean_pdf_artifacts(raw_content)
                
                with open(txt_file, 'w', encoding='utf-8') as f:
                    f.write(cleaned_content)
                
                converted_files.append(str(txt_file))
                print(f"✓ Converted {pdf_file.name}")
            except subprocess.CalledProcessError as e:
                print(f"✗ Failed to convert {pdf_file.name}: {e}")
                continue
        
        return converted_files
    
    def extract_function_signature(self, text: str, start_pos: int) -> Optional[Tuple[str, str]]:
        """Extract function name and signature from text"""
        # Look for function signature patterns
        patterns = [
            r'^([a-zA-Z][a-zA-Z0-9_]*)\s*\(',  # functionName(
            r'^([a-zA-Z][a-zA-Z0-9_]*)\s*\(\s*$',  # functionName( on separate line
        ]
        
        lines = text[start_pos:start_pos+500].split('\n')
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    func_name = match.group(1)
                    # Try to get full signature
                    signature_lines = []
                    for j in range(i, min(i+5, len(lines))):
                        signature_lines.append(lines[j].strip())
                        if ')' in lines[j]:
                            break
                    signature = ' '.join(signature_lines)
                    return func_name, signature
        return None
    
    def extract_description(self, text: str, start_pos: int) -> str:
        """Extract function description"""
        desc_match = re.search(r'Description\s*(.*?)(?:Arguments|Value Returned|Examples)', 
                              text[start_pos:start_pos+1000], re.DOTALL | re.IGNORECASE)
        if desc_match:
            return desc_match.group(1).strip()
        return ""
    
    def extract_arguments(self, text: str, start_pos: int) -> Dict[str, str]:
        """Extract function arguments"""
        args = {}
        args_match = re.search(r'Arguments\s*(.*?)(?:Value Returned|Examples|Description)', 
                              text[start_pos:start_pos+1500], re.DOTALL | re.IGNORECASE)
        if args_match:
            args_text = args_match.group(1)
            # Parse argument definitions
            arg_lines = args_text.split('\n')
            current_arg = None
            current_desc = []
            
            for line in arg_lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check if this is an argument name (usually starts at beginning of line)
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*$', line):
                    if current_arg:
                        args[current_arg] = ' '.join(current_desc)
                    current_arg = line
                    current_desc = []
                elif current_arg:
                    current_desc.append(line)
            
            if current_arg:
                args[current_arg] = ' '.join(current_desc)
                
        return args
    
    def extract_returns(self, text: str, start_pos: int) -> Dict[str, str]:
        """Extract return value information"""
        returns = {}
        returns_match = re.search(r'Value Returned\s*(.*?)(?:Examples|Related Topics)', 
                                 text[start_pos:start_pos+1000], re.DOTALL | re.IGNORECASE)
        if returns_match:
            returns_text = returns_match.group(1).strip()
            returns["description"] = returns_text
        return returns
    
    def extract_examples(self, text: str, start_pos: int) -> List[str]:
        """Extract function examples"""
        examples = []
        examples_match = re.search(r'Examples\s*(.*?)(?:Related Topics|August|$)', 
                                  text[start_pos:start_pos+2000], re.DOTALL | re.IGNORECASE)
        if examples_match:
            examples_text = examples_match.group(1)
            # Split examples by lines that look like SKILL code
            example_lines = examples_text.split('\n')
            current_example = []
            
            for line in example_lines:
                line = line.strip()
                if not line:
                    if current_example:
                        examples.append('\n'.join(current_example))
                        current_example = []
                    continue
                    
                # If line starts with function call or assignment, it's likely an example
                if (re.match(r'^[a-zA-Z_]', line) and 
                    ('(' in line or '=>' in line or '=' in line)):
                    current_example.append(line)
                elif current_example:
                    current_example.append(line)
            
            if current_example:
                examples.append('\n'.join(current_example))
                
        return examples[:3]  # Limit to 3 examples
    
    def clean_pdf_artifacts(self, text: str) -> str:
        """Remove PDF headers, footers, and other artifacts from extracted text"""
        
        # Split text into lines for easier processing
        lines = text.split('\n')
        cleaned_lines = []
        
        # Define patterns for lines to remove completely
        line_removal_patterns = [
            # Document headers and titles
            r'(?i)cadence\s+.*?\s+reference\s*$',
            r'(?i)product\s+version\s+ic\d+\.\d+\.\d+\s*$',
            r'(?i)(?:august|september|october|november|december|january|february|march|april|may|june|july)\s+\d{4}\s*$',
            
            # Copyright and legal text
            r'©\s*\d{4}\s+cadence\s+design\s+systems.*?$',
            r'(?i)all\s+rights\s+reserved\.?\s*$',
            r'(?i)printed\s+in\s+the\s+united\s+states.*?$',
            
            # Legal boilerplate
            r'(?i)restricted\s+permission:.*?$',
            r'(?i)trademarks:.*?$', 
            r'(?i)disclaimer:.*?$',
            r'(?i)restricted\s+rights:.*?$',
            
            # Page numbers and navigation
            r'^\s*\d+\s*$',  # Standalone page numbers
            r'^\s*\.\s*\..*?\d+\s*$',  # Table of contents with dots
            r'^\s*chapter\s+\d+.*?$',  # Chapter headers
            r'^\s*appendix\s+[a-z].*?$',  # Appendix headers
            
            # Repeated document identifiers
            r'(?i)cadence\s+skill\s+language\s+reference\s*$',
            r'(?i)cadence\s+user\s+interface\s+skill\s+reference\s*$',
            r'(?i)ocean\s+reference\s*$',
            r'(?i)cadence\s+ipc\s+skill\s+reference\s*$',
            
            # Headers/footers that appear on every page
            r'^\s*\d+\s*cadence\s+.*?reference\s*$',
            r'^\s*cadence\s+.*?reference\s*\d+\s*$',
            r'^\s*\d+\s*chapter\s+\d+.*?$',
            r'^\s*chapter\s+\d+.*?\d+\s*$',
            
            # Common footer patterns
            r'^\s*\d+\s*\|\s*.*?$',  # Page number with separator
            r'^\s*.*?\s*\|\s*\d+\s*$',  # Content with page number
            
            # Empty or whitespace-only lines
            r'^\s*$',
            
            # Lines with only punctuation or special characters
            r'^[\s\-_=\*\+\.]+$',
            
            # Date patterns that appear as headers/footers
            r'^\s*\d{1,2}\/\d{1,2}\/\d{2,4}\s*$',
            r'^\s*\d{4}-\d{2}-\d{2}\s*$',
        ]
        
        # Process each line
        for line in lines:
            # Check if line should be removed
            should_remove = False
            for pattern in line_removal_patterns:
                if re.match(pattern, line.strip()):
                    should_remove = True
                    break
            
            if not should_remove:
                # Clean the line but keep it
                cleaned_line = line.strip()
                
                # Remove common artifacts within lines
                text_cleaning_patterns = [
                    # Remove page references like "page 123" at end of line
                    r'\s+page\s+\d+\s*$',
                    # Remove standalone numbers at end of lines
                    r'\s+\d+\s*$',
                    # Remove excessive dots used in table of contents
                    r'\.{3,}',
                ]
                
                for pattern in text_cleaning_patterns:
                    cleaned_line = re.sub(pattern, '', cleaned_line, flags=re.IGNORECASE)
                
                cleaned_line = cleaned_line.strip()
                
                # Only add non-empty lines
                if cleaned_line:
                    cleaned_lines.append(cleaned_line)
        
        # Join lines and perform final cleanup
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Additional multi-line pattern removal
        multiline_patterns = [
            # Remove multi-line legal boilerplate
            r'(?i)restricted\s+permission:.*?successor\.?\s*',
            r'(?i)trademarks:.*?holders\.?\s*',
            r'(?i)disclaimer:.*?information\.?\s*',
            r'(?i)restricted\s+rights:.*?successor\.?\s*',
            
            # Remove document identification blocks
            r'(?i)cadence\s+design\s+systems.*?reference\s*',
            r'(?i)product\s+version.*?august\s+\d{4}\s*',
        ]
        
        for pattern in multiline_patterns:
            cleaned_text = re.sub(pattern, '\n', cleaned_text, flags=re.DOTALL)
        
        # Normalize whitespace
        cleaned_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_text)
        cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)
        
        return cleaned_text.strip()

    def extract_functions_from_text(self, txt_file: str) -> List[SkillFunction]:
        """Extract all functions from a text file"""
        functions = []
        category = Path(txt_file).stem
        
        with open(txt_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Content is already cleaned during PDF conversion
        
        # Find all potential function definitions
        # Look for patterns like function names followed by parentheses
        function_pattern = r'^([a-zA-Z][a-zA-Z0-9_]*)\s*\('
        
        for match in re.finditer(function_pattern, content, re.MULTILINE):
            start_pos = match.start()
            func_info = self.extract_function_signature(content, start_pos)
            
            if not func_info:
                continue
                
            func_name, signature = func_info
            
            # Skip if function name is too generic or common word
            if (len(func_name) < 3 or 
                func_name.lower() in ['the', 'and', 'for', 'are', 'not', 'you', 'can', 'may']):
                continue
            
            # Extract all function metadata
            description = self.extract_description(content, start_pos)
            arguments = self.extract_arguments(content, start_pos)
            returns = self.extract_returns(content, start_pos)
            examples = self.extract_examples(content, start_pos)
            
            # Only add if we have substantial information
            if description or arguments or examples:
                skill_func = SkillFunction(
                    name=func_name,
                    syntax=signature,
                    purpose=description[:200] + "..." if len(description) > 200 else description,
                    arguments=arguments,
                    returns=returns,
                    examples=examples,
                    category=self.categories.get(category, category),
                    source_file=category,
                    description=description
                )
                functions.append(skill_func)
        
        print(f"✓ Extracted {len(functions)} functions from {category}")
        return functions
    
    def process_all_files(self):
        """Process all PDF files and extract functions"""
        print("Processing all PDF files...")
        converted_files = self.convert_pdfs_to_text()
        
        all_functions = []
        for txt_file in converted_files:
            functions = self.extract_functions_from_text(txt_file)
            all_functions.extend(functions)
        
        # Remove duplicates and store in dict
        seen_names = set()
        for func in all_functions:
            if func.name not in seen_names:
                self.functions[func.name] = func
                seen_names.add(func.name)
        
        print(f"✓ Total unique functions extracted: {len(self.functions)}")
    
    def generate_markdown_reference(self):
        """Generate comprehensive markdown reference"""
        print("Generating markdown reference...")
        
        md_content = """# Complete SKILL Function Reference

Auto-generated from all 20 Cadence SKILL PDF manuals.

## Quick Navigation

"""
        
        # Group functions by category
        by_category = defaultdict(list)
        for func in self.functions.values():
            by_category[func.category].append(func)
        
        # Generate table of contents
        md_content += "### Categories\n\n"
        for category in sorted(by_category.keys()):
            func_count = len(by_category[category])
            md_content += f"- [{category}](#{category.lower().replace(' ', '-')}) ({func_count} functions)\n"
        
        md_content += "\n---\n\n"
        
        # Generate detailed sections
        for category in sorted(by_category.keys()):
            md_content += f"## {category}\n\n"
            
            # Sort functions alphabetically within category
            category_functions = sorted(by_category[category], key=lambda x: x.name.lower())
            
            for func in category_functions:
                md_content += f"### `{func.name}`\n\n"
                md_content += f"**Syntax:** `{func.syntax}`\n\n"
                
                if func.purpose:
                    md_content += f"**Purpose:** {func.purpose}\n\n"
                
                if func.arguments:
                    md_content += "**Arguments:**\n"
                    for arg_name, arg_desc in func.arguments.items():
                        md_content += f"- `{arg_name}`: {arg_desc}\n"
                    md_content += "\n"
                
                if func.returns:
                    md_content += "**Returns:**\n"
                    for ret_desc in func.returns.values():
                        md_content += f"- {ret_desc}\n"
                    md_content += "\n"
                
                if func.examples:
                    md_content += "**Examples:**\n"
                    for example in func.examples:
                        md_content += f"```skill\n{example}\n```\n\n"
                
                md_content += f"*Source: {func.source_file}*\n\n"
                md_content += "---\n\n"
        
        # Write to file
        output_file = self.output_dir / "complete-skill-reference.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"✓ Markdown reference written to {output_file}")
    
    def generate_json_database(self):
        """Generate JSON function database"""
        print("Generating JSON database...")
        
        # Convert functions to JSON-serializable format
        functions_dict = {}
        categories_dict = {}
        
        for func_name, func in self.functions.items():
            functions_dict[func_name] = asdict(func)
        
        # Group by category for easier access
        by_category = defaultdict(list)
        for func in self.functions.values():
            by_category[func.category].append(func.name)
            categories_dict[func.category] = {
                "description": f"Functions from {func.source_file}",
                "function_count": len(by_category[func.category])
            }
        
        # Create complete database
        database = {
            "metadata": {
                "total_functions": len(self.functions),
                "total_categories": len(by_category),
                "source_files": list(self.categories.keys()),
                "generated_by": "SKILL Function Extractor for Claude Code"
            },
            "functions": functions_dict,
            "categories": dict(categories_dict),
            "by_category": dict(by_category)
        }
        
        # Write to file
        output_file = self.output_dir / "complete-skill-functions.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(database, f, indent=2, ensure_ascii=False)
        
        print(f"✓ JSON database written to {output_file}")
    
    def generate_quick_reference(self):
        """Generate quick reference for commonly used functions"""
        print("Generating quick reference...")
        
        # Define commonly used functions
        common_functions = [
            'createDir', 'createDirHier', 'deleteDir', 'isDir', 'isFile',
            'dbOpenCellViewByType', 'dbCreateInst', 'dbCreateNet', 'dbSave',
            'printf', 'sprintf', 'strcat', 'substring', 'parseString',
            'list', 'append', 'length', 'nth', 'member', 'car', 'cdr',
            'let', 'if', 'when', 'unless', 'foreach', 'mapcar',
            'procedure', 'defun', 'lambda'
        ]
        
        md_content = """# SKILL Quick Reference

Most commonly used SKILL functions with syntax and examples.

"""
        
        for func_name in common_functions:
            if func_name in self.functions:
                func = self.functions[func_name]
                md_content += f"## `{func.name}`\n\n"
                md_content += f"**Syntax:** `{func.syntax}`\n\n"
                md_content += f"**Purpose:** {func.purpose}\n\n"
                
                if func.examples:
                    md_content += "**Example:**\n"
                    md_content += f"```skill\n{func.examples[0]}\n```\n\n"
                
                md_content += "---\n\n"
        
        # Write to file
        output_file = self.output_dir / "skill-quick-reference.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"✓ Quick reference written to {output_file}")
    
    def run(self):
        """Run the complete extraction process"""
        print("Starting SKILL Function Extraction...")
        print(f"PDF Directory: {self.pdf_dir}")
        print(f"Output Directory: {self.output_dir}")
        print("-" * 50)
        
        self.setup_directories()
        self.process_all_files()
        self.generate_markdown_reference()
        self.generate_json_database()
        self.generate_quick_reference()
        
        print("-" * 50)
        print("✓ Extraction complete!")
        print(f"Total functions extracted: {len(self.functions)}")
        print(f"Files generated in: {self.output_dir}")

def main():
    pdf_dir = "/mnt/d/git/skillRef"
    output_dir = "/mnt/d/git/VSCodeExtension-SKILL/docs"
    
    if not os.path.exists(pdf_dir):
        print(f"Error: PDF directory {pdf_dir} not found")
        sys.exit(1)
    
    extractor = SkillFunctionExtractor(pdf_dir, output_dir)
    extractor.run()

if __name__ == "__main__":
    main()