#!/usr/bin/env python3
"""
SKILL Structured Converter: Raw JSON → Structured JSON
Converts Raw JSON data to structured SkillFunctionWithOverloads format
"""

import os
import sys
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skill_pdf_html_parser import (
    SkillFunctionWithOverloads, 
    FunctionOverload, 
    SkillParameter, 
    ParameterType,
    FunctionCategory,
    RawFunctionData,
    RawDocumentData
)

class StructuredConverter:
    """Converts Raw JSON data to structured SKILL functions"""
    
    def __init__(self):
        self.skill_keywords = {
            'function_indicators': ['procedure', 'defun', 'lambda', 'let', 'prog'],
            'parameter_keywords': ['arguments', 'args', 'parameters', 'params'],
            'return_keywords': ['returns', 'return', 'value returned', 'result'],
            'example_keywords': ['example', 'examples', 'usage', 'sample'],
            'description_keywords': ['description', 'purpose', 'summary']
        }
        
        # SKILL data type mappings
        self.data_type_patterns = {
            r'^[lg]_': 'list',
            r'^[tS]_': 'string', 
            r'^[nxf]_': 'number',
            r'^[sb]_': 'symbol',
            r'^[ao]_': 'object',
            r'^[pr]_': 'port',
            r'^[ud]_': 'function',
            r'^[we]_': 'window'
        }
        
        # Special function patterns
        self.special_function_patterns = {
            'car_cdr_series': r'^c[ad]*r$',
            'vi_series': r'^vi[il]?$',
            'make_template': r'^make_\w+$',
            'copy_template': r'^copy_\w+$',
            'setf_helper': r'^setf_\w+$'
        }
    
    def convert_raw_document_to_structured(self, raw_data: RawDocumentData) -> List[SkillFunctionWithOverloads]:
        """Convert raw document data to structured functions"""
        
        print(f"🔄 Converting {len(raw_data.functions)} raw functions to structured format...")
        
        structured_functions = []
        
        for raw_func in raw_data.functions:
            try:
                structured_func = self.convert_raw_function_to_structured(raw_func, raw_data)
                if structured_func:
                    structured_functions.append(structured_func)
            except Exception as e:
                print(f"⚠️  Error converting function '{raw_func.name}': {e}")
                continue
        
        # Post-process for special functions and deduplication
        structured_functions = self.post_process_functions(structured_functions)
        
        print(f"✅ Converted {len(structured_functions)} structured functions")
        return structured_functions
    
    def convert_raw_function_to_structured(self, raw_func: RawFunctionData, raw_data: RawDocumentData) -> Optional[SkillFunctionWithOverloads]:
        """Convert a single raw function to structured format"""
        
        # Filter out non-function entries
        if not self.is_valid_function(raw_func):
            return None
        
        # Extract function signature and parameters
        overloads = self.extract_function_overloads(raw_func)
        if not overloads:
            # Create a basic overload if none found
            overloads = [self.create_basic_overload(raw_func)]
        
        # Extract description
        description = self.extract_description(raw_func)
        
        # Extract arguments description
        arguments_description = self.extract_arguments_description(raw_func)
        
        # Extract examples
        examples = self.extract_examples(raw_func)
        
        # Determine category
        category = self.determine_category(raw_func, raw_data)
        
        # Detect special function type
        special_type = self.detect_special_function_type(raw_func.name)
        
        return SkillFunctionWithOverloads(
            name=raw_func.name,
            overloads=overloads,
            description=description,
            arguments_description=arguments_description,
            examples=examples,
            page=raw_func.page_number,
            category=category,
            related_functions=[],
            special_type=special_type,
            raw_data=raw_func
        )
    
    def is_valid_function(self, raw_func: RawFunctionData) -> bool:
        """Determine if raw function data represents a valid SKILL function"""
        
        name = raw_func.name.strip()
        
        # Basic name validation
        if not name or len(name) < 2:
            return False
        
        # Must be valid identifier
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', name):
            return False
        
        # Skip common non-function words (expanded list)
        non_function_words = {
            'the', 'and', 'for', 'are', 'not', 'you', 'can', 'may', 'will', 'this',
            'that', 'with', 'from', 'they', 'have', 'been', 'were', 'said', 'each',
            'all', 'any', 'more', 'than', 'only', 'other', 'such', 'time', 'very',
            'what', 'when', 'where', 'who', 'how', 'why', 'way', 'many', 'much',
            'page', 'chapter', 'section', 'example', 'note', 'see', 'also', 'reference',
            'version', 'product', 'august', 'copyright', 'reserved', 'rights', 'cadence',
            'print', 'one', 'two', 'three', 'four', 'five', 'use', 'used', 'using',
            'does', 'did', 'information', 'document', 'contains', 'subject', 'following',
            'conditions', 'publication', 'customer', 'agreement', 'modified', 'authorized',
            'copy', 'include', 'original', 'trademark', 'proprietary', 'notices', 'permission',
            'statement', 'contained', 'development', 'products', 'software', 'internal',
            'external', 'benefit', 'party', 'consideration', 'disclaimer', 'change',
            'notice', 'represent', 'commitment', 'part', 'explicitly', 'set', 'forth',
            'representations', 'warranties', 'completeness', 'accuracy', 'usefulness',
            'warrant', 'infringe', 'third', 'assume', 'liability', 'damages', 'costs',
            'kind', 'result', 'restricted', 'duplication', 'disclosure', 'government',
            'restrictions', 'successor', 'united', 'states', 'america', 'design', 'systems',
            'inc', 'ave', 'san', 'jose', 'usa', 'open', 'initiative', 'trademarks',
            'registered', 'countries', 'permission', 'contained', 'attributed', 'appropriate',
            'symbol', 'queries', 'regarding', 'contact', 'corporate', 'legal', 'department',
            'address', 'shown', 'above', 'call', 'property', 'respective', 'holders',
            'protected', 'law', 'international', 'treaties', 'trade', 'secrets', 'owned',
            'unauthorized', 'reproduction', 'distribution', 'portion', 'civil', 'criminal',
            'penalties', 'except', 'specified', 'copied', 'reproduced', 'published',
            'uploaded', 'posted', 'transmitted', 'distributed', 'prior', 'written',
            'unless', 'otherwise', 'agreed', 'writing', 'grants', 'customers', 'hard',
            'scope', 'licensing', 'requirements', 'related', 'documentation', 'whats',
            'new', 'installation', 'environment', 'infrastructure', 'books', 'additional',
            'learning', 'resources', 'video', 'library', 'virtuoso', 'videos', 'book',
            'rapid', 'adoption', 'kits', 'help', 'support', 'facilities', 'feedback',
            'about', 'understanding', 'code', 'examples', 'sample', 'accessing', 'api',
            'typographic', 'syntax', 'conventions', 'identifiers', 'denote', 'data',
            'types', 'contents', 'preface', 'list', 'functions'
        }
        
        if name.lower() in non_function_words:
            return False
        
        # Skip single digit numbers
        if re.match(r'^\d+$', name):
            return False
        
        # Must be from pages with actual function content (page 31 onwards for sklangref)
        if raw_func.page_number < 31:
            return False
        
        # Check for function-like signatures
        signature = raw_func.raw_signature.lower()
        if '(' in signature and ('=>' in signature or 'return' in signature):
            return True
        
        # Check for function description patterns
        description = raw_func.raw_description.lower()
        if any(keyword in description for keyword in ['function', 'procedure', 'returns', 'arguments']):
            return True
        
        # Check for SKILL-specific patterns
        if any(pattern in signature for pattern in ['l_', 't_', 'n_', 'g_', 's_']):
            return True
        
        # Check context for function-like patterns
        context = (raw_func.context_before + ' ' + raw_func.context_after).lower()
        if any(pattern in context for pattern in ['function', 'procedure', 'returns', 'arguments']):
            return True
        
        # Default to false for safety
        return False
    
    def extract_function_overloads(self, raw_func: RawFunctionData) -> List[FunctionOverload]:
        """Extract function overloads from raw signature"""
        
        overloads = []
        signature = raw_func.raw_signature
        
        # Look for multiple signatures separated by common delimiters
        signature_patterns = [
            signature,  # Primary signature
        ]
        
        # Try to find additional signatures in description
        desc_signatures = re.findall(r'[a-zA-Z][a-zA-Z0-9_]*\s*\([^)]*\)\s*=>', raw_func.raw_description)
        signature_patterns.extend(desc_signatures)
        
        for sig_pattern in signature_patterns:
            if sig_pattern.strip():
                overload = self.parse_signature_to_overload(sig_pattern, raw_func)
                if overload:
                    overloads.append(overload)
        
        return overloads
    
    def parse_signature_to_overload(self, signature: str, raw_func: RawFunctionData) -> Optional[FunctionOverload]:
        """Parse a signature string to create a FunctionOverload"""
        
        # Clean up signature
        signature = signature.strip()
        
        # Extract function name and parameters
        func_match = re.match(r'([a-zA-Z][a-zA-Z0-9_]*)\s*\((.*?)\)', signature)
        if not func_match:
            return None
        
        func_name = func_match.group(1)
        params_str = func_match.group(2)
        
        # Extract return type
        return_type = self.extract_return_type(signature)
        
        # Parse parameters
        parameters = self.parse_parameters(params_str)
        
        return FunctionOverload(
            signature=signature,
            parameters=parameters,
            return_type=return_type,
            raw_signature=raw_func.raw_signature
        )
    
    def parse_parameters(self, params_str: str) -> List[SkillParameter]:
        """Parse parameter string into SkillParameter objects"""
        
        if not params_str.strip():
            return []
        
        parameters = []
        
        # Split parameters by whitespace and commas
        param_tokens = re.split(r'[,\s]+', params_str.strip())
        param_tokens = [token.strip() for token in param_tokens if token.strip()]
        
        position = 0
        for token in param_tokens:
            # Skip empty tokens and common separators
            if not token or token in ['&', '|', '=>']:
                continue
            
            param_type = self.determine_parameter_type(token)
            data_type = self.determine_data_type(token)
            
            # Clean parameter name
            param_name = re.sub(r'[^\w_]', '', token)
            
            if param_name:
                parameter = SkillParameter(
                    name=param_name,
                    param_type=param_type,
                    data_type=data_type,
                    position=position
                )
                parameters.append(parameter)
                position += 1
        
        return parameters
    
    def determine_parameter_type(self, token: str) -> ParameterType:
        """Determine parameter type from token"""
        
        if token.startswith('[') and token.endswith(']'):
            return ParameterType.OPTIONAL
        elif token.startswith('?'):
            return ParameterType.KEYWORD
        elif '...' in token:
            return ParameterType.VARIADIC
        else:
            return ParameterType.REQUIRED
    
    def determine_data_type(self, token: str) -> str:
        """Determine data type from parameter token"""
        
        for pattern, data_type in self.data_type_patterns.items():
            if re.match(pattern, token):
                return data_type
        
        return 'general'
    
    def extract_return_type(self, signature: str) -> str:
        """Extract return type from signature"""
        
        # Look for => pattern
        return_match = re.search(r'=>\s*([^=>\s]+)', signature)
        if return_match:
            return return_match.group(1)
        
        return "t"  # Default SKILL return type
    
    def extract_description(self, raw_func: RawFunctionData) -> str:
        """Extract clean description from raw function data"""
        
        description = raw_func.raw_description.strip()
        
        # Clean up common artifacts
        description = re.sub(r'\s+', ' ', description)  # Normalize whitespace
        description = re.sub(r'^[^a-zA-Z]*', '', description)  # Remove leading non-letters
        description = re.sub(r'[^a-zA-Z\s]*$', '', description)  # Remove trailing non-letters
        
        # Truncate if too long
        if len(description) > 500:
            description = description[:500] + "..."
        
        return description
    
    def extract_arguments_description(self, raw_func: RawFunctionData) -> Dict[str, str]:
        """Extract argument descriptions from raw function data"""
        
        arguments_desc = {}
        
        # Look for argument descriptions in raw_parameters
        params_text = raw_func.raw_parameters
        if params_text:
            # Simple pattern to extract arg descriptions
            arg_matches = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*[:\-]?\s*([^.]+)', params_text)
            for arg_name, arg_desc in arg_matches:
                if len(arg_desc.strip()) > 10:  # Only meaningful descriptions
                    arguments_desc[arg_name] = arg_desc.strip()
        
        return arguments_desc
    
    def extract_examples(self, raw_func: RawFunctionData) -> List[str]:
        """Extract examples from raw function data"""
        
        examples = []
        
        examples_text = raw_func.raw_examples
        if examples_text:
            # Split by common example delimiters
            example_parts = re.split(r'(?:\n|^)\s*(?:Example|==>|=>|\|\s)', examples_text)
            
            for part in example_parts:
                part = part.strip()
                if part and len(part) > 10:
                    # Clean up the example
                    part = re.sub(r'\s+', ' ', part)
                    examples.append(part)
        
        return examples[:3]  # Limit to 3 examples
    
    def determine_category(self, raw_func: RawFunctionData, raw_data: RawDocumentData) -> Optional[FunctionCategory]:
        """Determine function category based on context"""
        
        # Look for category context
        category_text = raw_func.category_context
        if not category_text:
            return None
        
        # Find matching category from raw_data
        for category_info in raw_data.categories:
            if category_info.get('text') == category_text:
                return FunctionCategory(
                    document_name=raw_data.metadata.get('document_name', ''),
                    category_path=[category_text],
                    level=category_info.get('level', 1),
                    full_path=f"{raw_data.metadata.get('document_name', '')} > {category_text}",
                    font_size=category_info.get('font_size', 0.0),
                    page_number=category_info.get('page_number', 0)
                )
        
        return None
    
    def detect_special_function_type(self, function_name: str) -> Optional[str]:
        """Detect special function types"""
        
        for special_type, pattern in self.special_function_patterns.items():
            if re.match(pattern, function_name):
                return special_type
        
        return None
    
    def create_basic_overload(self, raw_func: RawFunctionData) -> FunctionOverload:
        """Create a basic overload when no signature is found"""
        
        return FunctionOverload(
            signature=f"{raw_func.name}(...)",
            parameters=[],
            return_type="t",
            raw_signature=raw_func.raw_signature
        )
    
    def post_process_functions(self, functions: List[SkillFunctionWithOverloads]) -> List[SkillFunctionWithOverloads]:
        """Post-process functions for deduplication and enhancement"""
        
        print("🔄 Post-processing functions...")
        
        # Deduplicate by function name
        seen_names = set()
        deduplicated = []
        
        for func in functions:
            if func.name not in seen_names:
                deduplicated.append(func)
                seen_names.add(func.name)
        
        print(f"✅ Deduplicated {len(functions)} → {len(deduplicated)} functions")
        
        # Group related functions
        deduplicated = self.group_related_functions(deduplicated)
        
        return deduplicated
    
    def group_related_functions(self, functions: List[SkillFunctionWithOverloads]) -> List[SkillFunctionWithOverloads]:
        """Group related functions (e.g., car/cdr series)"""
        
        # Group car/cdr series
        car_cdr_functions = []
        other_functions = []
        
        for func in functions:
            if func.special_type == 'car_cdr_series':
                car_cdr_functions.append(func)
            else:
                other_functions.append(func)
        
        # Add related function references for car/cdr series
        car_cdr_names = [f.name for f in car_cdr_functions]
        for func in car_cdr_functions:
            func.related_functions = [name for name in car_cdr_names if name != func.name]
        
        return other_functions + car_cdr_functions
    
    def save_structured_data(self, structured_functions: List[SkillFunctionWithOverloads], output_path: str):
        """Save structured functions to JSON file"""
        
        print(f"💾 Saving structured data to {output_path}")
        
        # Convert to serializable format
        serializable_functions = []
        for func in structured_functions:
            func_data = asdict(func)
            
            # Convert enums to strings
            for overload in func_data['overloads']:
                for param in overload['parameters']:
                    if hasattr(param['param_type'], 'value'):
                        param['param_type'] = param['param_type'].value
                    else:
                        param['param_type'] = str(param['param_type'])
            
            serializable_functions.append(func_data)
        
        # Create output structure
        output_data = {
            'metadata': {
                'converter_version': '1.0.0',
                'total_functions': len(structured_functions),
                'conversion_timestamp': __import__('datetime').datetime.now().isoformat(),
                'function_types': {
                    'regular': len([f for f in structured_functions if not f.special_type]),
                    'special': len([f for f in structured_functions if f.special_type])
                }
            },
            'functions': serializable_functions
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Structured data saved with {len(structured_functions)} functions")

def main():
    """Main converter function for testing"""
    
    # Test with existing raw JSON
    raw_json_path = "/mnt/d/git/VSCodeExtension-SKILL/docs/raw_extraction/sklangref_raw.json"
    output_path = "/mnt/d/git/VSCodeExtension-SKILL/docs/structured_extraction/sklangref_structured.json"
    
    if not os.path.exists(raw_json_path):
        print(f"❌ Raw JSON file not found: {raw_json_path}")
        return 1
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print("🚀 Starting Raw → Structured conversion...")
    
    # Load raw data
    with open(raw_json_path, 'r', encoding='utf-8') as f:
        raw_data_dict = json.load(f)
    
    # Convert to RawDocumentData object
    raw_data = RawDocumentData(
        metadata=raw_data_dict['metadata'],
        pages=raw_data_dict['pages'],
        functions=[RawFunctionData(**func) for func in raw_data_dict['functions']],
        categories=raw_data_dict['categories'],
        raw_text=raw_data_dict['raw_text'],
        html_content=raw_data_dict['html_content']
    )
    
    # Convert to structured format
    converter = StructuredConverter()
    structured_functions = converter.convert_raw_document_to_structured(raw_data)
    
    # Save results
    converter.save_structured_data(structured_functions, output_path)
    
    print(f"✅ Conversion complete!")
    print(f"   Input: {len(raw_data.functions)} raw functions")
    print(f"   Output: {len(structured_functions)} structured functions")
    print(f"   Saved to: {output_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())