#!/usr/bin/env python3
"""
SKILL Markdown Function Page Merger

Merges multiple Markdown pages belonging to the same SKILL function into a single complete document.

This tool:
1. Detects which pages belong to the same function
2. Merges sections intelligently (concatenate examples, merge tables, etc.)
3. Produces clean, complete function documentation

Usage:
    # Merge all markdown files in a directory
    python3 merge_markdown_functions.py \\
        --input-dir output_markdown/ \\
        --output-dir merged_functions/

    # Merge specific range
    python3 merge_markdown_functions.py \\
        --input-dir output_markdown/ \\
        --pattern "sklangref-*.md" \\
        --output-dir merged_functions/

Author: Claude Code
Version: 1.0
Date: 2025-10-12
"""

import os
import re
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict


class MarkdownMerger:
    """Merge multiple markdown pages for the same function"""

    def __init__(self):
        pass

    def parse_markdown_file(self, filepath: str) -> Dict:
        """
        Parse a markdown file into structured sections

        Args:
            filepath: Path to markdown file

        Returns:
            Dictionary with:
                - front_matter: Dict of YAML front matter
                - function_name: str
                - sections: Dict of section_name -> content
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse front matter
        front_matter = {}
        body = content

        if content.startswith('---'):
            end_match = re.search(r'\n---\n', content[3:])
            if end_match:
                front_matter_text = content[3:3 + end_match.start()]
                body = content[3 + end_match.end():]

                # Parse YAML (simple key: value)
                for line in front_matter_text.split('\n'):
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        front_matter[key.strip()] = value.strip()

        # Extract function name from H1
        h1_match = re.search(r'^# (.+?)(?:\s+\*\(continued\)\*)?$', body, re.MULTILINE)
        function_name = h1_match.group(1).strip() if h1_match else None

        # Parse sections (H2 headers)
        sections = {}
        current_section = None
        section_lines = []

        for line in body.split('\n'):
            # Check for H2 header
            h2_match = re.match(r'^## (.+?)(?:\s+\*\(continued\)\*)?$', line)
            if h2_match:
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(section_lines).strip()

                # Start new section
                current_section = h2_match.group(1).strip()
                section_lines = []
            elif current_section:
                section_lines.append(line)

        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(section_lines).strip()

        return {
            'filepath': filepath,
            'filename': os.path.basename(filepath),
            'front_matter': front_matter,
            'function_name': function_name,
            'sections': sections
        }

    def group_pages_by_function(self, parsed_pages: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group parsed pages by function name

        Args:
            parsed_pages: List of parsed page dictionaries

        Returns:
            Dict mapping function_name -> list of pages
        """
        groups = defaultdict(list)

        for page in parsed_pages:
            function_name = page['function_name']
            if function_name:
                groups[function_name].append(page)
            else:
                # Use filename as key for pages without function name
                groups[f"_unknown_{page['filename']}"].append(page)

        return dict(groups)

    def merge_sections(self, pages: List[Dict]) -> Dict[str, str]:
        """
        Merge sections from multiple pages

        Args:
            pages: List of page dictionaries (in order)

        Returns:
            Dict of merged sections
        """
        merged = {}

        # Define section merge strategies
        CONCATENATE_SECTIONS = ['Examples', 'Notes', 'Related Topics']
        TABLE_SECTIONS = ['Tables']
        FIRST_ONLY_SECTIONS = ['Syntax', 'Description', 'Arguments', 'Return Value']

        all_section_names = set()
        for page in pages:
            all_section_names.update(page['sections'].keys())

        for section_name in all_section_names:
            contents = []
            for page in pages:
                if section_name in page['sections']:
                    content = page['sections'][section_name]
                    if content:
                        contents.append(content)

            if not contents:
                continue

            # Apply merge strategy
            if section_name in CONCATENATE_SECTIONS:
                # Concatenate with separator
                merged[section_name] = '\n\n'.join(contents)

            elif section_name in TABLE_SECTIONS:
                # Merge tables (concatenate, removing duplicate headers)
                merged[section_name] = self._merge_table_sections(contents)

            elif section_name in FIRST_ONLY_SECTIONS:
                # Take from first page only
                merged[section_name] = contents[0]

            else:
                # Unknown section: concatenate with separator
                merged[section_name] = '\n\n'.join(contents)

        return merged

    def _merge_table_sections(self, table_sections: List[str]) -> str:
        """
        Merge multiple table sections, removing duplicate headers

        Args:
            table_sections: List of table section contents

        Returns:
            Merged table section
        """
        if not table_sections:
            return ""

        if len(table_sections) == 1:
            return table_sections[0]

        # Parse tables from each section
        merged_tables = {}

        for section_content in table_sections:
            # Find all tables in this section (H3 title + table)
            tables = re.findall(
                r'### (.+?)\n\n(\|.+?\n\|[-:\s|]+\n(?:\|.+?\n)+)',
                section_content,
                re.DOTALL
            )

            for table_title, table_content in tables:
                # Remove *(continued)* from title
                clean_title = re.sub(r'\s*\*\(continued\)\*\s*', '', table_title)

                if clean_title not in merged_tables:
                    # First occurrence: store header and rows
                    lines = table_content.strip().split('\n')
                    merged_tables[clean_title] = {
                        'header': lines[0],
                        'separator': lines[1],
                        'rows': lines[2:] if len(lines) > 2 else []
                    }
                else:
                    # Continuation: append rows only (skip header)
                    lines = table_content.strip().split('\n')
                    if len(lines) > 2:
                        merged_tables[clean_title]['rows'].extend(lines[2:])

        # Reconstruct table section
        result_parts = []
        for title, table_data in merged_tables.items():
            result_parts.append(f"### {title}\n")
            result_parts.append(table_data['header'])
            result_parts.append(table_data['separator'])
            result_parts.extend(table_data['rows'])
            result_parts.append('')  # Blank line after table

        return '\n'.join(result_parts).strip()

    def create_merged_markdown(self, function_name: str, pages: List[Dict], merged_sections: Dict[str, str]) -> str:
        """
        Create final merged markdown document

        Args:
            function_name: Name of the function
            pages: List of source pages
            merged_sections: Merged sections

        Returns:
            Complete markdown document
        """
        # Use front matter from first page
        first_page = pages[0]
        front_matter = first_page['front_matter'].copy()

        # Update front matter
        front_matter['page_type'] = 'merged'
        front_matter['source_pages'] = ', '.join([p['filename'] for p in pages])
        front_matter['page_count'] = str(len(pages))

        # Remove continuation-specific fields
        front_matter.pop('previous_function', None)

        # Build document
        lines = ['---']

        # Output front matter
        for key, value in front_matter.items():
            lines.append(f'{key}: {value}')

        lines.append('---')
        lines.append('')

        # Function name
        lines.append(f'# {function_name}')
        lines.append('')

        # Sections in standard order
        SECTION_ORDER = [
            'Syntax',
            'Description',
            'Arguments',
            'Return Value',
            'Examples',
            'Tables',
            'Notes',
            'Related Topics'
        ]

        for section_name in SECTION_ORDER:
            if section_name in merged_sections:
                lines.append(f'## {section_name}')
                lines.append('')
                lines.append(merged_sections[section_name])
                lines.append('')

        # Add any sections not in standard order
        for section_name, content in merged_sections.items():
            if section_name not in SECTION_ORDER:
                lines.append(f'## {section_name}')
                lines.append('')
                lines.append(content)
                lines.append('')

        # Footer
        lines.append('---')
        source_pages = ', '.join([p['filename'] for p in pages])
        lines.append(f'*Merged from: {source_pages}*')

        return '\n'.join(lines)

    def merge_function_pages(self, input_dir: str, output_dir: str, pattern: str = "*.md"):
        """
        Merge all function pages in a directory

        Args:
            input_dir: Input directory with markdown files
            output_dir: Output directory for merged files
            pattern: File pattern to match (default: "*.md")
        """
        # Find all markdown files
        input_path = Path(input_dir)
        markdown_files = sorted(input_path.glob(pattern))

        if not markdown_files:
            print(f"❌ No markdown files found matching pattern: {pattern}")
            return

        print(f"📚 Found {len(markdown_files)} markdown files")

        # Parse all files
        print(f"\n📖 Parsing files...")
        parsed_pages = []
        for filepath in markdown_files:
            try:
                parsed = self.parse_markdown_file(str(filepath))
                parsed_pages.append(parsed)
                print(f"  ✅ {filepath.name}")
            except Exception as e:
                print(f"  ❌ {filepath.name}: {e}")

        # Group by function
        print(f"\n🔍 Grouping pages by function...")
        function_groups = self.group_pages_by_function(parsed_pages)

        print(f"   Found {len(function_groups)} unique functions/groups")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Merge each function group
        print(f"\n🔀 Merging function pages...")
        for function_name, pages in function_groups.items():
            print(f"\n📝 Function: {function_name}")
            print(f"   Pages: {len(pages)}")

            if len(pages) == 1:
                # Single page: just copy
                print(f"   (single page, copying)")
                output_filename = f"{function_name}.md"
                output_path = os.path.join(output_dir, output_filename)

                with open(pages[0]['filepath'], 'r', encoding='utf-8') as f:
                    content = f.read()

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            else:
                # Multiple pages: merge
                print(f"   (merging {len(pages)} pages)")

                # Sort pages by filename
                pages_sorted = sorted(pages, key=lambda p: p['filename'])

                # Merge sections
                merged_sections = self.merge_sections(pages_sorted)

                # Create merged document
                merged_markdown = self.create_merged_markdown(
                    function_name=function_name,
                    pages=pages_sorted,
                    merged_sections=merged_sections
                )

                # Save output
                output_filename = f"{function_name}.md"
                output_path = os.path.join(output_dir, output_filename)

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(merged_markdown)

                print(f"   ✅ Saved to {output_filename}")

        print(f"\n✅ Merging complete!")
        print(f"   Output directory: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Merge SKILL function markdown pages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Merge all markdown files
  python3 merge_markdown_functions.py \\
      --input-dir output_markdown/ \\
      --output-dir merged_functions/

  # Merge specific pattern
  python3 merge_markdown_functions.py \\
      --input-dir output_markdown/ \\
      --pattern "sklangref-*.md" \\
      --output-dir merged_functions/
        """
    )

    parser.add_argument('--input-dir', required=True, help='Input directory with markdown files')
    parser.add_argument('--output-dir', required=True, help='Output directory for merged files')
    parser.add_argument('--pattern', default='*.md', help='File pattern to match (default: *.md)')

    args = parser.parse_args()

    # Validate input directory
    if not os.path.isdir(args.input_dir):
        print(f"❌ Error: Input directory not found: {args.input_dir}")
        return 1

    # Run merger
    merger = MarkdownMerger()
    merger.merge_function_pages(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        pattern=args.pattern
    )

    return 0


if __name__ == '__main__':
    exit(main())
