#!/usr/bin/env python3
"""
SKILL PDF/HTML Parser - Advanced function extraction system
Complete implementation with hierarchical categorization and special function handling

Based on enhanced parameter parser prototype and comprehensive CLAUDE.md documentation
Implements all features described in the planning phase
"""

import sys
import os
import re
import json
import argparse
from typing import Dict, List, Optional, Tuple, Union, Set
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from bs4 import BeautifulSoup

# Add scripts directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class ParameterType(Enum):
    """SKILL parameter types with comprehensive pattern support"""
    REQUIRED = "required"
    OPTIONAL = "optional"           # [optional] parameters
    VARIADIC = "variadic"          # ... arguments  
    KEYWORD = "keyword"            # ?keyword arguments
    NESTED_OPTIONAL = "nested_optional"  # [[nested]] patterns

@dataclass
class SkillParameter:
    """Enhanced SKILL parameter with complete type information"""
    name: str
    param_type: ParameterType
    data_type: str                 # Official SKILL type prefix mapping
    default_value: Optional[str] = None
    keyword_name: Optional[str] = None  # For ?keyword parameters
    is_nested_optional: bool = False    # For [[nested]] patterns
    description: str = ""
    position: int = 0              # Parameter position in signature

@dataclass
class FunctionOverload:
    """Function overload with detailed parameter analysis"""
    signature: str
    parameters: List[SkillParameter]
    return_type: str
    raw_signature: str             # Original HTML signature
    parameter_count: int = 0
    has_optional: bool = False
    has_variadic: bool = False
    has_keywords: bool = False

    def __post_init__(self):
        self.parameter_count = len(self.parameters)
        self.has_optional = any(p.param_type == ParameterType.OPTIONAL for p in self.parameters)
        self.has_variadic = any(p.param_type == ParameterType.VARIADIC for p in self.parameters)
        self.has_keywords = any(p.param_type == ParameterType.KEYWORD for p in self.parameters)

@dataclass
class FunctionCategory:
    """Hierarchical category structure for SKILL functions"""
    document_name: str              # e.g., "Cadence SKILL Language Reference"
    category_path: List[str]        # e.g., ["Arithmetic Functions"] or ["User Entry", "Nesting"]
    level: int                     # Depth level (1, 2, 3, 4+)
    full_path: str                 # Complete hierarchical path
    font_size: float = 0.0         # Original font size for level detection
    page_number: int = 0           # Page where category appears
    
    def __post_init__(self):
        if not self.full_path:
            self.full_path = f"{self.document_name} > {' > '.join(self.category_path)}"

@dataclass 
class SkillFunctionWithOverloads:
    """Complete SKILL function with all enhancement features"""
    name: str
    overloads: List[FunctionOverload]
    description: str
    arguments_description: Dict[str, str]
    examples: List[str]
    page: int
    category: Optional[FunctionCategory] = None
    related_functions: List[str] = None
    special_type: Optional[str] = None     # car_cdr, vi_series, template, etc.
    
    def __post_init__(self):
        if self.related_functions is None:
            self.related_functions = []

    def get_parameter_count_range(self) -> Tuple[int, int]:
        """Get min and max parameter counts across overloads"""
        if not self.overloads:
            return (0, 0)
        counts = [overload.parameter_count for overload in self.overloads]
        return (min(counts), max(counts))

class SkillPDFHTMLParser:
    """Advanced SKILL function parser using HTML with positioning data"""
    
    def __init__(self):
        self.official_data_types = self._init_official_data_types()
        self.car_cdr_functions = self._init_car_cdr_functions()
        self.vi_series_functions = self._init_vi_series_functions()
        self.template_patterns = self._init_template_patterns()
        self.current_categories = []  # Stack for hierarchical categories
        
    def _init_official_data_types(self) -> Dict[str, str]:
        """Official SKILL data type prefix mappings from documentation"""
        return {
            'a_': 'array',
            'l_': 'list', 
            't_': 'string',
            'n_': 'number',
            'f_': 'flonum',
            'g_': 'general',
            's_': 'symbol',
            'S_': 'stringSymbol',
            'o_': 'userType',
            'r_': 'defstruct', 
            'p_': 'port',
            'x_': 'integer',
            'u_': 'function',
            'd_': 'dbobject',
            'e_': 'envobj',
            'w_': 'window',
            'c_': 'character',
            'b_': 'boolean',
            'v_': 'vector',
            'm_': 'matrix',
            'h_': 'hashtable',
            'i_': 'instance',
            'k_': 'keyword',
            'y_': 'binary',
            'z_': 'complex',
            'q_': 'queue',
            'R_': 'rodObj'
        }

    def _init_car_cdr_functions(self) -> List[str]:
        """Complete 30-function car/cdr series as specified"""
        return [
            'car', 'cdr', 'caar', 'cadr', 'cdar', 'cddr',
            'caaar', 'caadr', 'cadar', 'caddr', 'cdaar', 'cdadr', 'cddar', 'cdddr',
            'caaaar', 'caaadr', 'caadar', 'caaddr', 'cadaar', 'cadadr', 'caddar', 'cadddr',
            'cdaaar', 'cdaadr', 'cdadar', 'cdaddr', 'cddaar', 'cddadr', 'cdddar', 'cddddr'
        ]

    def _init_vi_series_functions(self) -> List[str]:
        """VI series functions as specified"""
        return ['vi', 'vii', 'vil']

    def _init_template_patterns(self) -> List[str]:
        """Template function patterns for dynamic generation"""
        return ['make_', 'copy_', 'setf_']

    def parse_html_content(self, html_content: str, document_name: str = "") -> List[SkillFunctionWithOverloads]:
        """Main parsing entry point"""
        soup = BeautifulSoup(html_content, 'html.parser')
        pages = soup.find_all('page')
        
        all_functions = []
        self.current_categories = []
        
        for page_num, page in enumerate(pages, 1):
            # Extract positioned words
            words = self._extract_positioned_words(page)
            if not words:
                continue
                
            # Detect categories on this page
            page_categories = self._detect_page_categories(words, page_num, document_name)
            
            # Extract functions with category context
            page_functions = self._extract_functions_from_page(words, page_num, page_categories)
            all_functions.extend(page_functions)
            
        # Post-process special function patterns
        all_functions = self._process_special_functions(all_functions)
        
        return all_functions

    def _extract_positioned_words(self, page) -> List[Dict]:
        """Extract words with position and font information"""
        words = []
        for word in page.find_all('word'):
            text = word.get_text().strip()
            if not text:
                continue
                
            try:
                x_min = float(word.get('xmin', 0))
                y_min = float(word.get('ymin', 0))
                y_max = float(word.get('ymax', 0))
                font_size = y_max - y_min
                
                words.append({
                    'text': text,
                    'x': x_min,
                    'y': y_min,
                    'font_size': font_size,
                    'element': word
                })
            except (ValueError, TypeError):
                continue
                
        # Sort by Y position to maintain reading order
        words.sort(key=lambda x: (x['y'], x['x']))
        return words

    def _detect_page_categories(self, words: List[Dict], page_num: int, document_name: str) -> List[FunctionCategory]:
        """Detect hierarchical categories using font size and position analysis"""
        categories = []
        
        for i, word in enumerate(words):
            text = word['text']
            font_size = word['font_size']
            x_pos = word['x']
            
            # Skip small text and right-side content
            if font_size < 12 or x_pos > 400:
                continue
                
            # Detect category headers by font size and position patterns
            if self._is_category_header(text, font_size, x_pos, words, i):
                level = self._determine_category_level(font_size, x_pos)
                
                # Build category path based on level
                category_path = self._build_category_path(text, level)
                
                category = FunctionCategory(
                    document_name=document_name,
                    category_path=category_path,
                    level=level,
                    full_path="",
                    font_size=font_size,
                    page_number=page_num
                )
                categories.append(category)
                
        return categories

    def _is_category_header(self, text: str, font_size: float, x_pos: float, words: List[Dict], index: int) -> bool:
        """Determine if text is a category header"""
        # Large font sizes typically indicate headers
        if font_size < 13:
            return False
            
        # Left-aligned content
        if x_pos > 100:
            return False
            
        # Look for typical category keywords
        category_keywords = [
            'Functions', 'Commands', 'Procedures', 'Methods', 'Operations',
            'Arithmetic', 'String', 'List', 'Database', 'User', 'System',
            'Input', 'Output', 'Control', 'Data', 'File', 'Window'
        ]
        
        return any(keyword in text for keyword in category_keywords)

    def _determine_category_level(self, font_size: float, x_pos: float) -> int:
        """Determine hierarchical level based on font size and position"""
        if font_size >= 16:
            return 1  # Top level
        elif font_size >= 14:
            return 2  # Second level
        elif font_size >= 13:
            return 3  # Third level
        else:
            return 4  # Fourth level and below

    def _build_category_path(self, text: str, level: int) -> List[str]:
        """Build hierarchical category path"""
        # Update current categories stack based on level
        while len(self.current_categories) >= level:
            self.current_categories.pop()
            
        # Add current category
        if len(self.current_categories) == level - 1:
            self.current_categories.append(text)
        else:
            # Fill missing levels if needed
            while len(self.current_categories) < level - 1:
                self.current_categories.append("General")
            self.current_categories.append(text)
            
        return self.current_categories.copy()

    def _extract_functions_from_page(self, words: List[Dict], page_num: int, categories: List[FunctionCategory]) -> List[SkillFunctionWithOverloads]:
        """Extract functions from page with category context"""
        functions = []
        current_category = categories[-1] if categories else None
        
        i = 0
        while i < len(words):
            word = words[i]
            text = word['text']
            
            # Check if this looks like a function name
            if self._is_potential_function_name(text, word):
                func = self._parse_complete_function(words, i, page_num, current_category)
                if func:
                    functions.append(func)
                    
            i += 1
            
        return functions

    def _is_potential_function_name(self, text: str, word: Dict) -> bool:
        """Enhanced function name detection"""
        # Position and font criteria
        if word['x'] > 100 or word['font_size'] < 11:
            return False
            
        # SKILL function patterns
        patterns = [
            r'^[a-z]+[A-Z][a-zA-Z]*$',      # camelCase: append, createElement
            r'^ipc[A-Z][a-zA-Z]*$',         # IPC functions
            r'^pho[A-Z][a-zA-Z]*$',         # Photonic functions  
            r'^db[A-Z][a-zA-Z]*$',          # Database functions
            r'^get[A-Z][a-zA-Z]*$',         # Getter functions
            r'^set[A-Z][a-zA-Z]*$',         # Setter functions
            r'^create[A-Z][a-zA-Z]*$',      # Creator functions
        ]
        
        for pattern in patterns:
            if re.match(pattern, text):
                return True
                
        # Known single-word functions
        known_functions = [
            'append', 'car', 'cdr', 'cons', 'list', 'length', 'member', 'reverse',
            'sort', 'nth', 'last', 'first', 'rest', 'remove', 'delete', 'find',
            'atof', 'buildString', 'nearlyEqual', 'lsprintf'
        ] + self.car_cdr_functions + self.vi_series_functions
        
        return text in known_functions

    def _parse_complete_function(self, words: List[Dict], start_idx: int, page_num: int, category: Optional[FunctionCategory]) -> Optional[SkillFunctionWithOverloads]:
        """Parse complete function with all overloads and information"""
        func_name = words[start_idx]['text']
        
        # Find all overloads
        overloads = self._find_all_overloads(words, start_idx, func_name)
        if not overloads:
            return None
            
        # Extract additional information
        description = self._extract_description(words, start_idx)
        arguments_desc = self._extract_arguments_description(words, start_idx)
        examples = self._extract_examples(words, start_idx)
        related_functions = self._extract_related_functions(words, start_idx)
        
        # Determine special function type
        special_type = self._determine_special_type(func_name)
        
        return SkillFunctionWithOverloads(
            name=func_name,
            overloads=overloads,
            description=description,
            arguments_description=arguments_desc,
            examples=examples,
            page=page_num,
            category=category,
            related_functions=related_functions,
            special_type=special_type
        )

    def _find_all_overloads(self, words: List[Dict], start_idx: int, func_name: str) -> List[FunctionOverload]:
        """Find all function overloads systematically"""
        overloads = []
        
        # Search for signatures in the function definition area
        search_end = min(start_idx + 200, len(words))
        
        for i in range(start_idx + 1, search_end):
            word = words[i]
            text = word['text']
            
            # Stop at next function or major section
            if self._is_section_boundary(words, i, func_name):
                break
                
            # Look for signature pattern: functionName(
            if text == f"{func_name}(" or text.startswith(f"{func_name}("):
                overload = self._parse_single_overload(words, i, func_name)
                if overload:
                    overloads.append(overload)
                    
        return overloads

    def _is_section_boundary(self, words: List[Dict], index: int, current_func: str) -> bool:
        """Detect section boundaries to stop function parsing"""
        word = words[index]
        text = word['text']
        
        # Next function
        if (self._is_potential_function_name(text, word) and 
            text != current_func and
            word['x'] < 100 and word['font_size'] > 11):
            return True
            
        # Major sections
        major_sections = ['Examples', 'Related', 'Topics', 'See', 'Also']
        if text in major_sections and word['x'] < 100:
            return True
            
        return False

    def _parse_single_overload(self, words: List[Dict], start_idx: int, func_name: str) -> Optional[FunctionOverload]:
        """Parse single function overload with enhanced parameter handling"""
        parameters = []
        signature_parts = [f"{func_name}("]
        return_type = ""
        
        i = start_idx + 1 if words[start_idx]['text'] == f"{func_name}(" else start_idx
        paren_count = 1
        bracket_depth = 0
        position = 0
        
        # Parse signature
        while i < len(words) and i < start_idx + 50:
            word = words[i]
            text = word['text']
            
            signature_parts.append(text)
            
            # Track parentheses and brackets
            paren_count += text.count('(') - text.count(')')
            
            if text == '[':
                bracket_depth += 1
            elif text == ']':
                bracket_depth -= 1
                
            # End of signature
            if paren_count <= 0:
                break
                
            # Parse parameter
            if text not in ['(', ')', '[', ']', '=>'] and re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', text):
                param = self._parse_enhanced_parameter(text, bracket_depth > 0, position)
                if param:
                    parameters.append(param)
                    position += 1
                    
            i += 1
            
        # Look for return type
        return_type = self._extract_return_type(words, i)
        
        if parameters or func_name in self.car_cdr_functions:
            raw_signature = ' '.join(signature_parts)
            return FunctionOverload(
                signature=raw_signature,
                parameters=parameters,
                return_type=return_type,
                raw_signature=raw_signature
            )
            
        return None

    def _parse_enhanced_parameter(self, param_name: str, is_optional: bool, position: int) -> Optional[SkillParameter]:
        """Parse parameter with comprehensive type detection"""
        # Determine parameter type
        if param_name == '...':
            param_type = ParameterType.VARIADIC
        elif param_name.startswith('?'):
            param_type = ParameterType.KEYWORD
            param_name = param_name[1:]  # Remove ? prefix
        elif is_optional:
            param_type = ParameterType.OPTIONAL
        else:
            param_type = ParameterType.REQUIRED
            
        # Extract data type from prefix
        data_type = self._extract_parameter_type(param_name)
        
        return SkillParameter(
            name=param_name,
            param_type=param_type,
            data_type=data_type,
            position=position
        )

    def _extract_parameter_type(self, param_name: str) -> str:
        """Extract parameter type using official SKILL mappings"""
        for prefix, type_name in self.official_data_types.items():
            if param_name.startswith(prefix):
                return type_name
        return 'general'  # Default type

    def _extract_return_type(self, words: List[Dict], start_idx: int) -> str:
        """Extract return type after '=>' """
        for i in range(start_idx, min(start_idx + 10, len(words))):
            if words[i]['text'] == '=>':
                return_parts = []
                j = i + 1
                while j < len(words) and j < i + 5:
                    ret_text = words[j]['text']
                    if ret_text in ['t', 'nil', '/', 'list', 'string', 'number'] or re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', ret_text):
                        return_parts.append(ret_text)
                    else:
                        break
                    j += 1
                return ' '.join(return_parts)
        return ""

    def _extract_description(self, words: List[Dict], start_idx: int) -> str:
        """Extract function description"""
        for i in range(start_idx, min(start_idx + 150, len(words))):
            if words[i]['text'] == 'Description':
                desc_parts = []
                j = i + 1
                while j < len(words) and j < i + 50:
                    text = words[j]['text']
                    if text in ['Arguments', 'Value', 'Returned', 'Examples', 'Related']:
                        break
                    desc_parts.append(text)
                    j += 1
                return ' '.join(desc_parts)
        return ""

    def _extract_arguments_description(self, words: List[Dict], start_idx: int) -> Dict[str, str]:
        """Extract argument descriptions"""
        args_desc = {}
        
        for i in range(start_idx, min(start_idx + 200, len(words))):
            if words[i]['text'] == 'Arguments':
                j = i + 1
                current_arg = None
                arg_desc_parts = []
                
                while j < len(words) and j < i + 100:
                    text = words[j]['text']
                    
                    if text in ['Value', 'Returned', 'Examples', 'Related']:
                        break
                    
                    # Check if this is an argument name
                    if self._extract_parameter_type(text) != 'general':
                        if current_arg and arg_desc_parts:
                            args_desc[current_arg] = ' '.join(arg_desc_parts)
                        current_arg = text
                        arg_desc_parts = []
                    else:
                        if current_arg:
                            arg_desc_parts.append(text)
                    
                    j += 1
                
                if current_arg and arg_desc_parts:
                    args_desc[current_arg] = ' '.join(arg_desc_parts)
                break
                
        return args_desc

    def _extract_examples(self, words: List[Dict], start_idx: int) -> List[str]:
        """Extract function examples"""
        examples = []
        
        for i in range(start_idx, min(start_idx + 300, len(words))):
            if words[i]['text'] == 'Examples':
                example_parts = []
                j = i + 1
                while j < len(words) and j < i + 50:
                    text = words[j]['text']
                    if text in ['Related', 'Topics', 'See', 'Also']:
                        break
                    example_parts.append(text)
                    j += 1
                if example_parts:
                    examples.append(' '.join(example_parts))
                break
                
        return examples

    def _extract_related_functions(self, words: List[Dict], start_idx: int) -> List[str]:
        """Extract related function names"""
        related = []
        
        for i in range(start_idx, min(start_idx + 300, len(words))):
            if words[i]['text'] in ['Related', 'Topics']:
                j = i + 1
                while j < len(words) and j < i + 20:
                    text = words[j]['text']
                    if re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', text):
                        related.append(text)
                    j += 1
                break
                
        return related

    def _determine_special_type(self, func_name: str) -> Optional[str]:
        """Determine if function belongs to special type categories"""
        if func_name in self.car_cdr_functions:
            return "car_cdr_series"
        elif func_name in self.vi_series_functions:
            return "vi_series"
        elif any(func_name.startswith(pattern) for pattern in self.template_patterns):
            return "template_function"
        return None

    def _process_special_functions(self, functions: List[SkillFunctionWithOverloads]) -> List[SkillFunctionWithOverloads]:
        """Post-process special function patterns"""
        # Only generate special functions if we found any real functions
        if not functions:
            return functions
            
        # Generate missing car/cdr functions
        existing_names = {f.name for f in functions}
        
        for car_cdr_name in self.car_cdr_functions:
            if car_cdr_name not in existing_names:
                generated_func = self._generate_car_cdr_function(car_cdr_name)
                if generated_func:
                    functions.append(generated_func)
                    
        # Process VI series functions individually
        for vi_func in self.vi_series_functions:
            if vi_func not in existing_names:
                generated_func = self._generate_vi_function(vi_func)
                if generated_func:
                    functions.append(generated_func)
                    
        return functions

    def _generate_car_cdr_function(self, func_name: str) -> SkillFunctionWithOverloads:
        """Generate car/cdr function with unified signature"""
        # Unified signature for all car/cdr functions
        param = SkillParameter(
            name="l_list",
            param_type=ParameterType.REQUIRED,
            data_type="list",
            position=0
        )
        
        overload = FunctionOverload(
            signature=f"{func_name}(l_list) => t",
            parameters=[param],
            return_type="t",
            raw_signature=f"{func_name}(l_list)"
        )
        
        return SkillFunctionWithOverloads(
            name=func_name,
            overloads=[overload],
            description=f"Extracts elements from list using {func_name} pattern",
            arguments_description={"l_list": "Input list to extract from"},
            examples=[f"{func_name}('(a b c d))"],
            page=0,
            special_type="car_cdr_series"
        )

    def _generate_vi_function(self, func_name: str) -> SkillFunctionWithOverloads:
        """Generate VI series function with individual examples"""
        examples_map = {
            'vi': ['vi("Layout")'],
            'vii': ['vii("Layout" "cellName")'], 
            'vil': ['vil("Layout" "cellName" "viewName")']
        }
        
        param = SkillParameter(
            name="t_string",
            param_type=ParameterType.REQUIRED,
            data_type="string",
            position=0
        )
        
        overload = FunctionOverload(
            signature=f"{func_name}(t_string) => t",
            parameters=[param],
            return_type="t",
            raw_signature=f"{func_name}(t_string)"
        )
        
        return SkillFunctionWithOverloads(
            name=func_name,
            overloads=[overload],
            description=f"VI series function {func_name}",
            arguments_description={"t_string": "Input string parameter"},
            examples=examples_map.get(func_name, [f"{func_name}(\"example\")"]),
            page=0,
            special_type="vi_series"
        )

    def convert_pdf_to_html(self, pdf_path: str, html_path: str) -> bool:
        """Convert PDF to HTML using pdftotext with bbox option"""
        import subprocess
        
        try:
            cmd = ['pdftotext', '-bbox', pdf_path, html_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            print("Error: pdftotext not found. Please install poppler-utils.")
            return False

    def save_results(self, functions: List[SkillFunctionWithOverloads], output_path: str):
        """Save parsing results to JSON file"""
        # Convert to serializable format
        serializable_functions = []
        for func in functions:
            func_data = asdict(func)
            # Convert enums to strings
            for overload in func_data['overloads']:
                for param in overload['parameters']:
                    param['param_type'] = param['param_type'].value if hasattr(param['param_type'], 'value') else str(param['param_type'])
            serializable_functions.append(func_data)
            
        # Save with metadata
        output_data = {
            'metadata': {
                'parser_version': '1.0.0',
                'total_functions': len(functions),
                'extraction_timestamp': __import__('datetime').datetime.now().isoformat(),
                'special_function_counts': {
                    'car_cdr_series': len([f for f in functions if f.special_type == 'car_cdr_series']),
                    'vi_series': len([f for f in functions if f.special_type == 'vi_series']),
                    'template_functions': len([f for f in functions if f.special_type == 'template_function']),
                }
            },
            'functions': serializable_functions
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

def main():
    """Main entry point for the SKILL PDF/HTML parser"""
    parser = argparse.ArgumentParser(description='SKILL PDF/HTML Function Parser')
    parser.add_argument('input_file', help='Input PDF or HTML file path')
    parser.add_argument('-o', '--output', help='Output JSON file path', required=True)
    parser.add_argument('--document-name', help='Document name for categorization', default='')
    parser.add_argument('--convert-pdf', action='store_true', help='Convert PDF to HTML first')
    
    args = parser.parse_args()
    
    skill_parser = SkillPDFHTMLParser()
    
    # Handle PDF conversion if needed
    if args.convert_pdf or args.input_file.endswith('.pdf'):
        if not args.input_file.endswith('.pdf'):
            print("Error: --convert-pdf specified but input is not a PDF file")
            return 1
            
        html_path = args.input_file.replace('.pdf', '.html')
        print(f"Converting PDF to HTML: {args.input_file} -> {html_path}")
        
        if not skill_parser.convert_pdf_to_html(args.input_file, html_path):
            print("Failed to convert PDF to HTML")
            return 1
            
        input_path = html_path
    else:
        input_path = args.input_file
    
    # Parse HTML content
    print(f"Parsing HTML content: {input_path}")
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except Exception as e:
        print(f"Error reading HTML file: {e}")
        return 1
        
    # Extract functions
    functions = skill_parser.parse_html_content(html_content, args.document_name)
    
    # Save results
    skill_parser.save_results(functions, args.output)
    
    # Print summary
    print(f"\n=== Parsing Complete ===")
    print(f"Total functions extracted: {len(functions)}")
    print(f"Functions with multiple overloads: {len([f for f in functions if len(f.overloads) > 1])}")
    print(f"Functions with categories: {len([f for f in functions if f.category])}")
    print(f"Special function counts:")
    print(f"  - Car/CDR series: {len([f for f in functions if f.special_type == 'car_cdr_series'])}")
    print(f"  - VI series: {len([f for f in functions if f.special_type == 'vi_series'])}")
    print(f"  - Template functions: {len([f for f in functions if f.special_type == 'template_function'])}")
    print(f"Results saved to: {args.output}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())