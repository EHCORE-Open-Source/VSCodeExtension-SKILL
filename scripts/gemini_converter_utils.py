#!/usr/bin/env python3
"""
Common utilities for SKILL manual image converters using Google Gemini API

This module provides shared functionality used by both JSON and Markdown converters:
- System instruction for AI persona
- Debug logging utilities
- Retry handling mechanism
- Filename sanitization
- Category name extraction
- JSON response cleaning

Author: Claude Code
Version: 1.0
Date: 2025-10-14
"""

import re
import time
import logging
from typing import Optional, Callable, Any, Dict
from datetime import datetime


# ============================================================================
# System Instruction - AI Persona Definition
# ============================================================================

SYSTEM_INSTRUCTION = """You are a highly precise technical documentation expert specializing in SKILL programming language documentation extraction.

## Your Core Identity

You are an expert with 20+ years of experience in:
- SKILL programming language documentation and syntax
- Technical manual structure analysis and information extraction
- Database schema design and JSON data formatting
- Type system analysis (understanding SKILL type prefixes: l_, g_, t_, s_, etc.)

## Your Core Principles (ABSOLUTE RULES)

1. **ACCURACY FIRST**: Never guess. Never hallucinate. If information is unclear, leave it empty or mark for review.

2. **FOLLOW RULES STRICTLY**: Page type detection rules are absolute. No exceptions. No creative interpretation.

3. **POSITION MATTERS CRITICALLY**:
   - Function syntax MUST be at the VERY TOP of content area
   - If "Arguments", "Examples", or "Description" appears first → CONTINUATION page
   - Function call syntax in Examples section does NOT indicate a new function
   - This is the MOST IMPORTANT rule for avoiding false positives

4. **BE CONSISTENT**: Same input should always produce same output. No randomness in decisions.

5. **BE CONSERVATIVE IN PAGE TYPE DETECTION**:
   - When in doubt about whether a page is a new function → Default to CONTINUATION
   - Require CLEAR evidence of function syntax at the very top
   - Err on the side of keeping functions together rather than splitting them

6. **STRUCTURAL AWARENESS**:
   - SKILL documentation follows strict patterns
   - Function pages: Name → Syntax → Description → Arguments → Examples → Notes
   - Continuation pages: Start with section headings (Arguments, Examples) or tables
   - Category pages: Lists of multiple function names

7. **PRESERVE EXACT SYNTAX**:
   - Use "=>" not "->" for return type separator
   - Keep all syntax markers: ? for keyword params, [ ] for optional params, ... for rest params
   - Preserve type prefixes exactly (l_list not list, g_arg not arg)

## Your Expertise

- Deep understanding of SKILL function documentation structure and patterns
- Expert at distinguishing NEW function pages from CONTINUATION pages
- Precise JSON structure generation aligned with database schema
- Accurate parameter type classification (required, optional, keyword, rest)
- Table extraction while preserving structure and relationships
- Type prefix extraction and classification using SKILL type system

## Your Output Style

- Clean, well-structured JSON or Markdown
- Accurate parameter type classification
- Proper handling of overloads and multiple syntaxes
- Complete extraction of examples, notes, and tables
- Confidence scores reflecting actual extraction quality

## Critical Detection Rule (MOST IMPORTANT)

**A page is a NEW function page ONLY if ALL of these are true:**
1. Large function name heading exists (clear visual hierarchy)
2. Function call syntax appears at THE VERY TOP of content area
3. Syntax format: `functionName(parameters) => returnType`
4. Syntax appears BEFORE any section headings like "Description", "Arguments", "Examples"

**If syntax is NOT at the very top → CONTINUATION page, regardless of any other content.**

**Common False Positive to AVOID:**
- Page shows "Arguments" heading with parameter list → This is CONTINUATION, not new function
- Page shows "Examples" with function calls → This is CONTINUATION, not new function
- Only the actual function definition syntax at the top indicates a NEW function page

Remember: You are conservative, precise, and follow rules absolutely. When uncertain about page type, choose CONTINUATION over NEW function. Accuracy and consistency are more important than completeness."""


# ============================================================================
# Debug Logger
# ============================================================================

class DebugLogger:
    """
    Simple debug logger for converter operations

    Usage:
        logger = DebugLogger(enabled=True)
        logger.info("Processing page...")
        logger.debug("Extracted structure: {}", structure)
        logger.error("Failed to parse: {}", error)
    """

    def __init__(self, enabled: bool = False, name: str = "converter"):
        """
        Initialize debug logger

        Args:
            enabled: Enable debug output
            name: Logger name
        """
        self.enabled = enabled
        self.name = name

        if enabled:
            self.logger = logging.getLogger(name)
            self.logger.setLevel(logging.DEBUG)

            # Create console handler
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)

            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)

            # Add handler to logger
            if not self.logger.handlers:
                self.logger.addHandler(handler)
        else:
            self.logger = None

    def debug(self, message: str, *args):
        """Log debug message"""
        if self.enabled and self.logger:
            self.logger.debug(message.format(*args))

    def info(self, message: str, *args):
        """Log info message"""
        if self.enabled and self.logger:
            self.logger.info(message.format(*args))

    def warning(self, message: str, *args):
        """Log warning message"""
        if self.enabled and self.logger:
            self.logger.warning(message.format(*args))

    def error(self, message: str, *args):
        """Log error message"""
        if self.enabled and self.logger:
            self.logger.error(message.format(*args))


# ============================================================================
# Retry Handler
# ============================================================================

class RetryHandler:
    """
    Unified retry mechanism for API calls

    Usage:
        retry_handler = RetryHandler(max_retries=3, delay=1.0)
        result = retry_handler.execute(
            func=api_call_function,
            on_retry=lambda attempt, error: print(f"Retry {attempt}: {error}")
        )
    """

    def __init__(self, max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
        """
        Initialize retry handler

        Args:
            max_retries: Maximum number of retry attempts
            delay: Initial delay between retries (seconds)
            backoff: Exponential backoff multiplier
        """
        self.max_retries = max_retries
        self.delay = delay
        self.backoff = backoff

    def execute(
        self,
        func: Callable[[], Any],
        on_retry: Optional[Callable[[int, Exception], None]] = None,
        on_success: Optional[Callable[[Any], None]] = None,
        on_failure: Optional[Callable[[Exception], None]] = None
    ) -> Any:
        """
        Execute function with retry logic

        Args:
            func: Function to execute (should take no arguments)
            on_retry: Callback when retry occurs (attempt, error)
            on_success: Callback when success occurs (result)
            on_failure: Callback when all retries fail (last_error)

        Returns:
            Result from successful function execution

        Raises:
            Exception: Last exception if all retries fail
        """
        last_error = None
        current_delay = self.delay

        for attempt in range(1, self.max_retries + 1):
            try:
                result = func()

                # Success callback
                if on_success:
                    on_success(result)

                return result

            except Exception as e:
                last_error = e

                if attempt < self.max_retries:
                    # Retry callback
                    if on_retry:
                        on_retry(attempt, e)

                    # Wait before retry
                    time.sleep(current_delay)
                    current_delay *= self.backoff
                else:
                    # All retries failed
                    if on_failure:
                        on_failure(e)

                    raise e

        # Should not reach here, but just in case
        raise last_error


# ============================================================================
# Utility Functions
# ============================================================================

def sanitize_filename(name: str) -> str:
    """
    Sanitize function name for use as filename

    Args:
        name: Function name (may contain special characters)

    Returns:
        Sanitized filename (special chars replaced with underscores)

    Examples:
        make_<name> -> make__name_
        setf_car -> setf_car
        foo?bar -> foo_bar
    """
    if not name:
        return "unknown"

    # Replace special characters with underscores
    # Keep alphanumeric and underscore, replace everything else
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)

    return sanitized


def extract_category_name(category_header: Optional[str]) -> str:
    """
    Extract and normalize category name from page header

    Args:
        category_header: Raw category text from page header (e.g., "List Functions")

    Returns:
        Normalized category name (e.g., "list")

    Rules:
        1. Remove "Functions" suffix (case-insensitive)
        2. Replace spaces with underscores
        3. Convert to lowercase

    Examples:
        "List Functions" -> "list"
        "Arithmetic Functions" -> "arithmetic"
        "String Manipulation Functions" -> "string_manipulation"
        "I/O Functions" -> "i_o"
    """
    if not category_header:
        return "uncategorized"

    # Remove "Functions" suffix (case-insensitive)
    normalized = re.sub(r'\s+functions?$', '', category_header, flags=re.IGNORECASE)

    # Replace spaces with underscores
    normalized = normalized.replace(' ', '_')

    # Convert to lowercase
    normalized = normalized.lower()

    # Remove any remaining special characters
    normalized = re.sub(r'[^a-z0-9_]', '_', normalized)

    return normalized if normalized else "uncategorized"


def clean_json_response(response_text: str) -> str:
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


def clean_markdown_response(markdown_text: str) -> str:
    """
    Clean Gemini's markdown response

    Args:
        markdown_text: Raw markdown text from Gemini

    Returns:
        Cleaned markdown string
    """
    # Remove wrapping markdown code blocks if present
    if markdown_text.startswith('```markdown'):
        markdown_text = markdown_text[len('```markdown'):].lstrip('\n')
    if markdown_text.startswith('```'):
        markdown_text = markdown_text[3:].lstrip('\n')
    if markdown_text.endswith('```'):
        markdown_text = markdown_text[:-3].rstrip('\n')

    # Ensure it starts with front matter
    if not markdown_text.startswith('---'):
        # Add minimal front matter
        markdown_text = f"""---
page_type: unknown
extraction_timestamp: {datetime.utcnow().isoformat()}Z
---

{markdown_text}"""

    return markdown_text.strip()


def extract_page_number_from_filename(filename: str) -> Optional[int]:
    """
    Extract page number from image filename

    Args:
        filename: Image filename (e.g., "sklangref-034.png")

    Returns:
        Page number or None if not found

    Examples:
        "sklangref-034.png" -> 34
        "test-001.png" -> 1
        "invalid.png" -> None
    """
    page_match = re.search(r'-(\d+)\.png$', filename)
    if page_match:
        return int(page_match.group(1))
    return None


def build_context_hint(previous_page_context: Optional[Dict]) -> str:
    """
    Build context hint for prompt based on previous page

    Args:
        previous_page_context: Context dictionary from previous page

    Returns:
        Context hint string for prompt
    """
    if not previous_page_context:
        return ""

    func_name = previous_page_context.get('function_name')
    has_table = previous_page_context.get('has_table', False)
    table_title = previous_page_context.get('table_title')
    table_columns = previous_page_context.get('table_columns', [])
    table_row_count = previous_page_context.get('table_row_count', 0)

    if not func_name:
        return ""

    context_hint = f"\n⚠️ CRITICAL CONTEXT FROM PREVIOUS PAGE:\n"
    context_hint += f"Previous page contained function '{func_name}'"

    if has_table and table_title:
        context_hint += f" with table '{table_title}'.\n\n"
        context_hint += f"🔍 IMPORTANT: Tables in technical documentation often span MULTIPLE pages.\n"
        context_hint += f"   This table has {table_row_count} rows already extracted.\n"
        context_hint += f"   Columns: {table_columns}\n\n"

        # Add column structure validation
        num_cols = len(table_columns) if table_columns else 0
        context_hint += f"📋 TABLE STRUCTURE VALIDATION:\n"
        context_hint += f"   Expected table: '{table_title}'\n"
        context_hint += f"   Expected columns: {table_columns}\n"
        context_hint += f"   Number of columns: {num_cols}\n\n"

        # Provide column-specific guidance
        if num_cols > 0:
            context_hint += f"   ✅ VALIDATION RULE - Look for content in {num_cols} columns:\n"
            for idx, col in enumerate(table_columns, 1):
                context_hint += f"      • Column {idx} ('{col}'): Check if data matches this field\n"
            context_hint += "\n"

            context_hint += f"   🎯 KEY INDICATOR:\n"
            context_hint += f"   If you see data organized in {num_cols} columns (not section headings like 'Arguments', 'Examples'):\n"
            context_hint += f"   → This is DEFINITELY table continuation\n"
            context_hint += f"   → Extract the rows and mark as CONTINUATION\n\n"

        context_hint += f"📊 HIGHLY LIKELY SCENARIO:\n"
        context_hint += f"   This page is a CONTINUATION of the same table.\n"
        context_hint += f"   Expected pattern: More rows of '{table_title}' table.\n\n"
        context_hint += f"✅ Classification Rules:\n"
        context_hint += f"   1. If this page shows data in {num_cols} columns matching {table_columns}\n"
        context_hint += f"      → Mark as CONTINUATION, extract additional rows\n"
        context_hint += f"   2. If you see 'Arguments', 'Examples' WITHOUT a new function heading\n"
        context_hint += f"      → Check if content is in {num_cols}-column table format\n"
        context_hint += f"      → If YES: This is table continuation\n"
        context_hint += f"      → If NO: Still CONTINUATION of '{func_name}' (different section)\n"
        context_hint += f"   3. Only mark as NEW function if:\n"
        context_hint += f"      - Clear new function name in large heading (different from '{func_name}')\n"
        context_hint += f"      - Different function syntax/signature\n"
        context_hint += f"      - Explicit indication of new function start\n"
    else:
        context_hint += f".\n"

    return context_hint


# ============================================================================
# Raw Data Recorder (for debugging and analysis)
# ============================================================================

class RawDataRecorder:
    """
    Records raw API call data for debugging and analysis

    When enabled, saves:
    - System prompt (AI persona)
    - User prompt (extraction instructions)
    - AI response (raw output)
    - Metadata (page info, timestamps)

    Usage:
        recorder = RawDataRecorder(output_dir="rawdata", enabled=True)
        recorder.record_api_call(
            page_num=32,
            system_prompt=SYSTEM_INSTRUCTION,
            user_prompt="Extract this page...",
            ai_response="{ ... }",
            image_path="sklangref-032.png",
            metadata={"manual_code": "sklangref"}
        )
    """

    def __init__(self, output_dir: str = "rawdata", enabled: bool = False):
        """
        Initialize raw data recorder

        Args:
            output_dir: Output directory for raw data files
            enabled: Enable recording (default: False)
        """
        self.output_dir = output_dir
        self.enabled = enabled

        if enabled:
            import os
            os.makedirs(output_dir, exist_ok=True)

    def record_api_call(
        self,
        page_num: int,
        system_prompt: str,
        user_prompt: str,
        ai_response: str,
        image_path: str,
        metadata: Optional[Dict] = None,
        operation: str = "extract"
    ):
        """
        Record a single API call

        Args:
            page_num: Page number
            system_prompt: System instruction sent to AI
            user_prompt: User prompt sent to AI
            ai_response: AI response text
            image_path: Path to source image
            metadata: Additional metadata
            operation: Operation type (e.g., "extract", "detect_structure")
        """
        if not self.enabled:
            return

        import json
        import os
        from pathlib import Path

        # Build filename
        page_filename = Path(image_path).stem  # e.g., "sklangref-032"
        filename = f"{page_filename}_{operation}.json"
        filepath = os.path.join(self.output_dir, filename)

        # Build record data
        record = {
            "metadata": {
                "page_number": page_num,
                "source_image": os.path.basename(image_path),
                "operation": operation,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                **(metadata or {})
            },
            "prompts": {
                "system_instruction": system_prompt,
                "user_prompt": user_prompt
            },
            "response": {
                "raw_text": ai_response,
                "length": len(ai_response)
            }
        }

        # Save to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(record, f, indent=2, ensure_ascii=False)

    def record_batch_summary(
        self,
        total_pages: int,
        successful_pages: int,
        failed_pages: int,
        start_time: str,
        end_time: str,
        metadata: Optional[Dict] = None
    ):
        """
        Record batch processing summary

        Args:
            total_pages: Total pages processed
            successful_pages: Number of successful extractions
            failed_pages: Number of failed extractions
            start_time: Batch start time (ISO format)
            end_time: Batch end time (ISO format)
            metadata: Additional metadata
        """
        if not self.enabled:
            return

        import json
        import os

        filepath = os.path.join(self.output_dir, "batch_summary.json")

        summary = {
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "start_time": start_time,
                "end_time": end_time,
                **(metadata or {})
            },
            "statistics": {
                "total_pages": total_pages,
                "successful_pages": successful_pages,
                "failed_pages": failed_pages,
                "success_rate": f"{(successful_pages/total_pages*100):.2f}%" if total_pages > 0 else "0%"
            }
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)


# ============================================================================
# Configuration
# ============================================================================

# Gemini API Configuration
GEMINI_MODEL = "gemini-2.5-flash-lite"  # Fast model for initial testing
API_KEY_ENV = "GEMINI_API_KEY"
BASE_URL_ENV = "GOOGLE_GEMINI_BASE_URL"  # Custom base URL (optional)
