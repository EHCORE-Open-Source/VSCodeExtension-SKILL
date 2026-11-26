#!/usr/bin/env python3
"""
Base converter class for SKILL manual image converters

This module provides the abstract base class and common functionality for:
- Page structure extraction
- Page type detection (NEW function / CONTINUATION / CATEGORY / OTHER)
- Gemini API client management
- Context tracking for multi-page functions
- Streaming page processing (memory efficient)

Author: Claude Code
Version: 1.0
Date: 2025-10-14
"""

import os
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from PIL import Image
from google import genai
from google.genai import types

from gemini_converter_utils import (
    SYSTEM_INSTRUCTION,
    GEMINI_MODEL,
    API_KEY_ENV,
    BASE_URL_ENV,
    DebugLogger,
    RetryHandler,
    RawDataRecorder,
    clean_json_response,
    extract_page_number_from_filename
)


# ============================================================================
# Base Converter Abstract Class
# ============================================================================

class BaseConverter(ABC):
    """
    Abstract base class for SKILL manual converters

    This class provides common functionality for all converters:
    - Gemini API client initialization
    - Page structure extraction
    - Page type detection
    - Context management for multi-page functions

    Subclasses must implement:
    - extract_page(): Format-specific extraction logic
    - merge_pages(): Format-specific merging logic
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
        Initialize base converter

        Args:
            api_key: Gemini API key (if None, reads from environment variable)
            base_url: Custom Gemini API base URL (if None, reads from environment variable)
            manual_metadata: Manual metadata dictionary
            debug: Enable debug logging
            rawdata_dir: Directory for raw data recording (enables recording if provided)
        """
        # Initialize API key
        self.api_key = api_key or os.getenv(API_KEY_ENV)
        if not self.api_key:
            raise ValueError(f"API key not found. Set {API_KEY_ENV} environment variable or pass it as argument.")

        # Get base URL
        self.base_url = base_url or os.getenv(BASE_URL_ENV)

        # Initialize Gemini client
        if self.base_url:
            self.client = genai.Client(api_key=self.api_key, http_options={'base_url': self.base_url})
        else:
            self.client = genai.Client(api_key=self.api_key)

        # Store manual metadata
        self.manual_metadata = manual_metadata or {}
        if 'source_type' not in self.manual_metadata:
            self.manual_metadata['source_type'] = 'manual'

        # Initialize logger
        self.logger = DebugLogger(enabled=debug, name=self.__class__.__name__)

        # Initialize retry handler
        self.retry_handler = RetryHandler(max_retries=3, delay=1.0, backoff=2.0)

        # Initialize raw data recorder (enabled if rawdata_dir is provided)
        self.raw_data_recorder = RawDataRecorder(
            output_dir=rawdata_dir or "rawdata",
            enabled=rawdata_dir is not None
        )

    # ========================================================================
    # Abstract Methods (must be implemented by subclasses)
    # ========================================================================

    @abstractmethod
    def extract_page(
        self,
        image_path: str,
        category: Optional[str] = None,
        previous_page_context: Optional[Dict] = None
    ) -> Any:
        """
        Extract content from a single page (format-specific)

        Args:
            image_path: Path to the PNG image file
            category: Optional category name
            previous_page_context: Optional context from previous page

        Returns:
            Extracted data in format-specific structure
        """
        pass

    @abstractmethod
    def merge_pages(self, pages: List[Any]) -> Any:
        """
        Merge multiple pages into a single document (format-specific)

        Args:
            pages: List of extracted page data

        Returns:
            Merged document in format-specific structure
        """
        pass

    # ========================================================================
    # Common Methods (shared by all converters)
    # ========================================================================

    def extract_page_structure(self, image_path: str) -> Dict:
        """
        Extract structural information from page (Step 1: Structure Detection)

        This focuses on extracting STRUCTURE only, not content.
        AI is used for extraction, but rules will determine page type.

        Args:
            image_path: Path to the PNG image file

        Returns:
            Dictionary with structural flags
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        self.logger.debug("Extracting structure from: {}", image_path)

        image = Image.open(image_path)

        prompt = """
Analyze this SKILL documentation page and determine its type.

📍 PAGE STRUCTURE:
┌────────────────────────────┐
│ Header (2 lines)           │ ← Extract title & category
├────────────────────────────┤
│ CONTENT AREA (focus here)  │
├────────────────────────────┤
│ Footer                     │ ← Ignore
└────────────────────────────┘

🔍 PAGE TYPE RULES:

1️⃣ NEW FUNCTION - MUST meet ALL 3:
   ✅ Function syntax at THE VERY TOP of content
   ✅ Format: functionName(params) => returnType
   ✅ BEFORE any section headings

   Example:
   ─────────────────
   sstatus                          ← Name
   sstatus(s_name g_switchValue)    ← SYNTAX at TOP
   => g_switchValue

   Sets the internal...             ← Description
   ─────────────────

2️⃣ CONTINUATION - ANY of these:
   ✅ Starts with section heading: "Arguments", "Examples", "Value Returned", "Notes"
   ✅ Starts with table (no syntax at top)
   ✅ NO function syntax at beginning

   Example:
   ─────────────────
   Arguments                        ← Section heading at TOP
     s_name
     g_switchValue

   Examples
     sstatus(debugMode t)           ← NOT a new function!
   ─────────────────

3️⃣ CATEGORY - Multiple function names listed

⚠️ KEY RULE:
NEW FUNCTION syntax MUST be at THE VERY TOP.
If "Arguments" or "Examples" appears first → CONTINUATION.

Return JSON:
{
  "manual_title": "header line 1 or null",
  "category": "header line 2 or null",
  "page_number": integer or null,
  "page_type": "NEW" or "CONTINUATION" or "CATEGORY" or "OTHER",
  "page_type_confidence": "high" or "medium" or "low",
  "page_type_reasoning": "brief reason",
  "content_first_line": "first line of content or null",
  "has_function_heading": true/false,
  "function_name": "name or null",
  "has_function_call_pattern": true/false,
  "function_call_syntax": "full syntax or null",
  "has_arguments_section": true/false,
  "has_examples_section": true/false,
  "has_notes_section": true/false,
  "has_return_section": true/false,
  "has_function_list": true/false,
  "has_table": true/false,
  "table_title": "table title or null",
  "table_columns": ["col1", "col2"] or null
}

Return ONLY the JSON object.
"""

        def extract_structure():
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[prompt, image],
                config=types.GenerateContentConfig(
                    systemInstruction=SYSTEM_INSTRUCTION,
                    temperature=0.0,  # Maximum consistency
                    topP=0.95,
                    topK=40
                )
            )
            return response

        # Execute with retry
        response = self.retry_handler.execute(
            func=extract_structure,
            on_retry=lambda attempt, error: self.logger.warning(
                "Structure extraction failed (attempt {}): {}", attempt, error
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
            operation="detect_structure"
        )

        try:
            response_text = clean_json_response(response.text)
            structure = json.loads(response_text)
            self.logger.debug("Structure extracted: {}", structure.get('page_type', 'unknown'))
            return structure
        except json.JSONDecodeError:
            self.logger.error("Failed to parse structure response")
            return {}

    def detect_page_type(
        self,
        image_path: str,
        previous_function: Optional[str] = None
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """
        Detect page type using RULE-BASED logic (not AI classification)

        Args:
            image_path: Path to the PNG image file
            previous_function: Name of the function from the previous page

        Returns:
            Tuple of (page_type, function_name, category)
            - page_type: 'function' | 'continuation' | 'category' | 'other'
            - function_name: Detected function name or None
            - category: Detected category or None
        """
        # Step 1: Extract structure
        structure = self.extract_page_structure(image_path)

        # Extract header info
        category = structure.get('category')

        # Step 2: Apply RULES to determine page type
        has_func_heading = structure.get('has_function_heading', False)
        has_func_call = structure.get('has_function_call_pattern', False)
        has_arguments = structure.get('has_arguments_section', False)
        has_examples = structure.get('has_examples_section', False)
        has_notes = structure.get('has_notes_section', False)
        has_return = structure.get('has_return_section', False)
        has_func_list = structure.get('has_function_list', False)
        has_table = structure.get('has_table', False)
        function_name = structure.get('function_name')

        self.logger.debug(
            "Detection flags - heading:{} call:{} args:{} table:{} prev_func:{}",
            has_func_heading, has_func_call, has_arguments, has_table, previous_function
        )

        # RULE 1: NEW FUNCTION PAGE (highest priority)
        # - Has function heading
        # - Has function call pattern (functionName followed by "(")
        # - OR has arguments section
        # - AND not just a table heading being misidentified
        if has_func_heading and (has_func_call or has_arguments) and not (has_table and not has_func_call):
            self.logger.info("Detected NEW function page: {}", function_name)
            return 'function', function_name, category

        # RULE 2: CONTINUATION PAGE (high priority when previous_function exists)
        # - NO function heading (or table title being misidentified as heading)
        # - Has ANY content (examples OR notes OR return section OR arguments OR table)
        # - Previous function exists
        #
        # IMPORTANT: Use LOOSE matching for continuation pages to handle AI extraction variance
        if not has_func_heading and previous_function:
            # Strong indicators: explicit content sections or tables
            if has_examples or has_notes or has_return or has_arguments or has_table:
                self.logger.info("Detected CONTINUATION page: {}", previous_function)
                return 'continuation', previous_function, category

            # Weak indicator but likely continuation: no function list
            # This handles cases where AI misses structure detection
            elif not has_func_list:
                self.logger.info("Detected CONTINUATION page (weak): {}", previous_function)
                return 'continuation', previous_function, category

        # RULE 2.5: SPECIAL CASE - Table in middle of function (enhanced detection)
        # If has_table and has_func_heading but NO func_call pattern, likely a table title being misidentified
        # Treat as continuation if previous_function exists
        if has_table and has_func_heading and not has_func_call and previous_function:
            self.logger.info("Detected CONTINUATION page (table): {}", previous_function)
            return 'continuation', previous_function, category

        # RULE 3: CATEGORY PAGE (lower priority - only when no previous context)
        # - Shows a list of multiple functions
        # - AND no function heading (to avoid false positives)
        # - AND no previous function (to avoid false positives on continuation pages)
        if has_func_list and not has_func_heading and not previous_function:
            self.logger.info("Detected CATEGORY page")
            return 'category', None, category

        # RULE 4: FALLBACK FOR CONTINUATION
        # Last resort: if previous function exists, treat as continuation
        # This handles edge cases where AI makes detection errors:
        # - False positive on has_function_heading (but missing call pattern/arguments)
        # - False positive on has_function_list
        if previous_function:
            # If we reached here, RULE 1 didn't match (not a valid new function page)
            # Even if has_func_heading=True, without call pattern/arguments, it's likely a false positive
            # Same for has_func_list - could be a false positive
            self.logger.info("Detected CONTINUATION page (fallback): {}", previous_function)
            return 'continuation', previous_function, category

        # RULE 5: OTHER (truly unrecognized)
        self.logger.warning("Page type: OTHER (unrecognized)")
        return 'other', None, category

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

        self.logger.info("Extracting category page: {}", image_path)

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

        def extract_category():
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
            func=extract_category,
            on_retry=lambda attempt, error: self.logger.warning(
                "Category extraction failed (attempt {}): {}", attempt, error
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
            operation="extract_category"
        )

        # Parse JSON response
        try:
            response_text = clean_json_response(response.text)
            category_data = json.loads(response_text)

            # Add page type
            category_data['page_type'] = 'category'

            # Extract page number from filename if not in data
            if not category_data.get('page_number'):
                page_num = extract_page_number_from_filename(image_path)
                if page_num:
                    category_data['page_number'] = page_num

            self.logger.info("Category extracted: {}", category_data.get('category_name'))
            return category_data

        except json.JSONDecodeError as e:
            self.logger.error("Failed to parse category JSON: {}", e)
            return {
                "page_type": "category",
                "error": "JSON parsing failed",
                "raw_response": response.text
            }


# ============================================================================
# Streaming Page Processor (Memory Efficient)
# ============================================================================

class StreamingPageProcessor:
    """
    Stream-based page processor for handling large page ranges

    This class processes pages one at a time and yields results,
    reducing memory usage for large document conversions.

    Usage:
        processor = StreamingPageProcessor(converter)
        for result in processor.process_range(start, end, image_dir):
            # Handle result
            save_to_file(result)
    """

    def __init__(self, converter: BaseConverter):
        """
        Initialize streaming processor

        Args:
            converter: BaseConverter instance
        """
        self.converter = converter
        self.logger = converter.logger

    def process_range(
        self,
        start_page: int,
        end_page: int,
        image_dir: str,
        image_prefix: str,
        category: Optional[str] = None
    ):
        """
        Process a range of pages with streaming (generator)

        Args:
            start_page: Start page number
            end_page: End page number (inclusive)
            image_dir: Directory containing images
            image_prefix: Image filename prefix (e.g., 'sklangref')
            category: Optional initial category

        Yields:
            Tuple of (page_num, result_dict, page_type)
        """
        current_category = category
        previous_function = None
        previous_page_context = None

        for page_num in range(start_page, end_page + 1):
            image_file = os.path.join(image_dir, f"{image_prefix}-{page_num:03d}.png")

            if not os.path.exists(image_file):
                self.logger.warning("Image not found: {}", image_file)
                continue

            self.logger.info("Processing page: {}", page_num)

            # Detect page type
            page_type, function_name, detected_category = self.converter.detect_page_type(
                image_file,
                previous_function
            )

            # Update category
            if detected_category:
                current_category = detected_category

            # Extract page content
            result = self.converter.extract_page(
                image_file,
                category=current_category,
                previous_page_context=previous_page_context
            )

            # Update context for next iteration
            if page_type == 'function':
                previous_function = function_name
                # Update previous_page_context based on result
                # (format-specific, should be implemented in subclass)
            elif page_type == 'continuation':
                # Keep previous_function unchanged
                pass
            else:
                # Reset for category or other pages
                previous_function = None
                previous_page_context = None

            # Yield result
            yield (page_num, result, page_type)

    def process_batch(
        self,
        page_nums: List[int],
        image_dir: str,
        image_prefix: str,
        category: Optional[str] = None
    ):
        """
        Process a batch of specific pages (non-sequential)

        Args:
            page_nums: List of page numbers to process
            image_dir: Directory containing images
            image_prefix: Image filename prefix
            category: Optional initial category

        Yields:
            Tuple of (page_num, result_dict, page_type)
        """
        for page_num in page_nums:
            image_file = os.path.join(image_dir, f"{image_prefix}-{page_num:03d}.png")

            if not os.path.exists(image_file):
                self.logger.warning("Image not found: {}", image_file)
                continue

            self.logger.info("Processing page: {}", page_num)

            # For batch processing, we don't track context
            result = self.converter.extract_page(
                image_file,
                category=category
            )

            # Detect page type
            page_type, function_name, _ = self.converter.detect_page_type(image_file)

            yield (page_num, result, page_type)
