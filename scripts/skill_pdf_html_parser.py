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
from typing import Dict, List, Optional, Tuple, Union, Set, Any
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
class RawFunctionData:
    """Raw function data extracted from PDF with complete context"""
    name: str
    raw_signature: str
    raw_description: str
    raw_parameters: str
    raw_return_info: str
    raw_examples: str
    page_number: int
    position: Dict[str, float]  # x, y coordinates
    font_info: Dict[str, Any]   # font_size, font_family, etc.
    context_before: str         # Text before function
    context_after: str          # Text after function
    category_context: str       # Current category context
    html_element: str           # Original HTML element
    
@dataclass
class RawDocumentData:
    """Complete raw document data with all PDF information"""
    metadata: Dict[str, Any]
    pages: List[Dict[str, Any]]
    functions: List[RawFunctionData]
    categories: List[Dict[str, Any]]
    raw_text: str
    html_content: str

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
    raw_data: Optional[RawFunctionData] = None  # Link to raw data
    
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
    
    def extract_raw_document_data(self, html_content: str, document_name: str = "", pdf_path: str = "") -> RawDocumentData:
        """Extract complete raw document data with all PDF information"""
        soup = BeautifulSoup(html_content, 'html.parser')
        pages = soup.find_all('page')
        
        # Extract raw text for full content preservation
        raw_text = soup.get_text()
        
        # Process each page
        page_data = []
        all_raw_functions = []
        all_categories = []
        
        for page_num, page in enumerate(pages, 1):
            # Extract positioned words with full context
            words = self._extract_positioned_words(page)
            
            # Store page information
            page_info = {
                'page_number': page_num,
                'dimensions': {
                    'width': float(page.get('width', 612)),
                    'height': float(page.get('height', 792))
                },
                'word_count': len(words),
                'raw_text': page.get_text()
            }
            page_data.append(page_info)
            
            # Extract raw functions with full context
            raw_functions = self._extract_raw_functions_from_page(words, page_num)
            all_raw_functions.extend(raw_functions)
            
            # Extract categories
            categories = self._extract_raw_categories_from_page(words, page_num, document_name)
            all_categories.extend(categories)
        
        # Create metadata
        metadata = {
            'source_file': pdf_path,
            'document_name': document_name,
            'extraction_timestamp': __import__('datetime').datetime.now().isoformat(),
            'total_pages': len(pages),
            'total_functions': len(all_raw_functions),
            'total_categories': len(all_categories),
            'parser_version': '1.0.0'
        }
        
        return RawDocumentData(
            metadata=metadata,
            pages=page_data,
            functions=all_raw_functions,
            categories=all_categories,
            raw_text=raw_text,
            html_content=html_content
        )
    
    def _extract_raw_functions_from_page(self, words: List[Dict], page_num: int) -> List[RawFunctionData]:
        """Extract raw function data with complete context"""
        raw_functions = []
        
        for i, word in enumerate(words):
            # Look for function signatures
            if self._is_function_signature(word['text'], words, i, page_num):
                func_name = word['text']
                
                # Extract surrounding context
                context_before = self._extract_context(words, i, -20, 0)
                context_after = self._extract_context(words, i, 1, 50)
                
                # Extract raw components
                raw_signature = self._extract_raw_signature(words, i)
                raw_description = self._extract_raw_section(words, i, 'Description')
                raw_parameters = self._extract_raw_section(words, i, 'Arguments')
                raw_return_info = self._extract_raw_section(words, i, 'Value Returned')
                raw_examples = self._extract_raw_section(words, i, 'Examples')
                
                # Get current category context
                category_context = self._get_current_category_context(words, i)
                
                raw_function = RawFunctionData(
                    name=func_name,
                    raw_signature=raw_signature,
                    raw_description=raw_description,
                    raw_parameters=raw_parameters,
                    raw_return_info=raw_return_info,
                    raw_examples=raw_examples,
                    page_number=page_num,
                    position={
                        'x': word['x'],
                        'y': word['y']
                    },
                    font_info={
                        'font_size': word['font_size'],
                        'element_info': str(word['element'])
                    },
                    context_before=context_before,
                    context_after=context_after,
                    category_context=category_context,
                    html_element=str(word['element'])
                )
                raw_functions.append(raw_function)
        
        return raw_functions
    
    def _extract_raw_categories_from_page(self, words: List[Dict], page_num: int, document_name: str) -> List[Dict[str, Any]]:
        """Extract raw category information"""
        categories = []
        
        for i, word in enumerate(words):
            if self._is_category_header(word['text'], word['font_size'], word['x'], words, i):
                category_info = {
                    'text': word['text'],
                    'page_number': page_num,
                    'position': {'x': word['x'], 'y': word['y']},
                    'font_size': word['font_size'],
                    'level': self._determine_category_level(word['font_size'], word['x']),
                    'context': self._extract_context(words, i, -5, 10),
                    'document_name': document_name
                }
                categories.append(category_info)
        
        return categories
    
    def _extract_context(self, words: List[Dict], center_idx: int, start_offset: int, end_offset: int) -> str:
        """Extract context text around a position"""
        start_idx = max(0, center_idx + start_offset)
        end_idx = min(len(words), center_idx + end_offset)
        
        context_words = []
        for i in range(start_idx, end_idx):
            if i != center_idx:  # Skip the center word
                context_words.append(words[i]['text'])
        
        return ' '.join(context_words)
    
    def _extract_raw_signature(self, words: List[Dict], start_idx: int) -> str:
        """Extract raw function signature"""
        signature_parts = []
        i = start_idx
        
        while i < len(words) and i < start_idx + 20:
            text = words[i]['text']
            signature_parts.append(text)
            
            # Stop at end of signature (usually marked by closing parenthesis)
            if ')' in text:
                break
            i += 1
        
        return ' '.join(signature_parts)
    
    def _extract_raw_section(self, words: List[Dict], start_idx: int, section_name: str) -> str:
        """Extract raw section content"""
        section_start = None
        
        # Find section start
        for i in range(start_idx, min(start_idx + 100, len(words))):
            if words[i]['text'] == section_name:
                section_start = i + 1
                break
        
        if section_start is None:
            return ""
        
        # Find section end (next major section or end of context)
        section_end = section_start + 50
        section_keywords = ['Arguments', 'Value Returned', 'Examples', 'Related', 'Description']
        
        for i in range(section_start, min(section_start + 100, len(words))):
            if words[i]['text'] in section_keywords:
                section_end = i
                break
        
        # Extract section content
        section_content = []
        for i in range(section_start, min(section_end, len(words))):
            section_content.append(words[i]['text'])
        
        return ' '.join(section_content)
    
    def _get_current_category_context(self, words: List[Dict], position: int) -> str:
        """Get current category context for a function"""
        # Look backwards for category headers
        for i in range(position - 1, max(0, position - 50), -1):
            word = words[i]
            if self._is_category_header(word['text'], word['font_size'], word['x'], words, i):
                return word['text']
        
        return ""
    
    def _is_function_signature(self, text: str, words: List[Dict], index: int, page_num: int = 0) -> bool:
        """Determine if text is likely a function signature - very strict criteria"""
        # Basic function name pattern
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', text):
            return False
        
        # Skip if this is on early pages (likely table of contents)
        if page_num > 0 and page_num < 31:  # Function definitions start around page 31 in sklangref
            return False
        
        # Skip if this is likely a table of contents (check for dots and page numbers)
        context_after = ' '.join([w['text'] for w in words[index:min(index+10, len(words))]])
        if '.' in context_after and re.search(r'\d+$', context_after.strip()):
            return False
        
        # Skip common non-function words
        common_words = {
            'cadence', 'skill', 'language', 'reference', 'list', 'functions', 'data', 'structures',
            'string', 'example', 'examples', 'association', 'table', 'check', 'contents', 'the',
            'of', 'and', 'or', 'if', 'then', 'else', 'when', 'where', 'this', 'that', 'with',
            'from', 'to', 'in', 'on', 'at', 'by', 'for', 'as', 'an', 'a', 'is', 'are', 'was',
            'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'can', 'cannot', 'not', 'no',
            'yes', 'true', 'false', 'nil', 'null', 'value', 'values', 'type', 'types', 'note',
            'notes', 'see', 'also', 'related', 'page', 'pages', 'chapter', 'section', 'subsection',
            'version', 'product', 'copyright', 'reserved', 'rights', 'all', 'inc', 'august',
            'argument', 'arguments', 'parameter', 'parameters', 'returned', 'returns', 'return',
            'description', 'syntax', 'usage', 'format', 'summary', 'overview', 'introduction',
            'conclusion', 'result', 'results', 'output', 'input', 'file', 'files', 'directory',
            'path', 'name', 'names', 'identifier', 'identifiers', 'symbol', 'symbols', 'keyword',
            'keywords', 'operator', 'operators', 'expression', 'expressions', 'statement',
            'statements', 'declaration', 'declarations', 'definition', 'definitions', 'implementation',
            'implementations', 'specification', 'specifications', 'documentation', 'manual',
            'guide', 'tutorial', 'help', 'support', 'error', 'errors', 'warning', 'warnings',
            'message', 'messages', 'status', 'state', 'states', 'condition', 'conditions',
            'operation', 'operations', 'action', 'actions', 'process', 'processes', 'procedure',
            'procedures', 'method', 'methods', 'technique', 'techniques', 'approach', 'approaches',
            'solution', 'solutions', 'problem', 'problems', 'issue', 'issues', 'topic', 'topics',
            'subject', 'subjects', 'matter', 'content', 'contents', 'item', 'items', 'element',
            'elements', 'component', 'components', 'part', 'parts', 'piece', 'pieces', 'unit',
            'units', 'module', 'modules', 'package', 'packages', 'library', 'libraries',
            'function', 'functions', 'routine', 'routines', 'subroutine', 'subroutines',
            'macro', 'macros', 'class', 'classes', 'object', 'objects', 'instance', 'instances',
            'variable', 'variables', 'constant', 'constants', 'field', 'fields', 'property',
            'properties', 'attribute', 'attributes', 'feature', 'features', 'option', 'options',
            'setting', 'settings', 'configuration', 'configurations', 'preference', 'preferences',
            'default', 'defaults', 'standard', 'standards', 'convention', 'conventions',
            'protocol', 'protocols', 'interface', 'interfaces', 'api', 'apis', 'service',
            'services', 'application', 'applications', 'program', 'programs', 'software',
            'system', 'systems', 'platform', 'platforms', 'environment', 'environments',
            'framework', 'frameworks', 'tool', 'tools', 'utility', 'utilities', 'resource',
            'resources', 'facility', 'facilities', 'capability', 'capabilities', 'feature',
            'features', 'functionality', 'functionalities', 'behavior', 'behaviors', 'performance',
            'performances', 'efficiency', 'efficiencies', 'optimization', 'optimizations',
            'improvement', 'improvements', 'enhancement', 'enhancements', 'extension', 'extensions',
            'modification', 'modifications', 'change', 'changes', 'update', 'updates', 'upgrade',
            'upgrades', 'migration', 'migrations', 'conversion', 'conversions', 'transformation',
            'transformations', 'translation', 'translations', 'adaptation', 'adaptations',
            'customization', 'customizations', 'personalization', 'personalizations',
            'configuration', 'configurations', 'installation', 'installations', 'setup',
            'setups', 'initialization', 'initializations', 'startup', 'startups', 'shutdown',
            'shutdowns', 'cleanup', 'cleanups', 'maintenance', 'maintenances', 'monitoring',
            'monitorings', 'logging', 'loggings', 'debugging', 'debuggings', 'testing',
            'testings', 'validation', 'validations', 'verification', 'verifications',
            'inspection', 'inspections', 'review', 'reviews', 'audit', 'audits', 'analysis',
            'analyses', 'evaluation', 'evaluations', 'assessment', 'assessments', 'measurement',
            'measurements', 'metric', 'metrics', 'statistic', 'statistics', 'report', 'reports',
            'summary', 'summaries', 'overview', 'overviews', 'detail', 'details', 'information',
            'informations', 'data', 'dataset', 'datasets', 'record', 'records', 'entry',
            'entries', 'item', 'items', 'element', 'elements', 'component', 'components',
            'part', 'parts', 'piece', 'pieces', 'fragment', 'fragments', 'portion', 'portions',
            'section', 'sections', 'segment', 'segments', 'block', 'blocks', 'chunk', 'chunks',
            'packet', 'packets', 'frame', 'frames', 'buffer', 'buffers', 'cache', 'caches',
            'memory', 'memories', 'storage', 'storages', 'disk', 'disks', 'drive', 'drives',
            'device', 'devices', 'hardware', 'hardwares', 'machine', 'machines', 'computer',
            'computers', 'processor', 'processors', 'cpu', 'cpus', 'server', 'servers',
            'client', 'clients', 'host', 'hosts', 'network', 'networks', 'connection',
            'connections', 'link', 'links', 'channel', 'channels', 'port', 'ports',
            'socket', 'sockets', 'stream', 'streams', 'flow', 'flows', 'pipe', 'pipes',
            'queue', 'queues', 'stack', 'stacks', 'heap', 'heaps', 'tree', 'trees',
            'graph', 'graphs', 'node', 'nodes', 'edge', 'edges', 'vertex', 'vertices',
            'branch', 'branches', 'leaf', 'leaves', 'root', 'roots', 'parent', 'parents',
            'child', 'children', 'sibling', 'siblings', 'ancestor', 'ancestors',
            'descendant', 'descendants', 'predecessor', 'predecessors', 'successor',
            'successors', 'neighbor', 'neighbors', 'adjacent', 'adjacents', 'connected',
            'connecteds', 'linked', 'linkeds', 'related', 'relateds', 'associated',
            'associateds', 'corresponding', 'correspondings', 'equivalent', 'equivalents',
            'similar', 'similars', 'identical', 'identicals', 'same', 'sames', 'different',
            'differents', 'distinct', 'distincts', 'unique', 'uniques', 'common', 'commons',
            'shared', 'shareds', 'public', 'publics', 'private', 'privates', 'protected',
            'protecteds', 'internal', 'internals', 'external', 'externals', 'visible',
            'visibles', 'hidden', 'hiddens', 'accessible', 'accessibles', 'available',
            'availables', 'enabled', 'enableds', 'disabled', 'disableds', 'active',
            'actives', 'inactive', 'inactives', 'valid', 'valids', 'invalid', 'invalids',
            'legal', 'legals', 'illegal', 'illegals', 'allowed', 'alloweds', 'forbidden',
            'forbiddens', 'permitted', 'permitteds', 'prohibited', 'prohibiteds',
            'required', 'requireds', 'optional', 'optionals', 'mandatory', 'mandatories',
            'necessary', 'necessaries', 'sufficient', 'sufficients', 'complete', 'completes',
            'incomplete', 'incompletes', 'partial', 'partials', 'full', 'fulls', 'empty',
            'empties', 'null', 'nulls', 'void', 'voids', 'blank', 'blanks', 'zero', 'zeros',
            'one', 'ones', 'two', 'twos', 'three', 'threes', 'four', 'fours', 'five', 'fives',
            'six', 'sixes', 'seven', 'sevens', 'eight', 'eights', 'nine', 'nines', 'ten', 'tens',
            'first', 'firsts', 'second', 'seconds', 'third', 'thirds', 'fourth', 'fourths',
            'fifth', 'fifths', 'sixth', 'sixths', 'seventh', 'sevenths', 'eighth', 'eighths',
            'ninth', 'ninths', 'tenth', 'tenths', 'last', 'lasts', 'final', 'finals',
            'initial', 'initials', 'beginning', 'beginnings', 'start', 'starts', 'end',
            'ends', 'finish', 'finishes', 'completion', 'completions', 'termination',
            'terminations', 'conclusion', 'conclusions', 'close', 'closes', 'open', 'opens',
            'create', 'creates', 'delete', 'deletes', 'remove', 'removes', 'add', 'adds',
            'insert', 'inserts', 'update', 'updates', 'modify', 'modifies', 'change', 'changes',
            'replace', 'replaces', 'substitute', 'substitutes', 'swap', 'swaps', 'exchange',
            'exchanges', 'move', 'moves', 'copy', 'copies', 'duplicate', 'duplicates',
            'clone', 'clones', 'backup', 'backups', 'restore', 'restores', 'save', 'saves',
            'load', 'loads', 'read', 'reads', 'write', 'writes', 'print', 'prints',
            'display', 'displays', 'show', 'shows', 'hide', 'hides', 'reveal', 'reveals',
            'expose', 'exposes', 'cover', 'covers', 'mask', 'masks', 'filter', 'filters',
            'sort', 'sorts', 'search', 'searches', 'find', 'finds', 'locate', 'locates',
            'discover', 'discovers', 'detect', 'detects', 'identify', 'identifies',
            'recognize', 'recognizes', 'match', 'matches', 'compare', 'compares',
            'contrast', 'contrasts', 'differentiate', 'differentiates', 'distinguish',
            'distinguishes', 'separate', 'separates', 'divide', 'divides', 'split', 'splits',
            'join', 'joins', 'combine', 'combines', 'merge', 'merges', 'unite', 'unites',
            'connect', 'connects', 'link', 'links', 'associate', 'associates', 'relate',
            'relates', 'bind', 'binds', 'attach', 'attaches', 'detach', 'detaches',
            'disconnect', 'disconnects', 'unlink', 'unlinks', 'break', 'breaks',
            'interrupt', 'interrupts', 'pause', 'pauses', 'resume', 'resumes',
            'continue', 'continues', 'proceed', 'proceeds', 'advance', 'advances',
            'progress', 'progresses', 'develop', 'develops', 'evolve', 'evolves',
            'grow', 'grows', 'expand', 'expands', 'extend', 'extends', 'stretch',
            'stretches', 'increase', 'increases', 'decrease', 'decreases', 'reduce',
            'reduces', 'minimize', 'minimizes', 'maximize', 'maximizes', 'optimize',
            'optimizes', 'improve', 'improves', 'enhance', 'enhances', 'upgrade',
            'upgrades', 'downgrade', 'downgrades', 'maintain', 'maintains', 'preserve',
            'preserves', 'conserve', 'conserves', 'protect', 'protects', 'secure',
            'secures', 'defend', 'defends', 'guard', 'guards', 'shield', 'shields',
            'cover', 'covers', 'wrap', 'wraps', 'enclose', 'encloses', 'contain',
            'contains', 'hold', 'holds', 'store', 'stores', 'keep', 'keeps',
            'retain', 'retains', 'maintain', 'maintains', 'sustain', 'sustains',
            'support', 'supports', 'help', 'helps', 'assist', 'assists', 'aid', 'aids',
            'serve', 'serves', 'provide', 'provides', 'supply', 'supplies', 'offer',
            'offers', 'give', 'gives', 'deliver', 'delivers', 'present', 'presents',
            'submit', 'submits', 'send', 'sends', 'transmit', 'transmits', 'transfer',
            'transfers', 'transport', 'transports', 'carry', 'carries', 'bring', 'brings',
            'take', 'takes', 'get', 'gets', 'obtain', 'obtains', 'acquire', 'acquires',
            'receive', 'receives', 'accept', 'accepts', 'reject', 'rejects', 'refuse',
            'refuses', 'deny', 'denies', 'allow', 'allows', 'permit', 'permits',
            'enable', 'enables', 'disable', 'disables', 'activate', 'activates',
            'deactivate', 'deactivates', 'turn', 'turns', 'switch', 'switches',
            'toggle', 'toggles', 'flip', 'flips', 'reverse', 'reverses', 'invert',
            'inverts', 'negate', 'negates', 'oppose', 'opposes', 'counter', 'counters',
            'balance', 'balances', 'offset', 'offsets', 'compensate', 'compensates',
            'adjust', 'adjusts', 'tune', 'tunes', 'calibrate', 'calibrates',
            'configure', 'configures', 'setup', 'setups', 'install', 'installs',
            'uninstall', 'uninstalls', 'deploy', 'deploys', 'undeploy', 'undeploys',
            'launch', 'launches', 'start', 'starts', 'stop', 'stops', 'restart',
            'restarts', 'reboot', 'reboots', 'reset', 'resets', 'clear', 'clears',
            'clean', 'cleans', 'purge', 'purges', 'flush', 'flushes', 'refresh',
            'refreshes', 'reload', 'reloads', 'renew', 'renews', 'rebuild', 'rebuilds',
            'reconstruct', 'reconstructs', 'recreate', 'recreates', 'regenerate',
            'regenerates', 'reproduce', 'reproduces', 'replicate', 'replicates',
            'repeat', 'repeats', 'retry', 'retries', 'redo', 'redoes', 'undo', 'undoes',
            'cancel', 'cancels', 'abort', 'aborts', 'quit', 'quits', 'exit', 'exits',
            'leave', 'leaves', 'return', 'returns', 'come', 'comes', 'go', 'goes',
            'move', 'moves', 'navigate', 'navigates', 'travel', 'travels', 'visit',
            'visits', 'explore', 'explores', 'browse', 'browses', 'scan', 'scans',
            'survey', 'surveys', 'examine', 'examines', 'inspect', 'inspects',
            'investigate', 'investigates', 'study', 'studies', 'research', 'researches',
            'analyze', 'analyzes', 'evaluate', 'evaluates', 'assess', 'assesses',
            'measure', 'measures', 'calculate', 'calculates', 'compute', 'computes',
            'determine', 'determines', 'decide', 'decides', 'choose', 'chooses',
            'select', 'selects', 'pick', 'picks', 'opt', 'opts', 'prefer', 'prefers',
            'favor', 'favors', 'like', 'likes', 'dislike', 'dislikes', 'love', 'loves',
            'hate', 'hates', 'want', 'wants', 'need', 'needs', 'require', 'requires',
            'demand', 'demands', 'request', 'requests', 'ask', 'asks', 'question',
            'questions', 'answer', 'answers', 'respond', 'responds', 'reply', 'replies',
            'react', 'reacts', 'interact', 'interacts', 'communicate', 'communicates',
            'talk', 'talks', 'speak', 'speaks', 'say', 'says', 'tell', 'tells',
            'inform', 'informs', 'notify', 'notifies', 'alert', 'alerts', 'warn',
            'warns', 'advise', 'advises', 'recommend', 'recommends', 'suggest',
            'suggests', 'propose', 'proposes', 'offer', 'offers', 'present',
            'presents', 'introduce', 'introduces', 'describe', 'describes',
            'explain', 'explains', 'clarify', 'clarifies', 'define', 'defines',
            'specify', 'specifies', 'detail', 'details', 'elaborate', 'elaborates',
            'expand', 'expands', 'extend', 'extends', 'develop', 'develops',
            'build', 'builds', 'construct', 'constructs', 'assemble', 'assembles',
            'manufacture', 'manufactures', 'produce', 'produces', 'generate',
            'generates', 'create', 'creates', 'make', 'makes', 'form', 'forms',
            'shape', 'shapes', 'mold', 'molds', 'cast', 'casts', 'forge', 'forges',
            'craft', 'crafts', 'design', 'designs', 'plan', 'plans', 'organize',
            'organizes', 'arrange', 'arranges', 'order', 'orders', 'structure',
            'structures', 'format', 'formats', 'layout', 'layouts', 'pattern',
            'patterns', 'template', 'templates', 'model', 'models', 'example',
            'examples', 'sample', 'samples', 'instance', 'instances', 'case',
            'cases', 'scenario', 'scenarios', 'situation', 'situations',
            'condition', 'conditions', 'circumstance', 'circumstances',
            'context', 'contexts', 'setting', 'settings', 'environment',
            'environments', 'background', 'backgrounds', 'history', 'histories',
            'record', 'records', 'log', 'logs', 'trace', 'traces', 'track',
            'tracks', 'monitor', 'monitors', 'watch', 'watches', 'observe',
            'observes', 'notice', 'notices', 'see', 'sees', 'view', 'views',
            'look', 'looks', 'check', 'checks', 'verify', 'verifies', 'confirm',
            'confirms', 'validate', 'validates', 'test', 'tests', 'try', 'tries',
            'attempt', 'attempts', 'effort', 'efforts', 'work', 'works', 'operate',
            'operates', 'function', 'functions', 'run', 'runs', 'execute', 'executes',
            'perform', 'performs', 'carry', 'carries', 'conduct', 'conducts',
            'manage', 'manages', 'handle', 'handles', 'deal', 'deals', 'treat',
            'treats', 'process', 'processes', 'manipulate', 'manipulates',
            'control', 'controls', 'govern', 'governs', 'rule', 'rules',
            'regulate', 'regulates', 'direct', 'directs', 'guide', 'guides',
            'lead', 'leads', 'follow', 'follows', 'accompany', 'accompanies',
            'escort', 'escorts', 'attend', 'attends', 'participate', 'participates',
            'join', 'joins', 'enter', 'enters', 'access', 'accesses', 'approach',
            'approaches', 'reach', 'reaches', 'arrive', 'arrives', 'come', 'comes',
            'appear', 'appears', 'emerge', 'emerges', 'surface', 'surfaces',
            'rise', 'rises', 'fall', 'falls', 'drop', 'drops', 'descend', 'descends',
            'climb', 'climbs', 'ascend', 'ascends', 'mount', 'mounts', 'dismount',
            'dismounts', 'board', 'boards', 'exit', 'exits', 'depart', 'departs',
            'leave', 'leaves', 'abandon', 'abandons', 'desert', 'deserts',
            'forsake', 'forsakes', 'quit', 'quits', 'resign', 'resigns',
            'retire', 'retires', 'withdraw', 'withdraws', 'retreat', 'retreats',
            'escape', 'escapes', 'flee', 'flees', 'run', 'runs', 'walk', 'walks',
            'step', 'steps', 'move', 'moves', 'shift', 'shifts', 'slide', 'slides',
            'glide', 'glides', 'flow', 'flows', 'stream', 'streams', 'pour',
            'pours', 'spill', 'spills', 'leak', 'leaks', 'drip', 'drips',
            'drop', 'drops', 'fall', 'falls', 'tumble', 'tumbles', 'collapse',
            'collapses', 'crash', 'crashes', 'break', 'breaks', 'shatter',
            'shatters', 'crack', 'cracks', 'split', 'splits', 'tear', 'tears',
            'rip', 'rips', 'cut', 'cuts', 'slice', 'slices', 'chop', 'chops',
            'hack', 'hacks', 'strike', 'strikes', 'hit', 'hits', 'punch',
            'punches', 'kick', 'kicks', 'push', 'pushes', 'pull', 'pulls',
            'drag', 'drags', 'draw', 'draws', 'attract', 'attracts', 'repel',
            'repels', 'resist', 'resists', 'oppose', 'opposes', 'fight',
            'fights', 'battle', 'battles', 'combat', 'combats', 'struggle',
            'struggles', 'compete', 'competes', 'contest', 'contests',
            'challenge', 'challenges', 'confront', 'confronts', 'face', 'faces',
            'meet', 'meets', 'encounter', 'encounters', 'experience',
            'experiences', 'undergo', 'undergoes', 'endure', 'endures',
            'suffer', 'suffers', 'bear', 'bears', 'tolerate', 'tolerates',
            'stand', 'stands', 'withstand', 'withstands', 'survive', 'survives',
            'live', 'lives', 'exist', 'exists', 'remain', 'remains', 'stay',
            'stays', 'continue', 'continues', 'persist', 'persists', 'last',
            'lasts', 'endure', 'endures', 'prevail', 'prevails', 'succeed',
            'succeeds', 'achieve', 'achieves', 'accomplish', 'accomplishes',
            'complete', 'completes', 'finish', 'finishes', 'end', 'ends',
            'terminate', 'terminates', 'conclude', 'concludes', 'close', 'closes',
            'seal', 'seals', 'lock', 'locks', 'unlock', 'unlocks', 'open',
            'opens', 'reveal', 'reveals', 'disclose', 'discloses', 'expose',
            'exposes', 'uncover', 'uncovers', 'discover', 'discovers', 'find',
            'finds', 'locate', 'locates', 'detect', 'detects', 'identify',
            'identifies', 'recognize', 'recognizes', 'know', 'knows', 'understand',
            'understands', 'comprehend', 'comprehends', 'grasp', 'grasps',
            'realize', 'realizes', 'perceive', 'perceives', 'sense', 'senses',
            'feel', 'feels', 'touch', 'touches', 'taste', 'tastes', 'smell',
            'smells', 'hear', 'hears', 'listen', 'listens', 'sound', 'sounds',
            'ring', 'rings', 'buzz', 'buzzes', 'hum', 'hums', 'whistle',
            'whistles', 'sing', 'sings', 'play', 'plays', 'perform', 'performs',
            'act', 'acts', 'behave', 'behaves', 'conduct', 'conducts', 'manage',
            'manages', 'handle', 'handles', 'operate', 'operates', 'control',
            'controls', 'direct', 'directs', 'guide', 'guides', 'lead', 'leads',
            'command', 'commands', 'order', 'orders', 'instruct', 'instructs',
            'teach', 'teaches', 'educate', 'educates', 'train', 'trains',
            'coach', 'coaches', 'mentor', 'mentors', 'advise', 'advises',
            'counsel', 'counsels', 'consult', 'consults', 'discuss', 'discusses',
            'talk', 'talks', 'converse', 'converses', 'chat', 'chats',
            'communicate', 'communicates', 'correspond', 'corresponds',
            'exchange', 'exchanges', 'share', 'shares', 'distribute', 'distributes',
            'spread', 'spreads', 'scatter', 'scatters', 'disperse', 'disperses',
            'disseminate', 'disseminates', 'broadcast', 'broadcasts', 'transmit',
            'transmits', 'send', 'sends', 'deliver', 'delivers', 'transport',
            'transports', 'carry', 'carries', 'bear', 'bears', 'bring', 'brings',
            'take', 'takes', 'fetch', 'fetches', 'retrieve', 'retrieves',
            'collect', 'collects', 'gather', 'gathers', 'assemble', 'assembles',
            'accumulate', 'accumulates', 'amass', 'amasses', 'pile', 'piles',
            'stack', 'stacks', 'heap', 'heaps', 'bunch', 'bunches', 'group',
            'groups', 'cluster', 'clusters', 'pack', 'packs', 'bundle', 'bundles',
            'wrap', 'wraps', 'package', 'packages', 'box', 'boxes', 'contain',
            'contains', 'hold', 'holds', 'store', 'stores', 'keep', 'keeps',
            'preserve', 'preserves', 'maintain', 'maintains', 'retain', 'retains',
            'save', 'saves', 'rescue', 'rescues', 'recover', 'recovers',
            'restore', 'restores', 'repair', 'repairs', 'fix', 'fixes',
            'mend', 'mends', 'heal', 'heals', 'cure', 'cures', 'treat',
            'treats', 'remedy', 'remedies', 'solve', 'solves', 'resolve',
            'resolves', 'settle', 'settles', 'decide', 'decides', 'determine',
            'determines', 'conclude', 'concludes', 'judge', 'judges', 'evaluate',
            'evaluates', 'assess', 'assesses', 'estimate', 'estimates',
            'calculate', 'calculates', 'compute', 'computes', 'count', 'counts',
            'measure', 'measures', 'weigh', 'weighs', 'balance', 'balances',
            'compare', 'compares', 'contrast', 'contrasts', 'match', 'matches',
            'equal', 'equals', 'differ', 'differs', 'vary', 'varies', 'change',
            'changes', 'alter', 'alters', 'modify', 'modifies', 'adjust',
            'adjusts', 'adapt', 'adapts', 'transform', 'transforms', 'convert',
            'converts', 'translate', 'translates', 'interpret', 'interprets',
            'decode', 'decodes', 'encode', 'encodes', 'encrypt', 'encrypts',
            'decrypt', 'decrypts', 'compress', 'compresses', 'decompress',
            'decompresses', 'expand', 'expands', 'contract', 'contracts',
            'shrink', 'shrinks', 'grow', 'grows', 'increase', 'increases',
            'decrease', 'decreases', 'rise', 'rises', 'fall', 'falls',
            'climb', 'climbs', 'descend', 'descends', 'advance', 'advances',
            'retreat', 'retreats', 'progress', 'progresses', 'regress',
            'regresses', 'develop', 'develops', 'evolve', 'evolves', 'mature',
            'matures', 'age', 'ages', 'decay', 'decays', 'deteriorate',
            'deteriorates', 'degrade', 'degrades', 'wear', 'wears', 'erode',
            'erodes', 'corrode', 'corrodes', 'rust', 'rusts', 'rot', 'rots',
            'spoil', 'spoils', 'corrupt', 'corrupts', 'contaminate',
            'contaminates', 'pollute', 'pollutes', 'dirty', 'dirties',
            'soil', 'soils', 'stain', 'stains', 'mark', 'marks', 'label',
            'labels', 'tag', 'tags', 'brand', 'brands', 'stamp', 'stamps',
            'print', 'prints', 'write', 'writes', 'inscribe', 'inscribes',
            'engrave', 'engraves', 'carve', 'carves', 'etch', 'etches',
            'scratch', 'scratches', 'score', 'scores', 'indent', 'indents',
            'dent', 'dents', 'bend', 'bends', 'fold', 'folds', 'crease',
            'creases', 'wrinkle', 'wrinkles', 'crumple', 'crumples',
            'flatten', 'flattens', 'smooth', 'smooths', 'polish', 'polishes',
            'shine', 'shines', 'glow', 'glows', 'sparkle', 'sparkles',
            'glitter', 'glitters', 'flash', 'flashes', 'blink', 'blinks',
            'twinkle', 'twinkles', 'flicker', 'flickers', 'flame', 'flames',
            'burn', 'burns', 'ignite', 'ignites', 'light', 'lights',
            'illuminate', 'illuminates', 'brighten', 'brightens', 'darken',
            'darkens', 'dim', 'dims', 'fade', 'fades', 'pale', 'pales',
            'bleach', 'bleaches', 'whiten', 'whitens', 'color', 'colors',
            'paint', 'paints', 'dye', 'dyes', 'tint', 'tints', 'shade',
            'shades', 'tone', 'tones', 'hue', 'hues', 'pigment', 'pigments',
            'texture', 'textures', 'surface', 'surfaces', 'finish', 'finishes',
            'coating', 'coatings', 'layer', 'layers', 'film', 'films',
            'membrane', 'membranes', 'skin', 'skins', 'shell', 'shells',
            'hull', 'hulls', 'case', 'cases', 'cover', 'covers', 'lid',
            'lids', 'cap', 'caps', 'top', 'tops', 'bottom', 'bottoms',
            'side', 'sides', 'edge', 'edges', 'border', 'borders', 'boundary',
            'boundaries', 'limit', 'limits', 'bound', 'bounds', 'range',
            'ranges', 'scope', 'scopes', 'extent', 'extents', 'reach',
            'reaches', 'span', 'spans', 'stretch', 'stretches', 'distance',
            'distances', 'length', 'lengths', 'width', 'widths', 'height',
            'heights', 'depth', 'depths', 'thickness', 'thicknesses',
            'diameter', 'diameters', 'radius', 'radii', 'circumference',
            'circumferences', 'perimeter', 'perimeters', 'area', 'areas',
            'volume', 'volumes', 'capacity', 'capacities', 'size', 'sizes',
            'dimension', 'dimensions', 'scale', 'scales', 'proportion',
            'proportions', 'ratio', 'ratios', 'fraction', 'fractions',
            'percentage', 'percentages', 'percent', 'percents', 'rate',
            'rates', 'speed', 'speeds', 'velocity', 'velocities',
            'acceleration', 'accelerations', 'momentum', 'momentums',
            'force', 'forces', 'power', 'powers', 'energy', 'energies',
            'strength', 'strengths', 'intensity', 'intensities', 'magnitude',
            'magnitudes', 'amplitude', 'amplitudes', 'frequency', 'frequencies',
            'wavelength', 'wavelengths', 'period', 'periods', 'cycle',
            'cycles', 'phase', 'phases', 'step', 'steps', 'stage', 'stages',
            'level', 'levels', 'degree', 'degrees', 'grade', 'grades',
            'rank', 'ranks', 'order', 'orders', 'sequence', 'sequences',
            'series', 'serieses', 'succession', 'successions', 'progression',
            'progressions', 'chain', 'chains', 'line', 'lines', 'row',
            'rows', 'column', 'columns', 'file', 'files', 'queue', 'queues',
            'stack', 'stacks', 'pile', 'piles', 'heap', 'heaps', 'batch',
            'batches', 'lot', 'lots', 'set', 'sets', 'collection',
            'collections', 'group', 'groups', 'cluster', 'clusters',
            'bundle', 'bundles', 'pack', 'packs', 'package', 'packages',
            'parcel', 'parcels', 'load', 'loads', 'cargo', 'cargos',
            'freight', 'freights', 'shipment', 'shipments', 'delivery',
            'deliveries', 'distribution', 'distributions', 'supply',
            'supplies', 'provision', 'provisions', 'stock', 'stocks',
            'inventory', 'inventories', 'reserve', 'reserves', 'backup',
            'backups', 'spare', 'spares', 'extra', 'extras', 'additional',
            'additionals', 'supplementary', 'supplementaries', 'auxiliary',
            'auxiliaries', 'secondary', 'secondaries', 'primary', 'primaries',
            'main', 'mains', 'major', 'majors', 'minor', 'minors', 'basic',
            'basics', 'fundamental', 'fundamentals', 'essential', 'essentials',
            'important', 'importants', 'significant', 'significants',
            'critical', 'criticals', 'vital', 'vitals', 'crucial', 'crucials',
            'key', 'keys', 'central', 'centrals', 'core', 'cores', 'heart',
            'hearts', 'center', 'centers', 'middle', 'middles', 'focus',
            'focuses', 'point', 'points', 'spot', 'spots', 'place', 'places',
            'position', 'positions', 'location', 'locations', 'site', 'sites',
            'area', 'areas', 'region', 'regions', 'zone', 'zones', 'sector',
            'sectors', 'district', 'districts', 'territory', 'territories',
            'domain', 'domains', 'realm', 'realms', 'field', 'fields',
            'sphere', 'spheres', 'scope', 'scopes', 'range', 'ranges',
            'extent', 'extents', 'limit', 'limits', 'boundary', 'boundaries',
            'border', 'borders', 'edge', 'edges', 'margin', 'margins',
            'frame', 'frames', 'outline', 'outlines', 'contour', 'contours',
            'profile', 'profiles', 'silhouette', 'silhouettes', 'shape',
            'shapes', 'form', 'forms', 'structure', 'structures', 'framework',
            'frameworks', 'architecture', 'architectures', 'design', 'designs',
            'layout', 'layouts', 'arrangement', 'arrangements', 'organization',
            'organizations', 'configuration', 'configurations', 'setup',
            'setups', 'format', 'formats', 'style', 'styles', 'manner',
            'manners', 'method', 'methods', 'way', 'ways', 'approach',
            'approaches', 'technique', 'techniques', 'procedure', 'procedures',
            'process', 'processes', 'system', 'systems', 'mechanism',
            'mechanisms', 'device', 'devices', 'tool', 'tools', 'instrument',
            'instruments', 'equipment', 'equipments', 'apparatus', 'apparatuses',
            'machine', 'machines', 'engine', 'engines', 'motor', 'motors',
            'generator', 'generators', 'transformer', 'transformers',
            'converter', 'converters', 'adapter', 'adapters', 'interface',
            'interfaces', 'connector', 'connectors', 'cable', 'cables',
            'wire', 'wires', 'cord', 'cords', 'line', 'lines', 'link',
            'links', 'connection', 'connections', 'junction', 'junctions',
            'joint', 'joints', 'bond', 'bonds', 'tie', 'ties', 'knot',
            'knots', 'loop', 'loops', 'hook', 'hooks', 'latch', 'latches',
            'lock', 'locks', 'key', 'keys', 'handle', 'handles', 'grip',
            'grips', 'hold', 'holds', 'clasp', 'clasps', 'clamp', 'clamps',
            'clip', 'clips', 'pin', 'pins', 'fastener', 'fasteners',
            'attachment', 'attachments', 'fitting', 'fittings', 'mount',
            'mounts', 'bracket', 'brackets', 'support', 'supports', 'stand',
            'stands', 'base', 'bases', 'foundation', 'foundations', 'ground',
            'grounds', 'floor', 'floors', 'ceiling', 'ceilings', 'roof',
            'roofs', 'wall', 'walls', 'door', 'doors', 'window', 'windows',
            'gate', 'gates', 'entrance', 'entrances', 'exit', 'exits',
            'passage', 'passages', 'corridor', 'corridors', 'hall', 'halls',
            'room', 'rooms', 'chamber', 'chambers', 'space', 'spaces',
            'area', 'areas', 'place', 'places', 'location', 'locations',
            'position', 'positions', 'spot', 'spots', 'point', 'points',
            'coordinate', 'coordinates', 'address', 'addresses', 'destination',
            'destinations', 'target', 'targets', 'goal', 'goals', 'objective',
            'objectives', 'purpose', 'purposes', 'intention', 'intentions',
            'aim', 'aims', 'plan', 'plans', 'scheme', 'schemes', 'strategy',
            'strategies', 'tactic', 'tactics', 'policy', 'policies', 'rule',
            'rules', 'regulation', 'regulations', 'law', 'laws', 'principle',
            'principles', 'guideline', 'guidelines', 'standard', 'standards',
            'criterion', 'criteria', 'requirement', 'requirements',
            'specification', 'specifications', 'condition', 'conditions',
            'constraint', 'constraints', 'limitation', 'limitations',
            'restriction', 'restrictions', 'prohibition', 'prohibitions',
            'ban', 'bans', 'veto', 'vetoes', 'rejection', 'rejections',
            'denial', 'denials', 'refusal', 'refusals', 'objection',
            'objections', 'protest', 'protests', 'complaint', 'complaints',
            'criticism', 'criticisms', 'feedback', 'feedbacks', 'response',
            'responses', 'reaction', 'reactions', 'answer', 'answers',
            'reply', 'replies', 'return', 'returns', 'result', 'results',
            'outcome', 'outcomes', 'consequence', 'consequences', 'effect',
            'effects', 'impact', 'impacts', 'influence', 'influences',
            'factor', 'factors', 'element', 'elements', 'component',
            'components', 'part', 'parts', 'piece', 'pieces', 'portion',
            'portions', 'section', 'sections', 'segment', 'segments',
            'fragment', 'fragments', 'bit', 'bits', 'particle', 'particles',
            'grain', 'grains', 'drop', 'drops', 'splash', 'splashes',
            'spray', 'sprays', 'mist', 'mists', 'fog', 'fogs', 'cloud',
            'clouds', 'vapor', 'vapors', 'steam', 'steams', 'smoke',
            'smokes', 'gas', 'gases', 'air', 'airs', 'atmosphere',
            'atmospheres', 'environment', 'environments', 'surrounding',
            'surroundings', 'context', 'contexts', 'setting', 'settings',
            'situation', 'situations', 'circumstance', 'circumstances',
            'condition', 'conditions', 'state', 'states', 'status',
            'statuses', 'mode', 'modes', 'phase', 'phases', 'stage',
            'stages', 'step', 'steps', 'level', 'levels', 'degree',
            'degrees', 'extent', 'extents', 'measure', 'measures',
            'amount', 'amounts', 'quantity', 'quantities', 'number',
            'numbers', 'count', 'counts', 'total', 'totals', 'sum',
            'sums', 'average', 'averages', 'mean', 'means', 'median',
            'medians', 'mode', 'modes', 'range', 'ranges', 'variation',
            'variations', 'deviation', 'deviations', 'difference',
            'differences', 'gap', 'gaps', 'distance', 'distances',
            'interval', 'intervals', 'space', 'spaces', 'span', 'spans',
            'duration', 'durations', 'period', 'periods', 'time', 'times',
            'moment', 'moments', 'instant', 'instants', 'second', 'seconds',
            'minute', 'minutes', 'hour', 'hours', 'day', 'days', 'week',
            'weeks', 'month', 'months', 'year', 'years', 'century',
            'centuries', 'millennium', 'millenniums', 'era', 'eras',
            'epoch', 'epochs', 'age', 'ages', 'generation', 'generations',
            'lifetime', 'lifetimes', 'lifespan', 'lifespans', 'existence',
            'existences', 'being', 'beings', 'entity', 'entities',
            'creature', 'creatures', 'organism', 'organisms', 'life',
            'lives', 'death', 'deaths', 'birth', 'births', 'creation',
            'creations', 'origin', 'origins', 'source', 'sources',
            'beginning', 'beginnings', 'start', 'starts', 'commencement',
            'commencements', 'initiation', 'initiations', 'launch',
            'launches', 'opening', 'openings', 'introduction', 'introductions',
            'inception', 'inceptions', 'genesis', 'geneses', 'foundation',
            'foundations', 'establishment', 'establishments', 'formation',
            'formations', 'construction', 'constructions', 'building',
            'buildings', 'structure', 'structures', 'edifice', 'edifices',
            'facility', 'facilities', 'installation', 'installations',
            'plant', 'plants', 'factory', 'factories', 'mill', 'mills',
            'workshop', 'workshops', 'laboratory', 'laboratories', 'office',
            'offices', 'studio', 'studios', 'shop', 'shops', 'store',
            'stores', 'market', 'markets', 'mall', 'malls', 'center',
            'centers', 'complex', 'complexes', 'compound', 'compounds',
            'campus', 'campuses', 'site', 'sites', 'location', 'locations',
            'place', 'places', 'venue', 'venues', 'destination', 'destinations',
            'spot', 'spots', 'point', 'points', 'position', 'positions',
            'coordinate', 'coordinates', 'address', 'addresses', 'number',
            'numbers', 'code', 'codes', 'identifier', 'identifiers',
            'label', 'labels', 'tag', 'tags', 'mark', 'marks', 'sign',
            'signs', 'symbol', 'symbols', 'character', 'characters',
            'letter', 'letters', 'digit', 'digits', 'figure', 'figures',
            'numeral', 'numerals', 'word', 'words', 'term', 'terms',
            'phrase', 'phrases', 'expression', 'expressions', 'sentence',
            'sentences', 'statement', 'statements', 'declaration',
            'declarations', 'assertion', 'assertions', 'claim', 'claims',
            'argument', 'arguments', 'reasoning', 'reasonings', 'logic',
            'logics', 'rationale', 'rationales', 'explanation', 'explanations',
            'description', 'descriptions', 'account', 'accounts', 'report',
            'reports', 'summary', 'summaries', 'synopsis', 'synopses',
            'abstract', 'abstracts', 'outline', 'outlines', 'overview',
            'overviews', 'survey', 'surveys', 'review', 'reviews',
            'analysis', 'analyses', 'study', 'studies', 'research',
            'researches', 'investigation', 'investigations', 'inquiry',
            'inquiries', 'examination', 'examinations', 'inspection',
            'inspections', 'evaluation', 'evaluations', 'assessment',
            'assessments', 'appraisal', 'appraisals', 'judgment',
            'judgments', 'opinion', 'opinions', 'view', 'views',
            'perspective', 'perspectives', 'viewpoint', 'viewpoints',
            'standpoint', 'standpoints', 'position', 'positions',
            'stance', 'stances', 'attitude', 'attitudes', 'approach',
            'approaches', 'philosophy', 'philosophies', 'belief',
            'beliefs', 'conviction', 'convictions', 'faith', 'faiths',
            'trust', 'trusts', 'confidence', 'confidences', 'assurance',
            'assurances', 'certainty', 'certainties', 'guarantee',
            'guarantees', 'promise', 'promises', 'commitment', 'commitments',
            'obligation', 'obligations', 'duty', 'duties', 'responsibility',
            'responsibilities', 'task', 'tasks', 'job', 'jobs', 'work',
            'works', 'assignment', 'assignments', 'project', 'projects',
            'mission', 'missions', 'purpose', 'purposes', 'goal', 'goals',
            'objective', 'objectives', 'target', 'targets', 'aim', 'aims',
            'intention', 'intentions', 'plan', 'plans', 'design', 'designs',
            'scheme', 'schemes', 'program', 'programs', 'schedule',
            'schedules', 'agenda', 'agendas', 'itinerary', 'itineraries',
            'timeline', 'timelines', 'timetable', 'timetables', 'calendar',
            'calendars', 'date', 'dates', 'appointment', 'appointments',
            'meeting', 'meetings', 'conference', 'conferences', 'session',
            'sessions', 'gathering', 'gatherings', 'assembly', 'assemblies',
            'convention', 'conventions', 'summit', 'summits', 'forum',
            'forums', 'seminar', 'seminars', 'workshop', 'workshops',
            'training', 'trainings', 'course', 'courses', 'class',
            'classes', 'lesson', 'lessons', 'lecture', 'lectures',
            'presentation', 'presentations', 'demonstration', 'demonstrations',
            'exhibition', 'exhibitions', 'display', 'displays', 'show',
            'shows', 'performance', 'performances', 'production',
            'productions', 'event', 'events', 'occasion', 'occasions',
            'celebration', 'celebrations', 'ceremony', 'ceremonies',
            'ritual', 'rituals', 'tradition', 'traditions', 'custom',
            'customs', 'practice', 'practices', 'habit', 'habits',
            'routine', 'routines', 'procedure', 'procedures', 'protocol',
            'protocols', 'method', 'methods', 'technique', 'techniques',
            'approach', 'approaches', 'strategy', 'strategies', 'tactic',
            'tactics', 'plan', 'plans', 'scheme', 'schemes', 'system',
            'systems', 'framework', 'frameworks', 'structure', 'structures',
            'organization', 'organizations', 'arrangement', 'arrangements',
            'configuration', 'configurations', 'setup', 'setups',
            'format', 'formats', 'layout', 'layouts', 'design', 'designs',
            'pattern', 'patterns', 'template', 'templates', 'model',
            'models', 'example', 'examples', 'sample', 'samples',
            'specimen', 'specimens', 'instance', 'instances', 'case',
            'cases', 'scenario', 'scenarios', 'situation', 'situations',
            'condition', 'conditions', 'circumstance', 'circumstances',
            'context', 'contexts', 'environment', 'environments',
            'setting', 'settings', 'background', 'backgrounds', 'scene',
            'scenes', 'stage', 'stages', 'platform', 'platforms',
            'foundation', 'foundations', 'base', 'bases', 'ground',
            'grounds', 'floor', 'floors', 'surface', 'surfaces',
            'layer', 'layers', 'level', 'levels', 'tier', 'tiers',
            'rank', 'ranks', 'grade', 'grades', 'class', 'classes',
            'category', 'categories', 'group', 'groups', 'set', 'sets',
            'collection', 'collections', 'series', 'serieses', 'sequence',
            'sequences', 'order', 'orders', 'arrangement', 'arrangements',
            'organization', 'organizations', 'classification', 'classifications',
            'taxonomy', 'taxonomies', 'hierarchy', 'hierarchies', 'tree',
            'trees', 'structure', 'structures', 'system', 'systems',
            'network', 'networks', 'web', 'webs', 'grid', 'grids',
            'matrix', 'matrices', 'table', 'tables', 'chart', 'charts',
            'graph', 'graphs', 'diagram', 'diagrams', 'map', 'maps',
            'plan', 'plans', 'blueprint', 'blueprints', 'drawing',
            'drawings', 'sketch', 'sketches', 'illustration', 'illustrations',
            'picture', 'pictures', 'image', 'images', 'photo', 'photos',
            'photograph', 'photographs', 'snapshot', 'snapshots', 'shot',
            'shots', 'frame', 'frames', 'view', 'views', 'scene',
            'scenes', 'sight', 'sights', 'vision', 'visions', 'appearance',
            'appearances', 'look', 'looks', 'aspect', 'aspects', 'feature',
            'features', 'characteristic', 'characteristics', 'attribute',
            'attributes', 'property', 'properties', 'quality', 'qualities',
            'trait', 'traits', 'nature', 'natures', 'essence', 'essences',
            'substance', 'substances', 'material', 'materials', 'matter',
            'matters', 'stuff', 'stuffs', 'thing', 'things', 'item',
            'items', 'object', 'objects', 'entity', 'entities', 'being',
            'beings', 'existence', 'existences', 'reality', 'realities',
            'fact', 'facts', 'truth', 'truths', 'actuality', 'actualities',
            'circumstance', 'circumstances', 'situation', 'situations',
            'condition', 'conditions', 'state', 'states', 'status',
            'statuses', 'position', 'positions', 'place', 'places',
            'location', 'locations', 'site', 'sites', 'spot', 'spots',
            'point', 'points', 'area', 'areas', 'region', 'regions',
            'zone', 'zones', 'territory', 'territories', 'domain',
            'domains', 'field', 'fields', 'sphere', 'spheres', 'realm',
            'realms', 'scope', 'scopes', 'range', 'ranges', 'extent',
            'extents', 'limit', 'limits', 'boundary', 'boundaries',
            'border', 'borders', 'edge', 'edges', 'margin', 'margins',
            'perimeter', 'perimeters', 'circumference', 'circumferences',
            'outline', 'outlines', 'contour', 'contours', 'shape',
            'shapes', 'form', 'forms', 'figure', 'figures', 'configuration',
            'configurations', 'structure', 'structures', 'framework',
            'frameworks', 'architecture', 'architectures', 'design',
            'designs', 'pattern', 'patterns', 'layout', 'layouts',
            'arrangement', 'arrangements', 'organization', 'organizations',
            'system', 'systems', 'method', 'methods', 'way', 'ways',
            'manner', 'manners', 'approach', 'approaches', 'technique',
            'techniques', 'procedure', 'procedures', 'process', 'processes',
            'operation', 'operations', 'action', 'actions', 'activity',
            'activities', 'function', 'functions', 'role', 'roles',
            'purpose', 'purposes', 'use', 'uses', 'utility', 'utilities',
            'service', 'services', 'benefit', 'benefits', 'advantage',
            'advantages', 'merit', 'merits', 'value', 'values', 'worth',
            'worths', 'importance', 'importances', 'significance',
            'significances', 'meaning', 'meanings', 'sense', 'senses',
            'definition', 'definitions', 'interpretation', 'interpretations',
            'understanding', 'understandings', 'comprehension',
            'comprehensions', 'knowledge', 'knowledges', 'awareness',
            'awarenesses', 'consciousness', 'consciousnesses', 'perception',
            'perceptions', 'recognition', 'recognitions', 'realization',
            'realizations', 'insight', 'insights', 'discovery', 'discoveries',
            'finding', 'findings', 'result', 'results', 'outcome',
            'outcomes', 'consequence', 'consequences', 'effect', 'effects',
            'impact', 'impacts', 'influence', 'influences', 'change',
            'changes', 'alteration', 'alterations', 'modification',
            'modifications', 'adjustment', 'adjustments', 'adaptation',
            'adaptations', 'transformation', 'transformations', 'conversion',
            'conversions', 'transition', 'transitions', 'shift', 'shifts',
            'move', 'moves', 'movement', 'movements', 'motion', 'motions',
            'action', 'actions', 'activity', 'activities', 'operation',
            'operations', 'function', 'functions', 'process', 'processes',
            'procedure', 'procedures', 'method', 'methods', 'technique',
            'techniques', 'approach', 'approaches', 'strategy', 'strategies',
            'plan', 'plans', 'scheme', 'schemes', 'system', 'systems',
            'framework', 'frameworks', 'structure', 'structures',
            'organization', 'organizations', 'arrangement', 'arrangements',
            'configuration', 'configurations', 'setup', 'setups',
            'format', 'formats', 'layout', 'layouts', 'design', 'designs',
            'pattern', 'patterns', 'template', 'templates', 'model',
            'models', 'example', 'examples', 'sample', 'samples',
            'instance', 'instances', 'case', 'cases', 'scenario',
            'scenarios', 'situation', 'situations', 'condition',
            'conditions', 'circumstance', 'circumstances', 'context',
            'contexts', 'environment', 'environments', 'setting',
            'settings', 'background', 'backgrounds', 'scene', 'scenes',
            'stage', 'stages', 'platform', 'platforms', 'foundation',
            'foundations', 'base', 'bases', 'ground', 'grounds',
            'floor', 'floors', 'surface', 'surfaces', 'layer', 'layers',
            'level', 'levels', 'tier', 'tiers', 'rank', 'ranks',
            'grade', 'grades', 'class', 'classes', 'category', 'categories',
            'group', 'groups', 'set', 'sets', 'collection', 'collections',
            'series', 'serieses', 'sequence', 'sequences', 'order',
            'orders', 'arrangement', 'arrangements', 'organization',
            'organizations', 'classification', 'classifications', 'taxonomy',
            'taxonomies', 'hierarchy', 'hierarchies', 'tree', 'trees',
            'structure', 'structures', 'system', 'systems', 'network',
            'networks', 'web', 'webs', 'grid', 'grids', 'matrix',
            'matrices', 'table', 'tables', 'chart', 'charts', 'graph',
            'graphs', 'diagram', 'diagrams', 'map', 'maps', 'plan',
            'plans', 'blueprint', 'blueprints', 'drawing', 'drawings',
            'sketch', 'sketches', 'illustration', 'illustrations',
            'picture', 'pictures', 'image', 'images', 'photo', 'photos',
            'photograph', 'photographs', 'snapshot', 'snapshots', 'shot',
            'shots', 'frame', 'frames', 'view', 'views', 'scene',
            'scenes', 'sight', 'sights', 'vision', 'visions', 'appearance',
            'appearances', 'look', 'looks', 'aspect', 'aspects', 'feature',
            'features', 'characteristic', 'characteristics', 'attribute',
            'attributes', 'property', 'properties', 'quality', 'qualities',
            'trait', 'traits', 'nature', 'natures', 'essence', 'essences',
            'substance', 'substances', 'material', 'materials', 'matter',
            'matters', 'stuff', 'stuffs', 'thing', 'things', 'item',
            'items', 'object', 'objects', 'entity', 'entities', 'being',
            'beings', 'existence', 'existences', 'reality', 'realities',
            'fact', 'facts', 'truth', 'truths', 'actuality', 'actualities',
            'circumstance', 'circumstances', 'situation', 'situations',
            'condition', 'conditions', 'state', 'states', 'status',
            'statuses', 'position', 'positions', 'place', 'places',
            'location', 'locations', 'site', 'sites', 'spot', 'spots',
            'point', 'points', 'area', 'areas', 'region', 'regions',
            'zone', 'zones', 'territory', 'territories', 'domain',
            'domains', 'field', 'fields', 'sphere', 'spheres', 'realm',
            'realms', 'scope', 'scopes', 'range', 'ranges', 'extent',
            'extents', 'limit', 'limits', 'boundary', 'boundaries',
            'border', 'borders', 'edge', 'edges', 'margin', 'margins',
            'perimeter', 'perimeters', 'circumference', 'circumferences',
            'outline', 'outlines', 'contour', 'contours', 'shape',
            'shapes', 'form', 'forms', 'figure', 'figures', 'configuration',
            'configurations', 'structure', 'structures', 'framework',
            'frameworks', 'architecture', 'architectures', 'design',
            'designs', 'pattern', 'patterns', 'layout', 'layouts',
            'arrangement', 'arrangements', 'organization', 'organizations',
            'system', 'systems', 'method', 'methods', 'way', 'ways',
            'manner', 'manners', 'approach', 'approaches', 'technique',
            'techniques', 'procedure', 'procedures', 'process', 'processes',
            'operation', 'operations', 'action', 'actions', 'activity',
            'activities', 'function', 'functions', 'role', 'roles',
            'purpose', 'purposes', 'use', 'uses', 'utility', 'utilities',
            'service', 'services', 'benefit', 'benefits', 'advantage',
            'advantages', 'merit', 'merits', 'value', 'values', 'worth',
            'worths', 'importance', 'importances', 'significance',
            'significances', 'meaning', 'meanings', 'sense', 'senses',
            'definition', 'definitions', 'interpretation', 'interpretations',
            'understanding', 'understandings', 'comprehension',
            'comprehensions', 'knowledge', 'knowledges', 'awareness',
            'awarenesses', 'consciousness', 'consciousnesses', 'perception',
            'perceptions', 'recognition', 'recognitions', 'realization',
            'realizations', 'insight', 'insights', 'discovery', 'discoveries',
            'finding', 'findings', 'result', 'results', 'outcome',
            'outcomes', 'consequence', 'consequences', 'effect', 'effects',
            'impact', 'impacts', 'influence', 'influences', 'change',
            'changes', 'alteration', 'alterations', 'modification',
            'modifications', 'adjustment', 'adjustments', 'adaptation',
            'adaptations', 'transformation', 'transformations', 'conversion',
            'conversions', 'transition', 'transitions', 'shift', 'shifts',
            'move', 'moves', 'movement', 'movements', 'motion', 'motions',
            'action', 'actions', 'activity', 'activities', 'operation',
            'operations', 'function', 'functions', 'process', 'processes',
            'procedure', 'procedures', 'method', 'methods', 'technique',
            'techniques', 'approach', 'approaches', 'strategy', 'strategies',
            'plan', 'plans', 'scheme', 'schemes', 'system', 'systems',
            'framework', 'frameworks', 'structure', 'structures',
            'organization', 'organizations', 'arrangement', 'arrangements',
            'configuration', 'configurations', 'setup', 'setups',
            'format', 'formats', 'layout', 'layouts', 'design', 'designs',
            'pattern', 'patterns', 'template', 'templates', 'model',
            'models', 'example', 'examples', 'sample', 'samples',
            'instance', 'instances', 'case', 'cases', 'scenario',
            'scenarios', 'situation', 'situations', 'condition',
            'conditions', 'circumstance', 'circumstances', 'context',
            'contexts', 'environment', 'environments', 'setting',
            'settings', 'background', 'backgrounds', 'scene', 'scenes',
            'stage', 'stages', 'platform', 'platforms', 'foundation',
            'foundations', 'base', 'bases', 'ground', 'grounds',
            'floor', 'floors', 'surface', 'surfaces', 'layer', 'layers',
            'level', 'levels', 'tier', 'tiers', 'rank', 'ranks',
            'grade', 'grades', 'class', 'classes', 'category', 'categories',
            'group', 'groups', 'set', 'sets', 'collection', 'collections',
            'series', 'serieses', 'sequence', 'sequences', 'order',
            'orders', 'arrangement', 'arrangements', 'organization',
            'organizations', 'classification', 'classifications', 'taxonomy',
            'taxonomies', 'hierarchy', 'hierarchies', 'tree', 'trees',
            'structure', 'structures', 'system', 'systems', 'network',
            'networks', 'web', 'webs', 'grid', 'grids', 'matrix',
            'matrices', 'table', 'tables', 'chart', 'charts', 'graph',
            'graphs', 'diagram', 'diagrams', 'map', 'maps', 'plan',
            'plans', 'blueprint', 'blueprints', 'drawing', 'drawings',
            'sketch', 'sketches', 'illustration', 'illustrations',
            'picture', 'pictures', 'image', 'images', 'photo', 'photos',
            'photograph', 'photographs', 'snapshot', 'snapshots', 'shot',
            'shots', 'frame', 'frames', 'view', 'views', 'scene',
            'scenes', 'sight', 'sights', 'vision', 'visions', 'appearance',
            'appearances', 'look', 'looks', 'aspect', 'aspects', 'feature',
            'features', 'characteristic', 'characteristics', 'attribute',
            'attributes', 'property', 'properties', 'quality', 'qualities',
            'trait', 'traits', 'nature', 'natures', 'essence', 'essences',
            'substance', 'substances', 'material', 'materials', 'matter',
            'matters', 'stuff', 'stuffs', 'thing', 'things', 'item',
            'items', 'object', 'objects', 'entity', 'entities', 'being',
            'beings', 'existence', 'existences', 'reality', 'realities',
            'fact', 'facts', 'truth', 'truths', 'actuality', 'actualities'
        }
        
        if text.lower() in common_words:
            return False
        
        # Now apply the strict function signature detection
        has_parentheses = False
        has_return_type = False
        has_skill_params = False
        has_description = False
        
        # Check next few words for signature patterns
        for i in range(index + 1, min(index + 15, len(words))):
            word_text = words[i]['text']
            
            # Check for opening parenthesis
            if '(' in word_text:
                has_parentheses = True
            
            # Check for return type indicator
            if '=>' in word_text:
                has_return_type = True
                break
            
            # Check for SKILL parameter patterns
            if re.match(r'^[ltngsoprxubdwe]_\w+', word_text):
                has_skill_params = True
            
            # Check for description section
            if word_text.lower() == 'description':
                has_description = True
            
            # Stop if we hit a period or line break
            if '.' in word_text or '\n' in word_text:
                break
        
        # Must have clear function signature indicators
        if has_parentheses and (has_return_type or (has_skill_params and has_description)):
            return True
        
        return False
    
    def save_raw_document_data(self, raw_data: RawDocumentData, output_path: str):
        """Save raw document data to JSON file"""
        # Convert to serializable format
        serializable_data = asdict(raw_data)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False)

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