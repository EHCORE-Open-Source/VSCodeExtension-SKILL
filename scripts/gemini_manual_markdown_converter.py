#!/usr/bin/env python3
"""
SKILL Manual Image to Markdown Converter

This tool converts SKILL manual images (PNG) to structured Markdown format
using Google Gemini API for intelligent extraction.

This is a refactored version using BaseConverter for better code organization.

Key Features:
- Clean, human-readable Markdown output
- Easy review and correction
- Git-friendly (clear diffs)
- Native table support
- YAML front matter for metadata

Usage:
    # Single image
    python3 gemini_manual_markdown_converter.py \
        --image docs/cadence_manual/images/sklangref/sklangref-594.png \
        --manual-code sklangref \
        --product-code SKILL \
        --version "6.1.8" \
        --document-title "Cadence SKILL Language Reference" \
        --output output.md

    # Range of images
    python3 gemini_manual_markdown_converter.py \
        --range sklangref-594 sklangref-601 \
        --image-dir docs/cadence_manual/images/sklangref/ \
        --manual-code sklangref \
        --product-code SKILL \
        --version "6.1.8" \
        --document-title "Cadence SKILL Language Reference" \
        --output-dir output_markdown/

Author: Claude Code
Version: 2.0 (Refactored)
Date: 2025-10-14
"""

import os
import sys
import re
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
    clean_markdown_response,
    sanitize_filename,
    extract_category_name,
    extract_page_number_from_filename
)


# ============================================================================
# Markdown Converter Class
# ============================================================================

class MarkdownConverter(BaseConverter):
    """
    Converter for SKILL manual images to Markdown format

    Inherits common functionality from BaseConverter and implements
    Markdown-specific extraction and merging logic.
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
        Initialize Markdown converter

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
    ) -> str:
        """
        Extract content from a page in Markdown format

        Args:
            image_path: Path to the PNG image file
            category: Optional category name
            previous_page_context: Optional context from previous page

        Returns:
            Markdown formatted string
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        self.logger.info("Extracting page: {}", image_path)

        # Extract page number
        page_number = extract_page_number_from_filename(image_path)
        source_filename = os.path.basename(image_path)

        # Load image
        image = Image.open(image_path)

        # Build context information
        context_info = self._build_markdown_context(previous_page_context)

        # Build prompt
        prompt = self._build_markdown_prompt(
            document_title=self.manual_metadata.get('document_title', 'SKILL Manual'),
            manual_code=self.manual_metadata.get('manual_code', 'unknown'),
            page_number=page_number or 0,
            source_filename=source_filename,
            context_info=context_info
        )

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
        self.raw_data_recorder.record_api_call(
            page_num=page_number or 0,
            system_prompt=SYSTEM_INSTRUCTION,
            user_prompt=prompt,
            ai_response=response.text,
            image_path=image_path,
            metadata=self.manual_metadata,
            operation="extract"
        )

        markdown_text = response.text.strip()

        # Clean up markdown
        markdown_text = clean_markdown_response(markdown_text)

        # Validate basic structure
        if not self._validate_markdown(markdown_text):
            self.logger.warning("Markdown validation failed")

        self.logger.info("Extraction successful")
        return markdown_text

    def merge_pages(self, pages: List[str]) -> str:
        """
        Merge multiple markdown pages into a single document

        Args:
            pages: List of markdown content strings

        Returns:
            Merged markdown content
        """
        if not pages:
            return ""

        if len(pages) == 1:
            return pages[0]

        self.logger.info("Merging {} pages", len(pages))

        # Parse all pages
        parsed_pages = []
        for md in pages:
            front_matter, content = self._parse_front_matter(md)
            parsed_pages.append({
                'front_matter': front_matter,
                'content': content
            })

        # Extract metadata from first page
        first_fm = parsed_pages[0]['front_matter']

        # Update page range metadata
        start_pages = []
        end_pages = []
        source_images = []

        for page in parsed_pages:
            fm = page['front_matter']
            if 'page_number' in fm:
                try:
                    page_num = int(fm['page_number'])
                    start_pages.append(page_num)
                    end_pages.append(page_num)
                except:
                    pass
            if 'source_image' in fm:
                source_images.append(fm['source_image'])

        # Build merged front matter
        merged_fm = first_fm.copy()
        merged_fm['page_type'] = 'merged_function'
        if start_pages:
            merged_fm['start_page'] = str(min(start_pages))
            merged_fm['end_page'] = str(max(end_pages))

        # Build front matter text
        merged_front_matter = "---\n"
        for key, value in merged_fm.items():
            merged_front_matter += f"{key}: {value}\n"
        merged_front_matter += f"source_images:\n"
        for img in source_images:
            merged_front_matter += f"  - {img}\n"
        merged_front_matter += "---\n\n"

        # Merge content sections
        first_content = parsed_pages[0]['content']

        # Get function name from first H1
        h1_match = re.search(r'^# (.+?)(?:\s+\*\(continued\)\*)?$', first_content, re.MULTILINE)
        function_name = h1_match.group(1).strip() if h1_match else None

        merged_content = first_content

        # Append subsequent pages
        for i in range(1, len(parsed_pages)):
            content = parsed_pages[i]['content']

            # Remove H1 if it's the same function (continuation)
            if function_name:
                content = re.sub(
                    rf'^# {re.escape(function_name)}\s*\*?\(continued\)\*?\s*\n',
                    '',
                    content,
                    flags=re.MULTILINE
                )

            # Append with separator
            merged_content += "\n\n" + content

        return merged_front_matter + merged_content

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _build_markdown_context(self, previous_page_context: Optional[Dict]) -> str:
        """Build context information for Markdown prompt"""
        if not previous_page_context:
            return ""

        prev_func = previous_page_context.get('current_function')
        prev_category = previous_page_context.get('category')
        prev_has_table = previous_page_context.get('has_table', False)

        if not prev_func:
            return ""

        context_info = f"""
📋 CONTEXT FROM PREVIOUS PAGE:
- Previous function: **{prev_func}**
- Category: {prev_category or 'Unknown'}
- Previous page had table: {'Yes' if prev_has_table else 'No'}

⚠️ IMPORTANT: If this page is a continuation of '{prev_func}', use the same function name and mark sections with *(continued)*.
"""
        return context_info

    def _build_markdown_prompt(
        self,
        document_title: str,
        manual_code: str,
        page_number: int,
        source_filename: str,
        context_info: str
    ) -> str:
        """Build extraction prompt for Markdown format"""

        prompt = f"""
You are a technical documentation expert specializing in extracting SKILL programming language documentation from images.

{context_info}

📖 **YOUR TASK**: Convert this SKILL function documentation page to well-structured Markdown format.

---

## 🎯 OUTPUT FORMAT

```markdown
---
page_type: new_function | continuation | category
page_number: {page_number}
source_image: {source_filename}
manual: {document_title}
category: [Extract from page or use from context]
extraction_timestamp: {datetime.utcnow().isoformat()}Z
previous_function: [Only if continuation page]
---

# [Function Name]

## Syntax

```skill
functionName(arg1 arg2 @optional arg3) => returnType
```

## Description

[Main description...]

## Arguments

- **`arg1`** (`type`) - Description
- **`arg2`** (`type`) - Description
- **`arg3`** (`type`) *(optional)* - Description

## Return Value

[Return value description]

## Examples

```skill
; Example 1
functionName(value1 value2)
=> result
```

## Tables

### [Table Title]

| Column1 | Column2 | Column3 |
|---------|---------|---------|
| value   | value   | value   |

## Notes

- Note 1
- Note 2

## Related Topics

- [RelatedFunction](related-function.md)
```

---

## 🔍 CRITICAL DETECTION RULES

### Rule 1: NEW FUNCTION PAGE Detection

A page is a NEW function page ONLY if it has **ALL** of these:

✅ **Large function name heading** (H1 level)
✅ **Function call syntax at THE VERY TOP of content area**
✅ **Format**: `functionName(parameters)` or `functionName( ... ) => returnType`
✅ **Position**: MUST appear BEFORE any section headings

**⚠️ CRITICAL POSITION RULE:**
- Function syntax MUST be at THE VERY TOP of content area
- If page starts with "Arguments", "Examples", "Description" → CONTINUATION, NOT new function
- Syntax in Examples section does NOT count as new function

### Rule 2: Section Headings are NOT Function Names

These are **ALWAYS** section titles, **NEVER** new function names:
- "Arguments", "Description", "Value Returned", "Examples", "Notes"

---

🚀 **Now extract this page to Markdown following the format above.**

Return ONLY the Markdown content (including YAML front matter), no additional explanation or wrapping.
"""
        return prompt

    def _parse_front_matter(self, markdown_text: str) -> Tuple[Dict, str]:
        """Parse YAML front matter from markdown"""
        if not markdown_text.startswith('---'):
            return {}, markdown_text

        # Find end of front matter
        end_match = re.search(r'\n---\n', markdown_text[3:])
        if not end_match:
            return {}, markdown_text

        front_matter_text = markdown_text[3:3 + end_match.start()]
        content = markdown_text[3 + end_match.end():]

        # Parse front matter (simple key: value parsing)
        front_matter = {}
        for line in front_matter_text.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                front_matter[key] = value

        return front_matter, content

    def _validate_markdown(self, markdown_text: str) -> bool:
        """Validate markdown structure"""
        if not markdown_text:
            return False

        # Should have front matter
        if not markdown_text.startswith('---'):
            return False

        # Should have at least one H1 heading
        if '\n# ' not in markdown_text and not markdown_text.startswith('# '):
            return False

        # Should have at least one H2 section
        if '\n## ' not in markdown_text:
            return False

        return True

    def extract_metadata_from_markdown(self, markdown_text: str) -> Dict:
        """Extract metadata needed for continuation detection"""
        front_matter, content = self._parse_front_matter(markdown_text)

        # Extract function name from H1
        h1_match = re.search(r'^# (.+?)(?:\s+\*\(continued\)\*)?$', content, re.MULTILINE)
        function_name = h1_match.group(1).strip() if h1_match else None

        # Check if has table
        has_table = '|' in content and '---' in content

        # Extract table columns if present
        table_columns = []
        if has_table:
            table_match = re.search(r'\|(.+?)\|\n\|[-:\s|]+\|', content)
            if table_match:
                header_line = table_match.group(1)
                table_columns = [col.strip() for col in header_line.split('|')]

        return {
            'page_type': front_matter.get('page_type', 'unknown'),
            'current_function': function_name,
            'category': front_matter.get('category'),
            'has_table': has_table,
            'table_columns': table_columns
        }


def save_individual_markdown(
    markdown_content: str,
    function_name: str,
    category: str,
    output_base_dir: str,
    manual_code: str
) -> str:
    """
    Save individual function markdown to structured directory

    Output structure:
        output_base_dir/
            manual_code/
                category/
                    function_name.md
    """
    # Normalize names
    sanitized_name = sanitize_filename(function_name)
    normalized_category = extract_category_name(category)

    # Build directory structure
    category_dir = os.path.join(output_base_dir, manual_code, normalized_category)
    os.makedirs(category_dir, exist_ok=True)

    # Build output file path
    output_path = os.path.join(category_dir, f"{sanitized_name}.md")

    # Save markdown
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    return output_path


# ============================================================================
# Main Entry Point (for backward compatibility)
# ============================================================================

def main():
    """Main entry point (kept for backward compatibility)"""
    print("Note: This script has been refactored to use the new BaseConverter architecture.")
    print("For the unified CLI, use gemini_manual_converter.py instead.")
    print()
    print("Please use the new unified converter:")
    print("  python3 scripts/gemini_manual_converter.py --format markdown ...")
    sys.exit(1)


if __name__ == '__main__':
    main()
