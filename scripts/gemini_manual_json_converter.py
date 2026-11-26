#!/usr/bin/env python3
"""
SKILL Manual Image to Database JSON Converter

This tool converts SKILL manual images (PNG) to database-ready JSON format
using Google Gemini API for intelligent extraction.

This is a refactored version using BaseConverter for better code organization.

Key Features:
- Database-ready JSON output (100% aligned with DATABASE_JSON_SCHEMA.md)
- Automatic type prefix extraction using skill_type_utils.py
- Parameter type classification (required/keyword/optional/rest)
- Category page detection and handling
- Multi-page function support
- Overload detection

Usage:
    # Convert single image
    python3 gemini_manual_json_converter.py \
        --image docs/cadence_manual/images/sklangref/sklangref-034.png \
        --manual-code sklangref \
        --product-code SKILL \
        --version 6.1.8 \
        --document-title "Cadence SKILL Language Reference" \
        --output test_output/append.json

    # Convert page range
    python3 gemini_manual_json_converter.py \
        --range sklangref-031 sklangref-038 \
        --image-dir docs/cadence_manual/images/sklangref/ \
        --manual-code sklangref \
        --product-code SKILL \
        --version 6.1.8 \
        --document-title "Cadence SKILL Language Reference" \
        --output-dir test_output/

Author: Claude Code
Version: 2.0 (Refactored)
Date: 2025-10-14
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
from google.genai import types

# Import base converter
from gemini_converter_base import BaseConverter

# Import utilities
from gemini_converter_utils import (
    SYSTEM_INSTRUCTION,
    GEMINI_MODEL,
    clean_json_response,
    sanitize_filename,
    extract_category_name,
    extract_page_number_from_filename,
    build_context_hint
)

# Import skill_type_utils
try:
    from skill_type_utils import (
        extract_type_prefix,
        classify_parameter_type,
        parse_syntax_arguments,
        parse_syntax_string,
        ParameterType
    )
except ImportError:
    print("Warning: skill_type_utils not found. Type extraction will be limited.")
    # Provide dummy functions
    def extract_type_prefix(name): return ('g', 'general')
    def parse_syntax_arguments(syntax): return []
    def parse_syntax_string(syntax): return (syntax, '')


# ============================================================================
# JSON Converter Class
# ============================================================================

class JSONConverter(BaseConverter):
    """
    Converter for SKILL manual images to database-ready JSON format

    Inherits common functionality from BaseConverter and implements
    JSON-specific extraction and merging logic.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        manual_metadata: Optional[Dict] = None,
        debug: bool = False,
        rawdata_dir: Optional[str] = None
    ):
        """
        Initialize JSON converter

        Args:
            api_key: Gemini API key
            base_url: Custom Gemini API base URL
            manual_metadata: Manual metadata dictionary
            debug: Enable debug logging
            rawdata_dir: Directory for raw data recording (enables recording if provided)
        """
        super().__init__(api_key, base_url, manual_metadata, debug, rawdata_dir)

    def extract_page(
        self,
        image_path: str,
        category: Optional[str] = None,
        previous_page_context: Optional[Dict] = None
    ) -> Dict:
        """
        Extract function information from a function page (JSON format)

        Args:
            image_path: Path to the PNG image file
            category: Optional category name
            previous_page_context: Optional context from previous page

        Returns:
            Dictionary containing function information in database-ready format
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        self.logger.info("Extracting page: {}", image_path)

        image = Image.open(image_path)

        # Build context hint
        context_hint = build_context_hint(previous_page_context)

        # Construct prompt
        prompt = self._build_extraction_prompt(context_hint)

        def extract():
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[prompt, image],
                config=types.GenerateContentConfig(
                    systemInstruction=SYSTEM_INSTRUCTION,
                    temperature=0.0,
                    topP=0.95,
                    topK=40
                )
            )
            return response

        # Execute with retry
        response = self.retry_handler.execute(
            func=extract,
            on_retry=lambda attempt, error: self.logger.warning(
                "Extraction failed (attempt {}): {}", attempt, error
            )
        )

        # Record raw data
        page_num = extract_page_number_from_filename(image_path) or 0
        self.raw_data_recorder.record_api_call(
            page_num=page_num,
            system_prompt=SYSTEM_INSTRUCTION,
            user_prompt=prompt,
            ai_response=response.text,
            image_path=image_path,
            metadata=self.manual_metadata,
            operation="extract"
        )

        # Parse JSON response
        try:
            response_text = clean_json_response(response.text)
            gemini_data = json.loads(response_text)

            # Convert to database-ready format
            function_data = self._convert_to_database_format(
                gemini_data,
                image_path,
                category
            )

            self.logger.info("Extraction successful: {}", function_data.get('function_name'))
            return function_data

        except json.JSONDecodeError as e:
            self.logger.error("JSON parsing failed: {}", e)
            raise

    def merge_pages(self, pages: List[Dict]) -> List[Dict]:
        """
        Merge multiple page extractions into complete function entries

        This handles multi-page functions by merging continuation pages
        with their primary function pages.

        Args:
            pages: List of function dictionaries (may contain duplicates)

        Returns:
            List of merged function dictionaries
        """
        if not pages:
            return []

        self.logger.info("Merging {} pages", len(pages))

        # Group functions by name
        function_groups = {}
        for func in pages:
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
                self.logger.info("Merging {} occurrences of '{}'", len(func_list), func_name)
                merged = self._merge_function_entries(func_list)
                merged_functions.append(merged)

        return merged_functions

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _build_extraction_prompt(self, context_hint: str) -> str:
        """Build extraction prompt for JSON format"""

        json_template = """{
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
}"""

        table_extraction = """  "table_data": {
    "title": "table title (e.g., 'Internal System Variables')",
    "columns": ["column1", "column2", "column3"],
    "rows": [
      ["value1_col1", "value1_col2", "value1_col3"],
      ["value2_col1", "value2_col2", "value2_col3"]
    ]
  }"""

        prompt = f"""
Analyze this SKILL function documentation page and extract complete information in JSON format.
{context_hint}
CRITICAL SYNTAX REQUIREMENTS:
1. Use "=>" (not "->") to separate function call from return value
2. Preserve ALL syntax markers EXACTLY as shown:
   - Keep '?' for keyword parameters (e.g., "?expr l_exprList")
   - Keep '[' and ']' for optional parameters (e.g., "[ x_index ]")
   - Keep '...' for rest parameters (e.g., "... g_args")
3. Format: "functionName(param1 param2 [ optionalParam ]) => returnType"

Extract the following information:

{json_template}

IMPORTANT:
- Extract function name from the heading (e.g., "append1" not "append")
- Use "=>" not "->" in syntax
- page_number must be an integer (e.g., 34 not "34")
- If the function has multiple syntaxes/overloads, list them all in the "overloads" array
- Do NOT use escaped characters in JSON (e.g., use "l_list" not "l\\_list")
- If a TABLE is present (e.g., "Internal System Variables"), extract it as "table_data"

TABLE EXTRACTION (if present):
If the page contains a table (e.g., with columns like "Name", "Meaning", "Default"),
add this to the JSON:

{table_extraction}

Return ONLY the JSON object, no additional text or markdown formatting.
"""
        return prompt

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

        # Process primary syntax arguments
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
            page_num = extract_page_number_from_filename(image_path)

        # Calculate extraction confidence
        confidence = self._calculate_confidence(gemini_data, arguments, return_values)

        # Determine if needs review
        needs_review = confidence < 0.85 or not gemini_data.get('description')

        # Process table data if present
        table_data = gemini_data.get('table_data')

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
                "parser_version": "2.0"
            }
        }

        # Add table data if present
        if table_data:
            function_obj['table_data'] = table_data

        return function_obj

    def _process_arguments(
        self,
        syntax_string: str,
        gemini_arguments: List[Dict]
    ) -> List[Dict]:
        """Process arguments using skill_type_utils and Gemini descriptions"""

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
        """Process return values"""

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
        """Calculate extraction confidence score"""

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

    def _merge_function_entries(self, func_list: List[Dict]) -> Dict:
        """Merge multiple entries of the same function"""

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

        # Merge notes
        notes_list = [f.get('notes') for f in func_list if f.get('notes')]
        if notes_list:
            notes_strings = []
            for note in notes_list:
                if isinstance(note, list):
                    notes_strings.append('\n'.join(str(n) for n in note))
                else:
                    notes_strings.append(str(note))
            merged['notes'] = '\n\n'.join(notes_strings)

        # Merge table data
        tables_with_data = [f for f in func_list if f.get('table_data')]
        if tables_with_data:
            base_table = tables_with_data[0]['table_data'].copy()

            # Check if all tables have the same structure
            all_same_table = all(
                f.get('table_data', {}).get('title') == base_table.get('title') and
                f.get('table_data', {}).get('columns') == base_table.get('columns')
                for f in tables_with_data
            )

            if all_same_table and len(tables_with_data) > 1:
                # Merge rows from all tables
                all_rows = []
                for f in tables_with_data:
                    table = f.get('table_data', {})
                    rows = table.get('rows', [])
                    all_rows.extend(rows)

                base_table['rows'] = all_rows
                merged['table_data'] = base_table
            else:
                merged['table_data'] = base_table

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

        merged['sources']['source_images'] = list(dict.fromkeys(all_images))
        merged['sources']['start_page'] = min(start_pages) if start_pages else None
        merged['sources']['end_page'] = max(end_pages) if end_pages else None

        # Update extraction confidence (average)
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


# ============================================================================
# Helper Functions
# ============================================================================

def save_individual_function(
    function_data: Dict,
    output_base_dir: str,
    manual_code: str,
    manual_metadata: Dict
) -> str:
    """
    Save individual function to structured directory

    Output structure:
        output_base_dir/
            manual_code/
                category/
                    function_name.json
    """
    # Extract function name and category
    function_name = function_data.get('function_name', 'unknown')
    category_raw = function_data.get('category', 'uncategorized')

    # Normalize names
    sanitized_name = sanitize_filename(function_name)
    normalized_category = extract_category_name(category_raw)

    # Build directory structure
    category_dir = os.path.join(output_base_dir, manual_code, normalized_category)
    os.makedirs(category_dir, exist_ok=True)

    # Build output file path
    output_path = os.path.join(category_dir, f"{sanitized_name}.json")

    # Build output data with metadata
    output_data = {
        "manual_metadata": {
            **manual_metadata,
            "processing_timestamp": datetime.now().isoformat() + "Z"
        },
        "function": function_data
    }

    # Save JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    return output_path


# ============================================================================
# Main Entry Point (for backward compatibility)
# ============================================================================

def main():
    """Main entry point (kept for backward compatibility)"""
    print("Note: This script has been refactored to use the new BaseConverter architecture.")
    print("For the unified CLI, use gemini_manual_converter.py instead.")
    print()

    # For now, we'll keep the old CLI interface working
    # In the future, this should redirect to gemini_manual_converter.py
    print("Please use the new unified converter:")
    print("  python3 scripts/gemini_manual_converter.py --format json ...")
    sys.exit(1)


if __name__ == '__main__':
    main()
