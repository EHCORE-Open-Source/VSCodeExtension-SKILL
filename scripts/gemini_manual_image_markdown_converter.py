#!/usr/bin/env python3
"""
SKILL Manual Image to Markdown Converter using Google Gemini API

This script converts SKILL manual PNG images to structured Markdown format.
Markdown provides better AI accuracy, easier human review, and simpler processing.

Key improvements over JSON approach:
1. Higher AI accuracy (natural format for LLMs)
2. Easy human review and correction
3. Git-friendly (clear diffs)
4. Native table support
5. Graceful degradation (partial extraction still useful)

Usage:
    # Single image
    python3 gemini_manual_image_markdown_converter.py \\
        --image docs/cadence_manual/images/sklangref/sklangref-594.png \\
        --manual-code sklangref \\
        --product-code SKILL \\
        --version "6.1.8" \\
        --document-title "Cadence SKILL Language Reference" \\
        --output output.md

    # Range of images
    python3 gemini_manual_image_markdown_converter.py \\
        --range sklangref-594 sklangref-601 \\
        --image-dir docs/cadence_manual/images/sklangref/ \\
        --manual-code sklangref \\
        --product-code SKILL \\
        --version "6.1.8" \\
        --document-title "Cadence SKILL Language Reference" \\
        --output-dir output_markdown/

Author: Claude Code
Version: 1.0
Date: 2025-10-12
"""

import os
import sys
import re
import argparse
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from pathlib import Path

# Check for required packages
try:
    from PIL import Image
    from google import genai
except ImportError as e:
    print(f"Error: Required package not found: {e}")
    print("Please install required packages:")
    print("  pip install Pillow google-genai")
    sys.exit(1)

# Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_BASE_URL = os.getenv('GOOGLE_GEMINI_BASE_URL')
GEMINI_MODEL = 'gemini-2.5-flash-lite'  # Use same model as JSON converter

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY environment variable not set")
    print("Please set it with: export GEMINI_API_KEY='your-api-key'")
    sys.exit(1)


class GeminiMarkdownConverter:
    """Convert SKILL manual images to Markdown using Gemini Vision API"""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        """
        Initialize Gemini client

        Args:
            api_key: Google Gemini API key
            base_url: Base URL for Gemini API (optional)
        """
        self.api_key = api_key
        self.base_url = base_url or GEMINI_BASE_URL

        # Initialize Gemini client with custom base URL if provided
        if self.base_url:
            self.client = genai.Client(api_key=self.api_key, http_options={'base_url': self.base_url})
        else:
            self.client = genai.Client(api_key=self.api_key)

    def extract_page_to_markdown(
        self,
        image_path: str,
        manual_code: str,
        product_code: str,
        version: str,
        document_title: str,
        previous_page_context: Optional[Dict] = None,
        max_retries: int = 3
    ) -> str:
        """
        Extract SKILL function page to Markdown format

        Args:
            image_path: Path to PNG image
            manual_code: Manual code (e.g., 'sklangref')
            product_code: Product code (e.g., 'SKILL')
            version: Document version
            document_title: Full document title
            previous_page_context: Context from previous page (for continuation detection)
            max_retries: Maximum number of retry attempts

        Returns:
            Markdown formatted string
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Extract page number from filename
        page_match = re.search(r'-(\d+)\.png$', image_path)
        page_number = int(page_match.group(1)) if page_match else 0

        source_filename = os.path.basename(image_path)

        # Build context information for prompt
        context_info = ""
        if previous_page_context:
            prev_func = previous_page_context.get('current_function')
            prev_category = previous_page_context.get('category')
            prev_has_table = previous_page_context.get('has_table', False)

            if prev_func:
                context_info = f"""
📋 CONTEXT FROM PREVIOUS PAGE:
- Previous function: **{prev_func}**
- Category: {prev_category or 'Unknown'}
- Previous page had table: {'Yes' if prev_has_table else 'No'}

⚠️ IMPORTANT: If this page is a continuation of '{prev_func}', use the same function name and mark sections with *(continued)*.
"""

        # Load image
        image = Image.open(image_path)

        # Build prompt
        prompt = self._build_extraction_prompt(
            document_title=document_title,
            manual_code=manual_code,
            page_number=page_number,
            source_filename=source_filename,
            context_info=context_info,
            previous_page_context=previous_page_context
        )

        # Retry loop
        for attempt in range(max_retries):
            try:
                print(f"  Attempt {attempt + 1}/{max_retries}...", end=" ")

                response = self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=[prompt, image]
                )

                markdown_text = response.text.strip()

                # Clean up markdown (remove any wrapping code blocks)
                markdown_text = self._clean_markdown_response(markdown_text)

                # Validate basic structure
                if self._validate_markdown(markdown_text):
                    print("✅ Success")
                    return markdown_text
                else:
                    print(f"⚠️ Validation failed (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        print("❌ All attempts failed validation, returning last attempt")
                        return markdown_text

            except Exception as e:
                print(f"❌ Error: {e}")
                if attempt < max_retries - 1:
                    print(f"  Retrying...")
                    continue
                else:
                    raise

        raise Exception(f"Failed to extract markdown after {max_retries} attempts")

    def _build_extraction_prompt(
        self,
        document_title: str,
        manual_code: str,
        page_number: int,
        source_filename: str,
        context_info: str,
        previous_page_context: Optional[Dict]
    ) -> str:
        """Build the extraction prompt for Gemini"""

        # Build table continuation hint
        table_hint = ""
        if previous_page_context and previous_page_context.get('has_table'):
            table_columns = previous_page_context.get('table_columns', [])
            if table_columns:
                columns_str = ', '.join(f'"{col}"' for col in table_columns)
                table_hint = f"""
🔍 **TABLE CONTINUATION DETECTION**:

The previous page had a table with columns: {columns_str}

**HIGHLY LIKELY SCENARIO**: If this page shows similar column structure:
→ This is a TABLE CONTINUATION, not a new function!
→ Mark table as "*(continued)*"
→ Use `page_type: continuation` in front matter
→ Use same function name as previous page: {previous_page_context.get('current_function')}

Example for continuation:
```markdown
---
page_type: continuation
previous_function: {previous_page_context.get('current_function')}
---

# {previous_page_context.get('current_function')} *(continued)*

## Tables

### Table Name *(continued)*

| {' | '.join(table_columns)} |
|{'|'.join(['---'] * len(table_columns))}|
| ... data ... |
```
"""

        prompt = f"""
You are a technical documentation expert specializing in extracting SKILL programming language documentation from images.

{context_info}

{table_hint}

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
✅ **Position**: MUST appear BEFORE any section headings (Description, Arguments, Examples, etc.)

**Example of NEW function page**:
```
───────────────────────────
append                         ← Function name (H1)

append(l_list1 l_list2)       ← Function call syntax at TOP (REQUIRED!)
=> l_result                      ← BEFORE "Description" section

Description                    ← Section heading comes AFTER syntax

Concatenates two lists...
───────────────────────────
```

**⚠️ CRITICAL POSITION RULE:**
- Function syntax MUST be at THE VERY TOP of content area
- If page starts with "Arguments", "Examples", "Description" → CONTINUATION, NOT new function
- Syntax in Examples section does NOT count as new function
- **Without syntax at top → NOT a new function!**

### Rule 2: Section Headings are NOT Function Names

These are **ALWAYS** section titles within a function, **NEVER** new function names:
- "Arguments"
- "Description"
- "Value Returned" / "Return Value"
- "Examples"
- "Notes"
- "Related Topics"
- "See Also"

**Example of CONTINUATION page** (NOT new function):
```
───────────────────────────
Arguments                     ← Section heading (NOT function name!)

  s_name         Name of...  ← Part of previous function
  g_switchValue  New value...

Examples                      ← Another section heading

  sstatus(debugMode t)
───────────────────────────
```

→ This is a CONTINUATION, use `page_type: continuation`

### Rule 3: Table Continuation

If you see tabular data with the SAME column structure as previous page:
→ Very likely a table continuation
→ Use `page_type: continuation`
→ Mark table title with "*(continued)*"

---

## 📝 MARKDOWN FORMATTING GUIDELINES

### Front Matter (YAML)
- **REQUIRED**: Always include YAML front matter at top
- **page_type**: Choose `new_function`, `continuation`, or `category`
- **previous_function**: Include if `page_type: continuation`

### Headings
- **H1 (`#`)**: Function name only
- **H2 (`##`)**: Major sections (Syntax, Description, Arguments, etc.)
- **H3 (`###`)**: Sub-sections (table titles, sub-topics)

### Code Blocks
- **Always** use fenced code blocks: ```skill ... ```
- Use `skill` language identifier
- Include comments in examples: `; This is a comment`
- Show results with `=>`

### Arguments
- Use bullet lists
- Bold argument name with backticks: **`argName`**
- Include type in parentheses: `(symbol)`, `(list)`, `(number)`
- Mark optional args: *(optional)*

### Tables
- Use standard Markdown table syntax
- Include header row
- Align columns with pipes `|`
- For continuation tables, add "*(continued)*" to title

### Handling Uncertainty
- If unsure about type: `(type unclear - REVIEW)`
- If table structure complex: Add note `<!-- AI: Table structure unclear -->`
- **Better to mark uncertainty than guess wrong**

---

## 🎨 VISUAL CUES TO MARKDOWN MAPPING

| Visual Element | Markdown |
|----------------|----------|
| Large heading at top | `# FunctionName` |
| Medium section headings | `## Section Name` |
| Code with syntax highlighting | ```skill ... ``` |
| Lists with type prefixes | Bullet list in Arguments |
| Tabular data | Markdown table |
| Inline code/variables | `` `code` `` |
| Bold text | `**bold**` |
| Notes/warnings | Bullet list in Notes |

---

## ⚠️ COMMON MISTAKES TO AVOID

❌ **Don't** treat "Arguments" as a function name
❌ **Don't** output JSON format
❌ **Don't** skip front matter (YAML)
❌ **Don't** use `json` code blocks (use `skill`)
❌ **Don't** invent information not visible in image
❌ **Don't** use HTML tags (use Markdown syntax)

✅ **Do** use standard Markdown syntax
✅ **Do** include YAML front matter
✅ **Do** mark sections with *(continued)* if continuation
✅ **Do** preserve code formatting and whitespace
✅ **Do** include all visible tables and examples
✅ **Do** mark uncertainty with comments

---

## 📊 OUTPUT REQUIREMENTS

1. **Start with YAML front matter** (between `---` delimiters)
2. **Include H1 function name** (or category name)
3. **Use proper section headings** (H2 for major sections)
4. **Format code blocks** with ```skill ... ```
5. **Create proper tables** if tabular data present
6. **Extract all visible content** (don't summarize)
7. **Mark continuations clearly** with *(continued)*

---

🚀 **Now extract this page to Markdown following the format above.**

Return ONLY the Markdown content (including YAML front matter), no additional explanation or wrapping.
"""

        return prompt

    def _clean_markdown_response(self, markdown_text: str) -> str:
        """Clean up Gemini's markdown response"""

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

    def _validate_markdown(self, markdown_text: str) -> bool:
        """
        Validate markdown structure

        Returns:
            True if valid, False otherwise
        """
        # Basic checks
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

    def parse_front_matter(self, markdown_text: str) -> Tuple[Dict, str]:
        """
        Parse YAML front matter from markdown

        Args:
            markdown_text: Full markdown text

        Returns:
            Tuple of (front_matter_dict, content_without_frontmatter)
        """
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

    def extract_metadata_from_markdown(self, markdown_text: str) -> Dict:
        """
        Extract metadata needed for continuation detection

        Args:
            markdown_text: Markdown content

        Returns:
            Dictionary with metadata
        """
        front_matter, content = self.parse_front_matter(markdown_text)

        # Extract function name from H1
        h1_match = re.search(r'^# (.+?)(?:\s+\*\(continued\)\*)?$', content, re.MULTILINE)
        function_name = h1_match.group(1).strip() if h1_match else None

        # Check if has table
        has_table = '|' in content and '---' in content

        # Extract table columns if present
        table_columns = []
        if has_table:
            # Find first table header
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


def merge_markdown_content(markdown_pages: List[str]) -> str:
    """
    Merge multiple markdown pages into a single markdown document

    Args:
        markdown_pages: List of markdown content strings

    Returns:
        Merged markdown content

    Strategy:
        - Use front matter from first page (with updated page range)
        - Concatenate content sections
        - Remove duplicate H1 headings (keep first)
    """
    if not markdown_pages:
        return ""

    if len(markdown_pages) == 1:
        return markdown_pages[0]

    # Parse all pages
    parsed_pages = []
    for md in markdown_pages:
        # Split front matter and content
        if md.startswith('---'):
            parts = md.split('---', 2)
            if len(parts) >= 3:
                front_matter_text = parts[1]
                content = parts[2].strip()
            else:
                front_matter_text = ""
                content = md
        else:
            front_matter_text = ""
            content = md

        parsed_pages.append({
            'front_matter_text': front_matter_text,
            'content': content
        })

    # Extract metadata from first page
    first_fm = parsed_pages[0]['front_matter_text']
    fm_lines = {}
    for line in first_fm.split('\n'):
        line = line.strip()
        if ':' in line:
            key, value = line.split(':', 1)
            fm_lines[key.strip()] = value.strip()

    # Update page range metadata
    # Extract start_page and end_page from all pages
    start_pages = []
    end_pages = []
    source_images = []

    for page in parsed_pages:
        fm_text = page['front_matter_text']
        for line in fm_text.split('\n'):
            line = line.strip()
            if line.startswith('page_number:'):
                page_num = line.split(':', 1)[1].strip()
                try:
                    page_num = int(page_num)
                    start_pages.append(page_num)
                    end_pages.append(page_num)
                except:
                    pass
            elif line.startswith('source_image:'):
                img = line.split(':', 1)[1].strip()
                source_images.append(img)

    # Build merged front matter
    fm_lines['page_type'] = 'merged_function'
    if start_pages:
        fm_lines['start_page'] = str(min(start_pages))
        fm_lines['end_page'] = str(max(end_pages))

    merged_front_matter = "---\n"
    for key, value in fm_lines.items():
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
            # Remove "# function_name (continued)" pattern
            content = re.sub(
                rf'^# {re.escape(function_name)}\s*\*?\(continued\)\*?\s*\n',
                '',
                content,
                flags=re.MULTILINE
            )

        # Append with separator
        merged_content += "\n\n" + content

    return merged_front_matter + merged_content


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

    Args:
        markdown_content: Markdown content string
        function_name: Function name
        category: Category name
        output_base_dir: Base output directory
        manual_code: Manual code (e.g., "sklangref")

    Returns:
        Path to saved markdown file
    """
    # Normalize names
    sanitized_name = sanitize_filename(function_name)
    normalized_category = extract_category_name(category)

    # Build directory structure: output_base_dir/manual_code/category/
    category_dir = os.path.join(output_base_dir, manual_code, normalized_category)
    os.makedirs(category_dir, exist_ok=True)

    # Build output file path
    output_path = os.path.join(category_dir, f"{sanitized_name}.md")

    # Save markdown
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    return output_path


def process_image_range(
    converter: GeminiMarkdownConverter,
    start_image: str,
    end_image: str,
    image_dir: str,
    manual_code: str,
    product_code: str,
    version: str,
    document_title: str,
    output_dir: str
) -> List[str]:
    """
    Process a range of images and save as individual function markdown files

    Args:
        converter: GeminiMarkdownConverter instance
        start_image: Start image name (e.g., 'sklangref-594')
        end_image: End image name (e.g., 'sklangref-601')
        image_dir: Directory containing images
        manual_code: Manual code
        product_code: Product code
        version: Version string
        document_title: Document title
        output_dir: Output directory for markdown files

    Returns:
        List of output markdown file paths
    """
    # Extract base name and numbers
    start_match = re.match(r'(.+?)-(\d+)$', start_image)
    end_match = re.match(r'(.+?)-(\d+)$', end_image)

    if not start_match or not end_match:
        raise ValueError(f"Invalid image range format: {start_image} to {end_image}")

    base_name = start_match.group(1)
    start_num = int(start_match.group(2))
    end_num = int(end_match.group(2))

    if start_num > end_num:
        raise ValueError(f"Start number {start_num} is greater than end number {end_num}")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Phase 1: Extract all pages
    print(f"📖 Processing range: {start_image} to {end_image}")
    print(f"   Total pages: {end_num - start_num + 1}\n")

    page_data = []
    previous_context = None
    current_category = None
    category_stack = []

    for page_num in range(start_num, end_num + 1):
        image_name = f"{base_name}-{page_num:03d}.png"
        image_path = os.path.join(image_dir, image_name)

        if not os.path.exists(image_path):
            print(f"  ⚠️  Warning: {image_name} not found, skipping")
            continue

        print(f"  Processing: {image_path}...", end=" ")

        try:
            markdown_text = converter.extract_page_to_markdown(
                image_path=image_path,
                manual_code=manual_code,
                product_code=product_code,
                version=version,
                document_title=document_title,
                previous_page_context=previous_context
            )

            # Extract metadata
            metadata = converter.extract_metadata_from_markdown(markdown_text)
            page_type = metadata.get('page_type', 'unknown')
            function_name = metadata.get('current_function')
            detected_category = metadata.get('category')

            # Update category tracking
            if detected_category:
                category_stack.append({'page': page_num, 'category': detected_category})
                if len(category_stack) > 5:
                    category_stack.pop(0)

            # Determine effective category
            effective_category = detected_category or current_category
            if not effective_category and category_stack:
                effective_category = category_stack[-1]['category']

            # Update current category
            if detected_category:
                current_category = detected_category

            page_data.append({
                'page_num': page_num,
                'markdown': markdown_text,
                'metadata': metadata,
                'page_type': page_type,
                'function_name': function_name,
                'category': effective_category
            })

            if page_type == 'new_function':
                print(f"✅ Function: {function_name}")
            elif page_type == 'continuation':
                print(f"✅ Function: {function_name} (continuation)")
            else:
                print(f"✅ Page type: {page_type}")

            # Update context for next iteration
            previous_context = metadata

        except Exception as e:
            print(f"❌ Error: {e}")
            continue

    # Phase 2: Group pages by function and merge
    print(f"\n{'='*80}")
    print(f"💾 Grouping and saving functions...")
    print(f"{'='*80}\n")

    function_groups = {}
    current_function = None

    for page in page_data:
        func_name = page['function_name']
        page_type = page['page_type']
        category = page['category']

        if page_type == 'new_function' and func_name:
            # Start new function
            current_function = func_name
            if current_function not in function_groups:
                function_groups[current_function] = {
                    'pages': [],
                    'category': category
                }
            function_groups[current_function]['pages'].append(page['markdown'])

        elif page_type == 'continuation' and current_function:
            # Add to current function
            if current_function not in function_groups:
                function_groups[current_function] = {
                    'pages': [],
                    'category': category
                }
            function_groups[current_function]['pages'].append(page['markdown'])

        else:
            # Reset current function (category page or unknown)
            current_function = None

    # Phase 3: Merge and save individual functions
    output_files = []

    for func_name, func_info in function_groups.items():
        try:
            # Merge pages
            if len(func_info['pages']) > 1:
                print(f"  ⚙️  Merging {len(func_info['pages'])} pages for '{func_name}'")
                merged_markdown = merge_markdown_content(func_info['pages'])
            else:
                merged_markdown = func_info['pages'][0]

            # Save individual file
            output_path = save_individual_markdown(
                markdown_content=merged_markdown,
                function_name=func_name,
                category=func_info['category'] or 'uncategorized',
                output_base_dir=output_dir,
                manual_code=manual_code
            )

            output_files.append(output_path)
            category = extract_category_name(func_info['category'] or 'uncategorized')
            print(f"  ✅ Saved: {manual_code}/{category}/{sanitize_filename(func_name)}.md")

        except Exception as e:
            print(f"  ❌ Failed to save {func_name}: {e}")

    print(f"\n{'='*80}")
    print(f"✅ Completed! Saved {len(output_files)} function(s)")
    print(f"📁 Base directory: {output_dir}")
    print(f"📂 Structure: {output_dir}/{manual_code}/<category>/<function>.md")
    print(f"{'='*80}")

    return output_files


def main():
    parser = argparse.ArgumentParser(
        description='Convert SKILL manual images to Markdown using Gemini Vision API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single image
  python3 gemini_manual_image_markdown_converter.py \\
      --image docs/cadence_manual/images/sklangref/sklangref-594.png \\
      --manual-code sklangref --product-code SKILL --version "6.1.8" \\
      --document-title "Cadence SKILL Language Reference" \\
      --output output.md

  # Range of images
  python3 gemini_manual_image_markdown_converter.py \\
      --range sklangref-594 sklangref-601 \\
      --image-dir docs/cadence_manual/images/sklangref/ \\
      --manual-code sklangref --product-code SKILL --version "6.1.8" \\
      --document-title "Cadence SKILL Language Reference" \\
      --output-dir output_markdown/
        """
    )

    # Single image mode
    parser.add_argument('--image', help='Path to single PNG image')
    parser.add_argument('--output', help='Output markdown file path (for single image)')

    # Range mode
    parser.add_argument('--range', nargs=2, metavar=('START', 'END'),
                        help='Process range of images (e.g., --range sklangref-594 sklangref-601)')
    parser.add_argument('--image-dir', help='Directory containing image files (for range mode)')
    parser.add_argument('--output-dir', help='Output directory for markdown files (for range mode)')

    # Common parameters
    parser.add_argument('--manual-code', required=True, help='Manual code (e.g., sklangref)')
    parser.add_argument('--product-code', required=True, help='Product code (e.g., SKILL)')
    parser.add_argument('--version', required=True, help='Document version (e.g., 6.1.8)')
    parser.add_argument('--document-title', required=True, help='Full document title')

    args = parser.parse_args()

    # Validate arguments
    if not args.image and not args.range:
        parser.error("Must specify either --image or --range")

    if args.image and not args.output:
        parser.error("--output required when using --image")

    if args.range and (not args.image_dir or not args.output_dir):
        parser.error("--image-dir and --output-dir required when using --range")

    # Initialize converter
    print(f"🚀 Initializing Gemini Markdown Converter...")
    print(f"   Model: {GEMINI_MODEL}")
    print(f"   Base URL: {GEMINI_BASE_URL}")

    converter = GeminiMarkdownConverter(
        api_key=GEMINI_API_KEY,
        base_url=GEMINI_BASE_URL
    )

    # Process images
    if args.image:
        # Single image mode
        print(f"\n📄 Processing single image: {args.image}")

        markdown_text = converter.extract_page_to_markdown(
            image_path=args.image,
            manual_code=args.manual_code,
            product_code=args.product_code,
            version=args.version,
            document_title=args.document_title
        )

        # Extract metadata to determine function name and category
        metadata = converter.extract_metadata_from_markdown(markdown_text)
        function_name = metadata.get('current_function', 'unknown')
        category = metadata.get('category', 'uncategorized')

        # Save using structured directory (if output_dir is provided) or to specified output file
        if args.output:
            # Direct output to specified file
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(markdown_text)
            print(f"\n✅ Markdown saved to: {args.output}")
        else:
            # Use structured directory (require --output-dir in this case)
            parser.error("--output required when using --image")

    else:
        # Range mode
        start_image, end_image = args.range
        print(f"\n📚 Processing image range: {start_image} to {end_image}")
        print(f"   Image directory: {args.image_dir}")
        print(f"   Output directory: {args.output_dir}")

        output_files = process_image_range(
            converter=converter,
            start_image=start_image,
            end_image=end_image,
            image_dir=args.image_dir,
            manual_code=args.manual_code,
            product_code=args.product_code,
            version=args.version,
            document_title=args.document_title,
            output_dir=args.output_dir
        )

        print(f"\n✅ Processed {len(output_files)} images")
        print(f"   Output directory: {args.output_dir}")


if __name__ == '__main__':
    main()
