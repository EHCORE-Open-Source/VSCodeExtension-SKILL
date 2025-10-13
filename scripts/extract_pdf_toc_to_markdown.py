#!/usr/bin/env python3
"""
PDF Table of Contents to Markdown Extractor

This script extracts function listings from PDF table of contents pages
and generates a well-formatted markdown documentation file.

Usage:
    python3 extract_pdf_toc_to_markdown.py --pdf vivaxlskill.pdf --pages 4-10 --output vivaxlskill-functions.md
    python3 extract_pdf_toc_to_markdown.py --images vivaxlskill-004.png,vivaxlskill-010.png --output functions.md
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import tempfile


@dataclass
class FunctionEntry:
    """Represents a single function entry from the TOC"""
    name: str
    page: int
    category: str = ""
    subcategory: str = ""
    description: str = ""

    def __repr__(self):
        return f"FunctionEntry({self.name}, page={self.page})"


@dataclass
class FunctionCategory:
    """Represents a category of functions"""
    name: str
    page: int
    level: int  # 1 = main category, 2 = subcategory
    functions: List[FunctionEntry] = field(default_factory=list)
    subcategories: List['FunctionCategory'] = field(default_factory=list)


class PDFTOCExtractor:
    """Extract table of contents from PDF files"""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.categories: List[FunctionCategory] = []

    def extract_pages_to_images(self, start_page: int, end_page: int,
                                output_dir: str = None, dpi: int = 150) -> List[str]:
        """
        Convert PDF pages to PNG images

        Args:
            start_page: Starting page number (1-indexed)
            end_page: Ending page number (1-indexed)
            output_dir: Output directory (default: temp directory)
            dpi: Resolution for conversion (default: 150)

        Returns:
            List of generated PNG file paths
        """
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="pdf_toc_")

        os.makedirs(output_dir, exist_ok=True)

        # Get base name without extension
        base_name = Path(self.pdf_path).stem
        output_prefix = os.path.join(output_dir, base_name)

        cmd = [
            'pdftoppm',
            '-png',
            '-r', str(dpi),
            '-f', str(start_page),
            '-l', str(end_page),
            self.pdf_path,
            output_prefix
        ]

        print(f"Converting PDF pages {start_page}-{end_page} to PNG...")
        print(f"Command: {' '.join(cmd)}")

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Error converting PDF: {e.stderr}")
            raise

        # Find generated files
        generated_files = sorted(Path(output_dir).glob(f"{base_name}-*.png"))
        print(f"Generated {len(generated_files)} images")

        return [str(f) for f in generated_files]

    def extract_text_from_pdf(self, start_page: int, end_page: int) -> str:
        """
        Extract text from PDF pages using pdftotext

        Args:
            start_page: Starting page number (1-indexed)
            end_page: Ending page number (1-indexed)

        Returns:
            Extracted text content
        """
        cmd = [
            'pdftotext',
            '-f', str(start_page),
            '-l', str(end_page),
            '-layout',  # Preserve layout
            self.pdf_path,
            '-'  # Output to stdout
        ]

        print(f"Extracting text from pages {start_page}-{end_page}...")

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Error extracting text: {e.stderr}")
            raise

    def parse_toc_text(self, text: str) -> List[FunctionCategory]:
        """
        Parse table of contents text and extract function entries

        Args:
            text: Raw text extracted from PDF

        Returns:
            List of function categories with their entries
        """
        lines = text.split('\n')
        categories = []
        current_category = None
        current_subcategory = None

        # Patterns for matching
        # Category: "2\nWaveform Window Functions . . . . . . 31"
        category_pattern = re.compile(r'^(\d+)\s*$')
        category_name_pattern = re.compile(r'^([A-Z][A-Za-z\s]+?)\s*\.{3,}\s*(\d+)\s*$')

        # Function entry (with leading whitespace): "    awvAddSubwindow . . . . . . 34"
        function_pattern = re.compile(r'^\s+(\w+)\s*\.{3,}\s*(\d+)\s*$')

        # Sometimes functions are listed without dots but with whitespace before page number
        function_pattern_alt = re.compile(r'^\s+(\w+)\s{10,}(\d+)\s*$')

        for i, line in enumerate(lines):
            if not line or len(line) < 3:
                continue

            # Check for category number (e.g., "2")
            stripped = line.strip()
            if category_pattern.match(stripped):
                # Next line should be category name
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    cat_match = category_name_pattern.match(next_line.strip())
                    if cat_match:
                        cat_name = cat_match.group(1).strip()
                        cat_page = int(cat_match.group(2))
                        current_category = FunctionCategory(
                            name=cat_name,
                            page=cat_page,
                            level=1
                        )
                        categories.append(current_category)
                        current_subcategory = None
                        continue

            # Check for function entry (must have leading whitespace)
            func_match = function_pattern.match(line)
            if not func_match:
                func_match = function_pattern_alt.match(line)

            if func_match and current_category:
                func_name = func_match.group(1).strip()
                func_page = int(func_match.group(2))

                func_entry = FunctionEntry(
                    name=func_name,
                    page=func_page,
                    category=current_category.name,
                    subcategory=current_subcategory.name if current_subcategory else ""
                )

                if current_subcategory:
                    current_subcategory.functions.append(func_entry)
                else:
                    current_category.functions.append(func_entry)

        return categories

    def extract_functions(self, start_page: int, end_page: int) -> List[FunctionCategory]:
        """
        Main method to extract function listings from PDF TOC

        Args:
            start_page: Starting page number
            end_page: Ending page number

        Returns:
            List of function categories
        """
        text = self.extract_text_from_pdf(start_page, end_page)
        categories = self.parse_toc_text(text)
        self.categories = categories
        return categories


class MarkdownGenerator:
    """Generate markdown documentation from extracted function data"""

    def __init__(self, pdf_name: str, categories: List[FunctionCategory]):
        self.pdf_name = pdf_name
        self.categories = categories

    def generate_header(self) -> str:
        """Generate markdown header"""
        pdf_base = Path(self.pdf_name).stem
        return f"""# {pdf_base.replace('_', ' ').title()} - Functions Reference

**Source**: {self.pdf_name}
**Generated**: {self._get_timestamp()}

---

## Table of Contents

{self._generate_toc()}

---

"""

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _generate_toc(self) -> str:
        """Generate table of contents"""
        toc_lines = []
        for i, cat in enumerate(self.categories, 1):
            anchor = cat.name.lower().replace(' ', '-').replace('_', '-')
            func_count = len(cat.functions)
            for subcat in cat.subcategories:
                func_count += len(subcat.functions)
            toc_lines.append(f"{i}. [{cat.name}](#{anchor}) ({func_count} functions)")
        return '\n'.join(toc_lines)

    def generate_category_section(self, category: FunctionCategory) -> str:
        """Generate markdown section for a category"""
        anchor = category.name.lower().replace(' ', '-').replace('_', '-')
        section = f"\n## {category.name}\n\n"

        if category.functions:
            section += "| Function | Page | Description |\n"
            section += "|----------|------|-------------|\n"

            for func in sorted(category.functions, key=lambda x: x.name):
                desc = func.description or "TBD"
                section += f"| `{func.name}` | {func.page} | {desc} |\n"

        # Add subcategories
        for subcat in category.subcategories:
            section += f"\n### {subcat.name}\n\n"
            if subcat.functions:
                section += "| Function | Page | Description |\n"
                section += "|----------|------|-------------|\n"

                for func in sorted(subcat.functions, key=lambda x: x.name):
                    desc = func.description or "TBD"
                    section += f"| `{func.name}` | {func.page} | {desc} |\n"

        return section

    def generate_summary(self) -> str:
        """Generate summary statistics"""
        total_functions = 0
        category_stats = []

        for cat in self.categories:
            func_count = len(cat.functions)
            for subcat in cat.subcategories:
                func_count += len(subcat.functions)

            total_functions += func_count
            category_stats.append(f"  - {cat.name}: {func_count}")

        summary = f"\n---\n\n## Summary\n\n"
        summary += f"- **Total Functions**: {total_functions}\n"
        summary += '\n'.join(category_stats) + '\n'

        return summary

    def generate(self) -> str:
        """Generate complete markdown document"""
        markdown = self.generate_header()

        for category in self.categories:
            markdown += self.generate_category_section(category)

        markdown += self.generate_summary()
        markdown += f"\n---\n\n*Generated from {self.pdf_name}*\n"

        return markdown


def main():
    parser = argparse.ArgumentParser(
        description='Extract function listings from PDF table of contents and generate markdown documentation'
    )

    parser.add_argument('--pdf', required=True, help='Input PDF file path')
    parser.add_argument('--pages', required=True, help='Page range (e.g., 4-10)')
    parser.add_argument('--output', required=True, help='Output markdown file path')
    parser.add_argument('--dpi', type=int, default=150, help='DPI for PDF to image conversion (default: 150)')
    parser.add_argument('--keep-images', action='store_true', help='Keep generated PNG images')
    parser.add_argument('--images-dir', help='Directory to save images (default: temp directory)')

    args = parser.parse_args()

    # Parse page range
    try:
        start_page, end_page = map(int, args.pages.split('-'))
    except ValueError:
        print(f"Error: Invalid page range format. Use format like '4-10'")
        sys.exit(1)

    # Check if PDF exists
    if not os.path.exists(args.pdf):
        print(f"Error: PDF file not found: {args.pdf}")
        sys.exit(1)

    # Extract functions
    print(f"\n{'='*60}")
    print(f"PDF TOC to Markdown Extractor")
    print(f"{'='*60}\n")

    extractor = PDFTOCExtractor(args.pdf)

    # Convert pages to images (for visual reference)
    if args.keep_images:
        images = extractor.extract_pages_to_images(
            start_page, end_page,
            output_dir=args.images_dir,
            dpi=args.dpi
        )
        print(f"Generated images: {len(images)}")
        for img in images:
            print(f"  - {img}")

    # Extract text and parse
    categories = extractor.extract_functions(start_page, end_page)

    print(f"\nExtracted {len(categories)} categories")

    # Generate markdown
    generator = MarkdownGenerator(args.pdf, categories)
    markdown_content = generator.generate()

    # Write output
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    print(f"\n✅ Generated markdown: {args.output}")
    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    main()
