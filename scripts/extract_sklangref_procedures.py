#!/usr/bin/env python3
"""
SKILL Language Reference Procedure Extractor
Extracts all 474 procedures from sklangref.txt and generates universal-procedures.json
with proper chapter categorization.
"""

import re
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

class SkillProcedureExtractor:
    def __init__(self, input_file: str):
        self.input_file = input_file
        self.procedures = {}
        self.chapters = {}
        self.current_chapter = None
        self.current_chapter_num = 0
        
        # Chapter mapping
        self.chapter_mapping = {
            1: "List Functions",
            2: "Data Structures", 
            3: "Data Operator Functions",
            4: "Type Conversion Functions",
            5: "String Functions",
            6: "Arithmetic Functions",
            7: "Bitwise Operator Functions",
            8: "Trigonometric Functions",
            9: "Logical and Relational Functions",
            10: "Flow Control Functions",
            11: "Input Output Functions",
            12: "Core Functions",
            13: "Function and Program Structure",
            14: "Environment Functions",
            15: "Namespace Functions",
            16: "Scheme/SKILL++ Equivalents Tables",
            17: "Mapping Symbols to Values",
            18: "setf Helper Functions",
            19: "Type Introspection Functions",
            20: "The Standalone skill Program"
        }

    def extract_parameter_info(self, param_line: str) -> Tuple[str, str, bool]:
        """Extract parameter name, type, and optional status from parameter line."""
        param_line = param_line.strip()
        
        # Check if optional
        is_optional = param_line.startswith('[') and param_line.endswith(']')
        if is_optional:
            param_line = param_line[1:-1].strip()
        
        # Extract type prefix and name
        if '_' in param_line:
            parts = param_line.split('_', 1)
            if len(parts) == 2:
                type_prefix = parts[0]
                param_name = parts[1]
            else:
                type_prefix = "g"
                param_name = param_line
        else:
            type_prefix = "g"
            param_name = param_line
        
        # Map type prefixes to readable types
        type_map = {
            'l': 'list',
            't': 'string',
            'g': 'any',
            's': 'symbol',
            'x': 'integer',
            'n': 'number',
            'p': 'port',
            'o': 'object',
            'f': 'function',
            'r': 'real'
        }
        
        param_type = type_map.get(type_prefix, 'any')
        
        return param_name, param_type, is_optional

    def parse_procedure_definition(self, lines: List[str], start_idx: int) -> Optional[Dict[str, Any]]:
        """Parse a single procedure definition starting at the given index."""
        if start_idx >= len(lines):
            return None
        
        # Find procedure name
        name_line = lines[start_idx].strip()
        if not name_line or name_line.startswith('Description'):
            return None
        
        procedure_name = name_line
        
        # Find syntax definition
        syntax_start = start_idx + 1
        while syntax_start < len(lines) and not lines[syntax_start].strip().startswith(procedure_name + '('):
            syntax_start += 1
        
        if syntax_start >= len(lines):
            return None
        
        # Extract parameters
        parameters = []
        param_idx = syntax_start
        while param_idx < len(lines) and not lines[param_idx].strip().startswith(')'):
            line = lines[param_idx].strip()
            if line and not line.startswith(procedure_name + '(') and not line.startswith(')'):
                if not line.startswith('=>'):
                    param_name, param_type, is_optional = self.extract_parameter_info(line)
                    if param_name:
                        parameters.append({
                            'name': param_name,
                            'type': param_type,
                            'optional': is_optional
                        })
            param_idx += 1
        
        # Find return type
        return_type = 'any'
        return_idx = param_idx
        while return_idx < len(lines) and not lines[return_idx].strip().startswith('=>'):
            return_idx += 1
        
        if return_idx < len(lines):
            return_line = lines[return_idx].strip()
            if return_line.startswith('=>'):
                return_type = return_line[2:].strip()
        
        # Find description
        desc_start = return_idx + 1
        while desc_start < len(lines) and lines[desc_start].strip() != 'Description':
            desc_start += 1
        
        description = ""
        if desc_start < len(lines):
            desc_idx = desc_start + 1
            while desc_idx < len(lines) and not lines[desc_idx].strip().startswith('Arguments'):
                if lines[desc_idx].strip():
                    description += lines[desc_idx].strip() + " "
                desc_idx += 1
        
        # Find arguments section
        args_docs = {}
        arg_start = desc_idx if 'desc_idx' in locals() else desc_start
        while arg_start < len(lines) and lines[arg_start].strip() != 'Arguments':
            arg_start += 1
        
        if arg_start < len(lines):
            arg_idx = arg_start + 1
            current_arg = None
            while arg_idx < len(lines) and not lines[arg_idx].strip().startswith('Value Returned'):
                line = lines[arg_idx].strip()
                if line:
                    # Check if this is a new argument
                    if not line.startswith(' ') and '_' in line:
                        current_arg = line.split('_')[-1] if '_' in line else line
                        args_docs[current_arg] = ""
                    elif current_arg:
                        args_docs[current_arg] += line + " "
                arg_idx += 1
        
        # Find return value documentation
        return_doc = ""
        ret_start = arg_idx if 'arg_idx' in locals() else arg_start
        while ret_start < len(lines) and lines[ret_start].strip() != 'Value Returned':
            ret_start += 1
        
        if ret_start < len(lines):
            ret_idx = ret_start + 1
            while ret_idx < len(lines) and not lines[ret_idx].strip().startswith('Examples'):
                if lines[ret_idx].strip():
                    return_doc += lines[ret_idx].strip() + " "
                ret_idx += 1
        
        # Find examples
        examples = []
        ex_start = ret_idx if 'ret_idx' in locals() else ret_start
        while ex_start < len(lines) and lines[ex_start].strip() != 'Examples':
            ex_start += 1
        
        if ex_start < len(lines):
            ex_idx = ex_start + 1
            current_example = ""
            while ex_idx < len(lines) and not lines[ex_idx].strip().startswith('Related Topics'):
                line = lines[ex_idx].strip()
                if line:
                    current_example += line + "\n"
                elif current_example:
                    examples.append(current_example.strip())
                    current_example = ""
                ex_idx += 1
            
            if current_example:
                examples.append(current_example.strip())
        
        # Generate syntax string
        param_strings = []
        for param in parameters:
            if param['optional']:
                param_strings.append(f"[{param['name']}]")
            else:
                param_strings.append(param['name'])
        
        syntax = f"{procedure_name}({' '.join(param_strings)})"
        
        # Convert parameters to expected format
        doc_parameters = []
        for param in parameters:
            doc_parameters.append({
                'name': param['name'],
                'type': param['type'],
                'required': not param['optional'],
                'description': args_docs.get(param['name'], f"Parameter {param['name']}")
            })
        
        return {
            'name': procedure_name,
            'scope': 'universal',
            'category': self.current_chapter,
            'source': 'SKILL Language Reference',
            'availability': [{
                'scope': 'universal',
                'version_range': {
                    'pattern': '*',
                    'description': 'Available in all SKILL implementations'
                }
            }],
            'documentation': {
                'syntax': syntax,
                'summary': description.strip(),
                'parameters': doc_parameters,
                'return_value': return_doc.strip() if return_doc.strip() else f"Returns {return_type}",
                'examples': examples,
                'notes': f"Chapter {self.current_chapter_num}: {self.current_chapter}"
            }
        }

    def detect_chapter(self, line: str) -> Optional[Tuple[int, str]]:
        """Detect chapter headers and return chapter number and title."""
        line = line.strip()
        
        # Pattern for chapter headers like "Chapter 1 List Functions"
        chapter_pattern = r'^Chapter\s+(\d+)\s+(.+)$'
        match = re.match(chapter_pattern, line)
        if match:
            chapter_num = int(match.group(1))
            chapter_title = match.group(2).strip()
            return chapter_num, chapter_title
        
        # Alternative patterns for section headers
        for num, title in self.chapter_mapping.items():
            if title.lower() in line.lower() and len(line) < 100:
                return num, title
        
        return None

    def parse_sklangref_file(self) -> Dict[str, Any]:
        """Parse the entire sklangref.txt file."""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        i = 0
        procedure_count = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for chapter headers
            chapter_info = self.detect_chapter(line)
            if chapter_info:
                self.current_chapter_num, self.current_chapter = chapter_info
                print(f"Found Chapter {self.current_chapter_num}: {self.current_chapter}")
            
            # Look for procedure definitions
            if (line and not line.startswith('#') and not line.startswith('Chapter') 
                and not line.startswith('Description') and not line.startswith('Arguments')
                and not line.startswith('Value Returned') and not line.startswith('Examples')
                and not line.startswith('Related Topics') and len(line) < 50
                and self.current_chapter):
                
                # Check if next few lines contain procedure syntax
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line.startswith(line + '(') or (i + 2 < len(lines) and lines[i + 2].strip().startswith(line + '(')):
                        procedure = self.parse_procedure_definition(lines, i)
                        if procedure:
                            self.procedures[procedure['name']] = procedure
                            procedure_count += 1
                            print(f"Extracted: {procedure['name']} ({self.current_chapter})")
            
            i += 1
        
        print(f"\nTotal procedures extracted: {procedure_count}")
        return self.generate_json_output()

    def generate_json_output(self) -> Dict[str, Any]:
        """Generate the final JSON structure."""
        categories = list(set(proc['category'] for proc in self.procedures.values() if proc['category']))
        
        return {
            'metadata': {
                'category': 'Universal SKILL Functions',
                'scope': 'universal',
                'description': 'Complete SKILL language functions (sklangref) available in all tools and versions',
                'version': '3.0.0',
                'total_functions': len(self.procedures),
                'categories': sorted(categories),
                'source_reference': 'sklangref - SKILL Language Reference IC6.1.8',
                'last_updated': datetime.now().strftime('%Y-%m-%d'),
                'chapters': self.chapter_mapping
            },
            'procedures': self.procedures
        }

def main():
    input_file = '/mnt/d/git/VSCodeExtension-SKILL/docs/skill_extraction/sklangref.txt'
    output_file = '/mnt/d/git/VSCodeExtension-SKILL/docs/skill_extraction/universal-procedures-new.json'
    
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found")
        return
    
    extractor = SkillProcedureExtractor(input_file)
    result = extractor.parse_sklangref_file()
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\nExtraction complete! Output saved to: {output_file}")
    print(f"Total procedures: {result['metadata']['total_functions']}")
    print(f"Categories: {len(result['metadata']['categories'])}")

if __name__ == '__main__':
    main()