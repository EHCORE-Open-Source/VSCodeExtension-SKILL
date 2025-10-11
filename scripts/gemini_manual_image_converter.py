#!/usr/bin/env python3
"""
SKILL Manual Image to Database JSON Converter

This tool converts SKILL manual images (PNG) to database-ready JSON format
using Google Gemini API for intelligent extraction.

Key Features:
- Database-ready JSON output (100% aligned with DATABASE_JSON_SCHEMA.md)
- Automatic type prefix extraction using skill_type_utils.py
- Parameter type classification (required/keyword/optional/rest)
- Category page detection and handling
- Multi-page function support
- Overload detection

Usage:
    # Convert single image
    python3 gemini_manual_image_converter.py \
        --image docs/cadence_manual/images/sklangref/sklangref-034.png \
        --manual-code sklangref \
        --product-code SKILL \
        --version 6.1.8 \
        --document-title "Cadence SKILL Language Reference" \
        --output test_output/append.json

    # Convert page range
    python3 gemini_manual_image_converter.py \
        --range sklangref-031 sklangref-038 \
        --image-dir docs/cadence_manual/images/sklangref/ \
        --manual-code sklangref \
        --product-code SKILL \
        --version 6.1.8 \
        --document-title "Cadence SKILL Language Reference" \
        --output-dir test_output/

Author: Claude Code
Version: 1.0
Date: 2025-10-11
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from PIL import Image
from google import genai

# Import skill_type_utils
from skill_type_utils import (
    extract_type_prefix,
    classify_parameter_type,
    parse_syntax_arguments,
    parse_syntax_string,
    ParameterType
)

# Configuration
GEMINI_MODEL = "gemini-2.5-flash-lite"  # Fast model for initial testing
API_KEY_ENV = "GEMINI_API_KEY"
BASE_URL_ENV = "GOOGLE_GEMINI_BASE_URL"  # Custom base URL (optional)


class SkillManualConverter:
    """
    Converter for SKILL manual images to database-ready JSON format
    """

    def __init__(self, api_key: Optional[str] = None, manual_metadata: Optional[Dict] = None, base_url: Optional[str] = None):
        """
        Initialize the converter with Gemini API client

        Args:
            api_key: Gemini API key (if None, reads from environment variable)
            manual_metadata: Manual metadata dictionary containing:
                - manual_code: str (e.g., "sklangref")
                - product_code: str (e.g., "SKILL")
                - product_hierarchy_level: int (0=Core, 1=Family, 2=Product)
                - version: str (e.g., "6.1.8")
                - document_title: str
                - source_type: str (default: "manual")
            base_url: Custom Gemini API base URL (if None, reads from environment variable)
        """
        self.api_key = api_key or os.getenv(API_KEY_ENV)
        if not self.api_key:
            raise ValueError(f"API key not found. Set {API_KEY_ENV} environment variable or pass it as argument.")

        # Get base URL from parameter or environment variable
        self.base_url = base_url or os.getenv(BASE_URL_ENV)

        # Initialize Gemini client with custom base URL if provided
        if self.base_url:
            self.client = genai.Client(api_key=self.api_key, http_options={'base_url': self.base_url})
        else:
            self.client = genai.Client(api_key=self.api_key)

        self.manual_metadata = manual_metadata or {}

        # Ensure source_type is set
        if 'source_type' not in self.manual_metadata:
            self.manual_metadata['source_type'] = 'manual'

    def detect_page_type(self, image_path: str) -> str:
        """
        Detect if a page is a category page or function page

        Args:
            image_path: Path to the PNG image file

        Returns:
            'category', 'function', or 'other'
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        image = Image.open(image_path)

        prompt = """
Analyze this SKILL documentation page and determine its type.

Page Types:
1. CATEGORY PAGE: Shows a list of functions under a category heading (e.g., "List Functions")
2. FUNCTION PAGE: Detailed documentation for a specific function (syntax, arguments, examples)
3. OTHER: Table of contents, introduction, or other content

Return ONLY one word: "category", "function", or "other"
"""

        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, image]
        )

        page_type = response.text.strip().lower()
        if page_type not in ['category', 'function', 'other']:
            page_type = 'other'

        return page_type

    def extract_category_page(self, image_path: str) -> Dict:
        """
        Extract category information from a category page

        Args:
            image_path: Path to the PNG image file

        Returns:
            Dictionary containing:
                - page_type: 'category'
                - page_number: int
                - category_name: str
                - category_hierarchy: List[str]
                - functions_list: List[str]
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        image = Image.open(image_path)

        prompt = """
Analyze this SKILL category/section page and extract the following information in JSON format:

{
  "category_name": "the main category name (e.g., 'List Functions')",
  "category_hierarchy": ["parent category if any", "current category"],
  "functions_list": ["function1", "function2", "..."],
  "page_number": page number if visible
}

Extract all visible function names listed under this category.
Return ONLY the JSON object, no additional text.
"""

        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, image]
        )

        # Parse JSON response
        try:
            response_text = self._clean_json_response(response.text)
            category_data = json.loads(response_text)

            # Add page type
            category_data['page_type'] = 'category'

            # Extract page number from filename if not in data
            if not category_data.get('page_number'):
                page_match = re.search(r'-(\d+)\.png$', image_path)
                if page_match:
                    category_data['page_number'] = int(page_match.group(1))

            return category_data

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse JSON response for category page {image_path}")
            print(f"Response: {response.text}")
            return {
                "page_type": "category",
                "error": "JSON parsing failed",
                "raw_response": response.text
            }

    def extract_function_page(self, image_path: str, category: Optional[str] = None) -> Dict:
        """
        Extract function information from a function page

        Args:
            image_path: Path to the PNG image file
            category: Optional category name to include in the result

        Returns:
            Dictionary containing function information in database-ready format
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        image = Image.open(image_path)

        # Construct detailed prompt for database-ready extraction
        prompt = """
Analyze this SKILL function documentation page and extract complete information in JSON format.

CRITICAL SYNTAX REQUIREMENTS:
1. Use "=>" (not "->") to separate function call from return value
2. Preserve ALL syntax markers EXACTLY as shown:
   - Keep '?' for keyword parameters (e.g., "?expr l_exprList")
   - Keep '[' and ']' for optional parameters (e.g., "[ x_index ]")
   - Keep '...' for rest parameters (e.g., "... g_args")
3. Format: "functionName(param1 param2 [ optionalParam ]) => returnType"

Extract the following information:

{
  "function_name": "exact function name from the heading",
  "syntax": "complete syntax in format: functionName(params) => returnType",
  "description": "detailed description of what the function does",
  "arguments": [
    {
      "name": "parameter name with type prefix (e.g., l_list, g_arg)",
      "description": "parameter description from Arguments section",
      "keyword_name": "keyword if this is a keyword parameter (e.g., 'expr' for ?expr)"
    }
  ],
  "return_value": "return type and description from Value Returned section",
  "examples": [
    {
      "code": "example code from Examples section",
      "description": "what this example demonstrates"
    }
  ],
  "notes": "any warnings, notes, or additional information",
  "page_number": integer page number if visible at bottom of page,
  "overloads": [
    {
      "syntax": "alternative syntax if function has multiple signatures => returnType",
      "description": "description for this overload"
    }
  ]
}

IMPORTANT:
- Extract function name from the heading (e.g., "append1" not "append")
- Use "=>" not "->" in syntax
- page_number must be an integer (e.g., 34 not "34")
- If the function has multiple syntaxes/overloads, list them all in the "overloads" array

Return ONLY the JSON object, no additional text or markdown formatting.
"""

        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, image]
        )

        # Parse JSON response
        try:
            response_text = self._clean_json_response(response.text)
            gemini_data = json.loads(response_text)

            # Convert to database-ready format
            function_data = self._convert_to_database_format(
                gemini_data,
                image_path,
                category
            )

            return function_data

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse JSON response for {image_path}")
            print(f"Response: {response.text}")
            return {
                "error": "JSON parsing failed",
                "raw_response": response.text,
                "source_image": os.path.basename(image_path)
            }

    def _clean_json_response(self, response_text: str) -> str:
        """
        Clean Gemini response text to extract JSON

        Args:
            response_text: Raw response text from Gemini

        Returns:
            Cleaned JSON string
        """
        text = response_text.strip()

        # Remove markdown code blocks
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]

        if text.endswith('```'):
            text = text[:-3]

        return text.strip()

    def _convert_to_database_format(
        self,
        gemini_data: Dict,
        image_path: str,
        category: Optional[str] = None
    ) -> Dict:
        """
        Convert Gemini extraction result to database-ready JSON format

        Args:
            gemini_data: Raw data from Gemini API
            image_path: Source image path
            category: Optional category name

        Returns:
            Database-ready function dictionary
        """
        function_name = gemini_data.get('function_name', 'unknown')

        # Parse syntax string
        syntax_full = gemini_data.get('syntax', '')
        syntax_string, return_syntax = parse_syntax_string(syntax_full)

        # Process primary syntax arguments using skill_type_utils
        arguments = self._process_arguments(
            syntax_string,
            gemini_data.get('arguments', [])
        )

        # Process return values
        return_values = self._process_return_values(
            return_syntax,
            gemini_data.get('return_value', '')
        )

        # Process overloads
        overloads = []
        for overload_data in gemini_data.get('overloads', []):
            overload_syntax = overload_data.get('syntax', '')
            overload_call, overload_ret = parse_syntax_string(overload_syntax)

            overload_args = self._process_arguments(
                overload_call,
                overload_data.get('arguments', [])
            )

            overload_rets = self._process_return_values(
                overload_ret,
                overload_data.get('return_value', '')
            )

            overloads.append({
                "syntax_string": overload_call,
                "return_syntax": overload_ret,
                "description": overload_data.get('description', ''),
                "arguments": overload_args,
                "return_values": overload_rets
            })

        # Process examples
        examples = []
        for idx, ex in enumerate(gemini_data.get('examples', [])):
            examples.append({
                "code": ex.get('code', ''),
                "description": ex.get('description', ''),
                "position": idx
            })

        # Extract page number
        page_num = gemini_data.get('page_number')
        if not page_num:
            page_match = re.search(r'-(\d+)\.png$', image_path)
            if page_match:
                page_num = int(page_match.group(1))

        # Calculate extraction confidence
        confidence = self._calculate_confidence(gemini_data, arguments, return_values)

        # Determine if needs review
        needs_review = confidence < 0.85 or not gemini_data.get('description')

        # Build database-ready function object
        function_obj = {
            "function_name": function_name,
            "category": category or gemini_data.get('category', 'Uncategorized'),
            "category_hierarchy": [category] if category else [],

            "primary_syntax": {
                "syntax_string": syntax_string,
                "return_syntax": return_syntax,
                "description": gemini_data.get('description', ''),
                "arguments": arguments,
                "return_values": return_values
            },

            "overloads": overloads,

            "description": gemini_data.get('description', ''),
            "notes": gemini_data.get('notes'),

            "examples": examples,

            "aliases": [],

            "availability": {
                "product_code": self.manual_metadata.get('product_code'),
                "product_release_id": None,
                "status": "active"
            },

            "sources": {
                "source_file": f"docs/cadence_manual/{self.manual_metadata.get('manual_code', 'unknown')}.pdf",
                "source_images": [os.path.basename(image_path)],
                "start_page": page_num,
                "end_page": page_num
            },

            "metadata": {
                "verified": False,
                "extraction_confidence": confidence,
                "needs_review": needs_review,
                "parser_version": "1.0"
            }
        }

        return function_obj

    def _process_arguments(
        self,
        syntax_string: str,
        gemini_arguments: List[Dict]
    ) -> List[Dict]:
        """
        Process arguments using skill_type_utils and Gemini descriptions

        Args:
            syntax_string: Function call syntax (e.g., "append(l_list1 l_list2)")
            gemini_arguments: Argument descriptions from Gemini

        Returns:
            List of database-ready argument dictionaries
        """
        # Parse arguments using skill_type_utils
        parsed_args = parse_syntax_arguments(syntax_string)

        # Create description lookup map
        desc_map = {}
        for arg in gemini_arguments:
            arg_name = arg.get('name', '').strip()
            # Clean the name for lookup
            clean_name = arg_name.replace('?', '').replace('[', '').replace(']', '').strip()
            # Handle keyword parameters
            if ' ' in clean_name:
                clean_name = clean_name.split()[-1]
            desc_map[clean_name] = arg.get('description', '')

        # Merge parsed args with descriptions
        result = []
        for arg in parsed_args:
            arg_name = arg['name']
            description = desc_map.get(arg_name, '')

            result.append({
                "name": arg_name,
                "type_prefix": arg['type_prefix'],
                "type_description": arg['type_description'],
                "description": description,
                "parameter_type": arg['parameter_type'],
                "position": arg['position'],
                "is_keyword": arg['is_keyword'],
                "default_value": arg.get('default_value')
            })

        return result

    def _process_return_values(
        self,
        return_syntax: str,
        return_description: str
    ) -> List[Dict]:
        """
        Process return values

        Args:
            return_syntax: Return syntax (e.g., "l_result", "t/nil")
            return_description: Return value description from Gemini

        Returns:
            List of database-ready return value dictionaries
        """
        # Handle special cases
        if '/' in return_syntax:
            # Multiple return types (e.g., "t/nil")
            return_types = return_syntax.split('/')
        else:
            return_types = [return_syntax]

        result = []
        for idx, ret_type in enumerate(return_types):
            ret_type = ret_type.strip()
            type_prefix, type_desc = extract_type_prefix(ret_type)

            result.append({
                "type_name": ret_type,
                "type_prefix": type_prefix,
                "type_description": type_desc,
                "description": return_description,
                "position": idx
            })

        return result

    def _calculate_confidence(
        self,
        gemini_data: Dict,
        arguments: List[Dict],
        return_values: List[Dict]
    ) -> float:
        """
        Calculate extraction confidence score

        Args:
            gemini_data: Raw Gemini data
            arguments: Processed arguments
            return_values: Processed return values

        Returns:
            Confidence score (0.0 - 1.0)
        """
        score = 0.0
        max_score = 0.0

        # Function name (required)
        max_score += 0.2
        if gemini_data.get('function_name'):
            score += 0.2

        # Syntax (required)
        max_score += 0.2
        if gemini_data.get('syntax'):
            score += 0.2

        # Description (important)
        max_score += 0.2
        if gemini_data.get('description'):
            score += 0.2

        # Arguments (important)
        max_score += 0.15
        if arguments and all(arg.get('type_prefix') != 'g' or '_' not in arg.get('name', '') for arg in arguments):
            score += 0.15
        elif arguments:
            score += 0.10  # Partial credit

        # Return values (important)
        max_score += 0.1
        if return_values:
            score += 0.1

        # Examples (nice to have)
        max_score += 0.1
        if gemini_data.get('examples'):
            score += 0.1

        # Notes (optional)
        max_score += 0.05
        if gemini_data.get('notes'):
            score += 0.05

        return round(score / max_score if max_score > 0 else 0.0, 2)

    def convert_page(self, image_path: str, category: Optional[str] = None) -> Dict:
        """
        Convert a single page (auto-detect type)

        Args:
            image_path: Path to the PNG image file
            category: Optional category name

        Returns:
            Dictionary containing extracted data
        """
        page_type = self.detect_page_type(image_path)

        if page_type == 'category':
            return self.extract_category_page(image_path)
        elif page_type == 'function':
            return self.extract_function_page(image_path, category)
        else:
            return {
                "page_type": "other",
                "source_image": os.path.basename(image_path),
                "message": "Not a category or function page"
            }

    def save_to_json(self, functions: List[Dict], output_path: str):
        """
        Save functions to JSON file with manual metadata

        Args:
            functions: List of function dictionaries
            output_path: Output JSON file path
        """
        output_data = {
            "manual_metadata": {
                **self.manual_metadata,
                "total_functions": len(functions),
                "processing_timestamp": datetime.now().isoformat() + "Z"
            },
            "functions": functions
        }

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved {len(functions)} function(s) to: {output_path}")


def merge_duplicate_functions(functions: List[Dict]) -> List[Dict]:
    """
    Merge duplicate function entries (from multi-page documentation)

    Args:
        functions: List of function dictionaries that may contain duplicates

    Returns:
        List of merged function dictionaries

    Merging strategy:
    - Keep overloads from the first occurrence (usually the syntax page)
    - Merge examples from all occurrences
    - Combine source_images
    - Use the most complete description
    - Update page range (start_page, end_page)
    """
    # Group functions by name
    function_groups = {}
    for func in functions:
        func_name = func.get('function_name', 'unknown')
        if func_name not in function_groups:
            function_groups[func_name] = []
        function_groups[func_name].append(func)

    merged_functions = []

    for func_name, func_list in function_groups.items():
        if len(func_list) == 1:
            # No duplicates, keep as-is
            merged_functions.append(func_list[0])
        else:
            # Merge multiple occurrences
            print(f"  ⚙️  Merging {len(func_list)} occurrences of '{func_name}'")
            merged = merge_function_entries(func_list)
            merged_functions.append(merged)

    return merged_functions


def merge_function_entries(func_list: List[Dict]) -> Dict:
    """
    Merge multiple entries of the same function

    Args:
        func_list: List of function dictionaries with the same function_name

    Returns:
        Single merged function dictionary
    """
    # Start with the first entry as base
    merged = func_list[0].copy()

    # Collect all overloads (prefer non-empty ones)
    all_overloads = []
    for func in func_list:
        overloads = func.get('overloads', [])
        if overloads:
            all_overloads.extend(overloads)

    # Deduplicate overloads by syntax_string
    seen_syntaxes = set()
    unique_overloads = []
    for overload in all_overloads:
        syntax = overload.get('syntax_string', '')
        if syntax and syntax not in seen_syntaxes:
            seen_syntaxes.add(syntax)
            unique_overloads.append(overload)

    merged['overloads'] = unique_overloads

    # Merge examples
    all_examples = []
    for func in func_list:
        examples = func.get('examples', [])
        all_examples.extend(examples)

    # Reposition examples
    for idx, ex in enumerate(all_examples):
        ex['position'] = idx

    merged['examples'] = all_examples

    # Use the longest description (most complete)
    descriptions = [f.get('description', '') for f in func_list]
    merged['description'] = max(descriptions, key=len) if descriptions else ''

    # Merge notes (combine non-empty notes)
    notes_list = [f.get('notes') for f in func_list if f.get('notes')]
    if notes_list:
        merged['notes'] = '\n\n'.join(notes_list)

    # Merge source information
    all_images = []
    start_pages = []
    end_pages = []

    for func in func_list:
        sources = func.get('sources', {})
        images = sources.get('source_images', [])
        all_images.extend(images)

        if sources.get('start_page'):
            start_pages.append(sources['start_page'])
        if sources.get('end_page'):
            end_pages.append(sources['end_page'])

    merged['sources']['source_images'] = list(dict.fromkeys(all_images))  # Remove duplicates, preserve order
    merged['sources']['start_page'] = min(start_pages) if start_pages else None
    merged['sources']['end_page'] = max(end_pages) if end_pages else None

    # Update extraction confidence (average of all occurrences)
    confidences = [f.get('metadata', {}).get('extraction_confidence', 0.0) for f in func_list]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    merged['metadata']['extraction_confidence'] = round(avg_confidence, 2)

    # Mark as verified if any occurrence was verified
    verified = any(f.get('metadata', {}).get('verified', False) for f in func_list)
    merged['metadata']['verified'] = verified

    # Needs review if any occurrence needs review
    needs_review = any(f.get('metadata', {}).get('needs_review', False) for f in func_list)
    merged['metadata']['needs_review'] = needs_review

    return merged


def main():
    parser = argparse.ArgumentParser(
        description='Convert SKILL manual images to database-ready JSON',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Input options
    parser.add_argument(
        '--image',
        help='Path to a single image file'
    )

    parser.add_argument(
        '--range',
        nargs=2,
        metavar=('START', 'END'),
        help='Convert a range of images (e.g., sklangref-031 sklangref-038)'
    )

    parser.add_argument(
        '--image-dir',
        default='.',
        help='Directory containing images (for --range)'
    )

    # Manual metadata (required)
    parser.add_argument(
        '--manual-code',
        required=True,
        help='Manual code (e.g., sklangref, vivaxlskill)'
    )

    parser.add_argument(
        '--product-code',
        required=True,
        help='Product code (e.g., SKILL, ICADV, IC)'
    )

    parser.add_argument(
        '--product-hierarchy-level',
        type=int,
        default=0,
        help='Product hierarchy level (0=Core, 1=Family, 2=Product)'
    )

    parser.add_argument(
        '--version',
        required=True,
        help='Version string (e.g., 6.1.8, 23.1)'
    )

    parser.add_argument(
        '--document-title',
        required=True,
        help='Document title (e.g., "Cadence SKILL Language Reference")'
    )

    # Output options
    parser.add_argument(
        '--output',
        help='Output JSON file path (for single image)'
    )

    parser.add_argument(
        '--output-dir',
        help='Output directory (for range mode)'
    )

    parser.add_argument(
        '--api-key',
        help='Gemini API key (or set GEMINI_API_KEY environment variable)'
    )

    parser.add_argument(
        '--base-url',
        help='Custom Gemini API base URL (or set GOOGLE_GEMINI_BASE_URL environment variable)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.image and not args.range:
        parser.error("Must specify --image or --range")

    # Build manual metadata
    manual_metadata = {
        "manual_code": args.manual_code,
        "product_code": args.product_code,
        "product_hierarchy_level": args.product_hierarchy_level,
        "version": args.version,
        "document_title": args.document_title,
        "source_type": "manual"
    }

    try:
        # Initialize converter
        converter = SkillManualConverter(
            api_key=args.api_key,
            manual_metadata=manual_metadata,
            base_url=args.base_url
        )

        # Process single image
        if args.image:
            print(f"📖 Processing: {args.image}")

            result = converter.convert_page(args.image)

            if 'page_type' in result and result['page_type'] == 'function':
                # Save as database-ready JSON
                output_path = args.output or f"{result['function_name']}.json"
                converter.save_to_json([result], output_path)
            else:
                # Category page or other
                print("\n" + "="*80)
                print(json.dumps(result, indent=2, ensure_ascii=False))
                print("="*80)

                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"\nℹ️  Saved to: {args.output}")

        # Process range
        elif args.range:
            start_name, end_name = args.range

            # Extract page numbers
            start_match = re.search(r'-(\d+)', start_name)
            end_match = re.search(r'-(\d+)', end_name)

            if not start_match or not end_match:
                parser.error("Invalid range format. Expected format: prefix-NNN")

            prefix = start_name[:start_name.rfind('-')]
            start_num = int(start_match.group(1))
            end_num = int(end_match.group(1))

            print(f"📖 Processing range: {start_name} to {end_name}")
            print(f"   Total pages: {end_num - start_num + 1}\n")

            functions = []
            current_category = None

            for page_num in range(start_num, end_num + 1):
                image_file = os.path.join(args.image_dir, f"{prefix}-{page_num:03d}.png")

                if not os.path.exists(image_file):
                    print(f"  ⚠️  Warning: {image_file} not found, skipping")
                    continue

                print(f"  Processing: {image_file}...", end=" ")

                result = converter.convert_page(image_file, current_category)

                if result.get('page_type') == 'category':
                    # Update current category
                    current_category = result.get('category_name')
                    print(f"✅ Category: {current_category}")
                elif result.get('page_type') == 'function' or 'function_name' in result:
                    func_name = result.get('function_name', 'unknown')
                    functions.append(result)
                    print(f"✅ Function: {func_name}")
                else:
                    print("↳ (skipped)")

            # Merge duplicate functions before saving
            if functions:
                functions = merge_duplicate_functions(functions)

                output_dir = args.output_dir or 'test_output'
                os.makedirs(output_dir, exist_ok=True)

                output_path = os.path.join(
                    output_dir,
                    f"{args.manual_code}_{start_name}_to_{end_name}.json"
                )

                converter.save_to_json(functions, output_path)

                print(f"\n{'='*80}")
                print(f"✅ Completed! Extracted {len(functions)} function(s)")
                print(f"{'='*80}")
            else:
                print("\n⚠️  No functions extracted")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
