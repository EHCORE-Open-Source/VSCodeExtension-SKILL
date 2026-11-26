#!/usr/bin/env python3
"""
Unified SKILL Manual Converter - Main Entry Point

This is the unified CLI for converting SKILL manual images to various formats
using Google Gemini API for intelligent extraction.

Supported output formats:
- JSON: Database-ready format with complete metadata
- Markdown: Human-readable format with YAML front matter

Key Features:
- Unified interface for all converters
- Automatic page type detection
- Multi-page function support
- Category tracking
- Streaming processing for memory efficiency

Usage:
    # Convert to JSON
    python3 gemini_manual_converter.py --format json \\
        --range sklangref-031 sklangref-038 \\
        --image-dir docs/cadence_manual/images/sklangref/ \\
        --manual-code sklangref \\
        --product-code SKILL \\
        --version 6.1.8 \\
        --document-title "Cadence SKILL Language Reference" \\
        --output-dir test_output/

    # Convert to Markdown
    python3 gemini_manual_converter.py --format markdown \\
        --range sklangref-594 sklangref-601 \\
        --image-dir docs/cadence_manual/images/sklangref/ \\
        --manual-code sklangref \\
        --product-code SKILL \\
        --version "6.1.8" \\
        --document-title "Cadence SKILL Language Reference" \\
        --output-dir output_markdown/

    # Single image
    python3 gemini_manual_converter.py --format json \\
        --image docs/cadence_manual/images/sklangref/sklangref-034.png \\
        --manual-code sklangref \\
        --product-code SKILL \\
        --version 6.1.8 \\
        --document-title "Cadence SKILL Language Reference" \\
        --output output.json

Author: Claude Code
Version: 2.0 (Unified)
Date: 2025-10-14
"""

import os
import sys
import argparse
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

# Import converters
from gemini_manual_json_converter import JSONConverter, save_individual_function
from gemini_manual_markdown_converter import MarkdownConverter, save_individual_markdown

# Import utilities
from gemini_converter_utils import (
    sanitize_filename,
    extract_category_name,
    extract_page_number_from_filename
)


# ============================================================================
# Main Converter Orchestrator
# ============================================================================

class ConverterOrchestrator:
    """
    Orchestrates the conversion process for different formats

    This class manages:
    - Format selection (JSON/Markdown)
    - Converter initialization
    - Page processing workflow
    - Output file management
    """

    def __init__(
        self,
        output_format: str,
        manual_metadata: Dict,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        debug: bool = False,
        rawdata_dir: Optional[str] = None
    ):
        """
        Initialize converter orchestrator

        Args:
            output_format: Output format ('json' or 'markdown')
            manual_metadata: Manual metadata dictionary
            api_key: Gemini API key
            base_url: Custom Gemini API base URL
            debug: Enable debug logging
            rawdata_dir: Directory for raw data recording (None = disabled)
        """
        self.output_format = output_format.lower()
        self.manual_metadata = manual_metadata
        self.debug = debug
        self.rawdata_dir = rawdata_dir

        # Initialize appropriate converter
        if self.output_format == 'json':
            self.converter = JSONConverter(
                api_key=api_key,
                base_url=base_url,
                manual_metadata=manual_metadata,
                debug=debug,
                rawdata_dir=rawdata_dir
            )
        elif self.output_format == 'markdown':
            self.converter = MarkdownConverter(
                api_key=api_key,
                base_url=base_url,
                manual_metadata=manual_metadata,
                debug=debug,
                rawdata_dir=rawdata_dir
            )
        else:
            raise ValueError(f"Unsupported format: {output_format}. Use 'json' or 'markdown'.")

    def process_single_image(
        self,
        image_path: str,
        output_path: Optional[str] = None,
        output_dir: Optional[str] = None
    ):
        """
        Process a single image

        Args:
            image_path: Path to the PNG image file
            output_path: Direct output file path (optional)
            output_dir: Output directory for structured output (optional)
        """
        print(f"📖 Processing single image: {image_path}")

        # Detect page type
        page_type, function_name, category = self.converter.detect_page_type(image_path)

        print(f"   Page type: {page_type}")
        if function_name:
            print(f"   Function: {function_name}")
        if category:
            print(f"   Category: {category}")

        # Extract content
        result = self.converter.extract_page(image_path, category=category)

        # Save result
        if self.output_format == 'json':
            if output_path:
                # Save to specified path
                self.converter.save_to_json([result], output_path)
            else:
                # Save to structured directory
                base_dir = output_dir or 'test_output'
                saved_path = save_individual_function(
                    function_data=result,
                    output_base_dir=base_dir,
                    manual_code=self.manual_metadata['manual_code'],
                    manual_metadata=self.manual_metadata
                )
                print(f"\n✅ Saved to: {saved_path}")

        elif self.output_format == 'markdown':
            if output_path:
                # Save to specified path
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(result)
                print(f"\n✅ Saved to: {output_path}")
            else:
                # Save to structured directory
                base_dir = output_dir or 'output_markdown'
                metadata = self.converter.extract_metadata_from_markdown(result)
                func_name = metadata.get('current_function', function_name or 'unknown')
                cat = metadata.get('category', category or 'uncategorized')

                saved_path = save_individual_markdown(
                    markdown_content=result,
                    function_name=func_name,
                    category=cat,
                    output_base_dir=base_dir,
                    manual_code=self.manual_metadata['manual_code']
                )
                print(f"\n✅ Saved to: {saved_path}")

    def process_range(
        self,
        start_name: str,
        end_name: str,
        image_dir: str,
        output_dir: str
    ):
        """
        Process a range of images

        Args:
            start_name: Start image name (e.g., 'sklangref-031')
            end_name: End image name (e.g., 'sklangref-038')
            image_dir: Directory containing images
            output_dir: Output directory
        """
        from datetime import datetime

        # Record start time
        start_time = datetime.utcnow()

        # Extract page numbers
        start_match = re.search(r'-(\d+)', start_name)
        end_match = re.search(r'-(\d+)', end_name)

        if not start_match or not end_match:
            raise ValueError("Invalid range format. Expected format: prefix-NNN")

        prefix = start_name[:start_name.rfind('-')]
        start_num = int(start_match.group(1))
        end_num = int(end_match.group(1))

        print(f"📖 Processing range: {start_name} to {end_name}")
        print(f"   Total pages: {end_num - start_num + 1}\n")

        # Process pages
        pages = []
        current_category = None
        previous_function = None
        previous_page_context = None
        category_stack = []

        for page_num in range(start_num, end_num + 1):
            image_file = os.path.join(image_dir, f"{prefix}-{page_num:03d}.png")

            if not os.path.exists(image_file):
                print(f"  ⚠️  Warning: {image_file} not found, skipping")
                continue

            print(f"  Processing: {image_file}...", end=" ")

            # Detect page type
            page_type, function_name, detected_category = self.converter.detect_page_type(
                image_file,
                previous_function
            )

            # Update category tracking
            if detected_category:
                category_stack.append({'page': page_num, 'category': detected_category})
                if len(category_stack) > 5:
                    category_stack.pop(0)

            # Determine effective category
            effective_category = detected_category or current_category
            if not effective_category and category_stack:
                effective_category = category_stack[-1]['category']

            # Extract page content
            result = self.converter.extract_page(
                image_file,
                category=effective_category,
                previous_page_context=previous_page_context
            )

            # Handle based on page type
            if page_type == 'category':
                current_category = detected_category
                print(f"✅ Category: {current_category}")
                previous_function = None
                previous_page_context = None

            elif page_type == 'function':
                pages.append(result)
                func_name = function_name or 'unknown'
                print(f"✅ Function: {func_name}")
                previous_function = func_name

                # Update category
                if detected_category:
                    current_category = detected_category

                # Update context for next page
                if self.output_format == 'json':
                    previous_page_context = {
                        'function_name': func_name,
                        'has_table': 'table_data' in result,
                        'table_title': result.get('table_data', {}).get('title'),
                        'table_columns': result.get('table_data', {}).get('columns'),
                        'table_row_count': len(result.get('table_data', {}).get('rows', []))
                    }
                elif self.output_format == 'markdown':
                    metadata = self.converter.extract_metadata_from_markdown(result)
                    previous_page_context = metadata

            elif page_type == 'continuation':
                pages.append(result)
                func_name = function_name or previous_function or 'unknown'
                print(f"✅ Function: {func_name} (continuation)")

                # Update context for next page
                if self.output_format == 'json' and previous_page_context:
                    previous_page_context = {
                        'function_name': func_name,
                        'has_table': 'table_data' in result or previous_page_context.get('has_table', False),
                        'table_title': result.get('table_data', {}).get('title') or previous_page_context.get('table_title'),
                        'table_columns': result.get('table_data', {}).get('columns') or previous_page_context.get('table_columns'),
                        'table_row_count': previous_page_context.get('table_row_count', 0) + len(result.get('table_data', {}).get('rows', []))
                    }
                elif self.output_format == 'markdown':
                    metadata = self.converter.extract_metadata_from_markdown(result)
                    previous_page_context = metadata

            else:
                print("↳ (skipped)")
                previous_function = None
                previous_page_context = None

        # Merge and save results
        if not pages:
            print("\n⚠️  No pages extracted")
            return

        print(f"\n{'='*80}")
        print(f"💾 Processing {len(pages)} extracted page(s)...")
        print(f"{'='*80}\n")

        # Save results
        self._save_results(pages, output_dir)

        # Record batch summary
        end_time = datetime.utcnow()
        total_pages = end_num - start_num + 1

        if self.rawdata_dir:
            self.converter.raw_data_recorder.record_batch_summary(
                total_pages=total_pages,
                successful_pages=len(pages),
                failed_pages=total_pages - len(pages),
                start_time=start_time.isoformat() + "Z",
                end_time=end_time.isoformat() + "Z",
                metadata=self.manual_metadata
            )
            print(f"\n📊 Batch summary recorded to: {self.rawdata_dir}/batch_summary.json")

    def _save_results(self, pages: List[Any], output_dir: str):
        """Save processed results to output directory"""

        if self.output_format == 'json':
            # Merge duplicate functions
            merged_functions = self.converter.merge_pages(pages)

            print(f"  Saving {len(merged_functions)} function(s)...\n")

            saved_files = []
            for func in merged_functions:
                try:
                    output_path = save_individual_function(
                        function_data=func,
                        output_base_dir=output_dir,
                        manual_code=self.manual_metadata['manual_code'],
                        manual_metadata=self.manual_metadata
                    )
                    saved_files.append(output_path)
                    func_name = func.get('function_name', 'unknown')
                    category = extract_category_name(func.get('category', 'uncategorized'))
                    print(f"  ✅ Saved: {self.manual_metadata['manual_code']}/{category}/{sanitize_filename(func_name)}.json")
                except Exception as e:
                    func_name = func.get('function_name', 'unknown')
                    print(f"  ❌ Failed to save {func_name}: {e}")

            print(f"\n{'='*80}")
            print(f"✅ Completed! Saved {len(saved_files)} function(s)")
            print(f"📁 Base directory: {output_dir}")
            print(f"📂 Structure: {output_dir}/{self.manual_metadata['manual_code']}/<category>/<function>.json")
            print(f"{'='*80}")

        elif self.output_format == 'markdown':
            # Group pages by function and merge
            function_groups = self._group_markdown_pages(pages)

            print(f"  Saving {len(function_groups)} function(s)...\n")

            saved_files = []
            for func_name, func_info in function_groups.items():
                try:
                    # Merge pages
                    if len(func_info['pages']) > 1:
                        print(f"  ⚙️  Merging {len(func_info['pages'])} pages for '{func_name}'")
                        merged_markdown = self.converter.merge_pages(func_info['pages'])
                    else:
                        merged_markdown = func_info['pages'][0]

                    # Save individual file
                    output_path = save_individual_markdown(
                        markdown_content=merged_markdown,
                        function_name=func_name,
                        category=func_info['category'] or 'uncategorized',
                        output_base_dir=output_dir,
                        manual_code=self.manual_metadata['manual_code']
                    )

                    saved_files.append(output_path)
                    category = extract_category_name(func_info['category'] or 'uncategorized')
                    print(f"  ✅ Saved: {self.manual_metadata['manual_code']}/{category}/{sanitize_filename(func_name)}.md")

                except Exception as e:
                    print(f"  ❌ Failed to save {func_name}: {e}")

            print(f"\n{'='*80}")
            print(f"✅ Completed! Saved {len(saved_files)} function(s)")
            print(f"📁 Base directory: {output_dir}")
            print(f"📂 Structure: {output_dir}/{self.manual_metadata['manual_code']}/<category>/<function>.md")
            print(f"{'='*80}")

    def _group_markdown_pages(self, pages: List[str]) -> Dict[str, Dict]:
        """Group markdown pages by function"""
        function_groups = {}
        current_function = None

        for page in pages:
            metadata = self.converter.extract_metadata_from_markdown(page)
            func_name = metadata.get('current_function')
            page_type = metadata.get('page_type')
            category = metadata.get('category')

            if page_type == 'new_function' and func_name:
                current_function = func_name
                if current_function not in function_groups:
                    function_groups[current_function] = {
                        'pages': [],
                        'category': category
                    }
                function_groups[current_function]['pages'].append(page)

            elif page_type == 'continuation' and current_function:
                if current_function not in function_groups:
                    function_groups[current_function] = {
                        'pages': [],
                        'category': category
                    }
                function_groups[current_function]['pages'].append(page)

            else:
                current_function = None

        return function_groups


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Unified SKILL manual converter (JSON/Markdown)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert range to JSON
  python3 gemini_manual_converter.py --format json \\
      --range sklangref-031 sklangref-038 \\
      --image-dir docs/cadence_manual/images/sklangref/ \\
      --manual-code sklangref --product-code SKILL --version 6.1.8 \\
      --document-title "Cadence SKILL Language Reference" \\
      --output-dir test_output/

  # Convert range to Markdown
  python3 gemini_manual_converter.py --format markdown \\
      --range sklangref-594 sklangref-601 \\
      --image-dir docs/cadence_manual/images/sklangref/ \\
      --manual-code sklangref --product-code SKILL --version "6.1.8" \\
      --document-title "Cadence SKILL Language Reference" \\
      --output-dir output_markdown/

  # Convert single image to JSON
  python3 gemini_manual_converter.py --format json \\
      --image docs/cadence_manual/images/sklangref/sklangref-034.png \\
      --manual-code sklangref --product-code SKILL --version 6.1.8 \\
      --document-title "Cadence SKILL Language Reference" \\
      --output output.json
        """
    )

    # Format selection
    parser.add_argument(
        '--format',
        required=True,
        choices=['json', 'markdown'],
        help='Output format (json or markdown)'
    )

    # Input options
    parser.add_argument('--image', help='Path to a single image file')
    parser.add_argument('--range', nargs=2, metavar=('START', 'END'),
                        help='Convert a range of images (e.g., sklangref-031 sklangref-038)')
    parser.add_argument('--image-dir', default='.', help='Directory containing images (for --range)')

    # Manual metadata (required)
    parser.add_argument('--manual-code', required=True, help='Manual code (e.g., sklangref)')
    parser.add_argument('--product-code', required=True, help='Product code (e.g., SKILL)')
    parser.add_argument('--product-hierarchy-level', type=int, default=0,
                        help='Product hierarchy level (0=Core, 1=Family, 2=Product)')
    parser.add_argument('--version', required=True, help='Version string (e.g., 6.1.8)')
    parser.add_argument('--document-title', required=True, help='Document title')

    # Output options
    parser.add_argument('--output', help='Output file path (for single image)')
    parser.add_argument('--output-dir', help='Output directory (for range mode)')
    parser.add_argument('--rawdata-dir',
                        help='Directory for raw API call data (enables raw data recording). '
                             'If not specified, defaults to OUTPUT_DIR/rawdata when --output-dir is used.')

    # API options
    parser.add_argument('--api-key', help='Gemini API key (or set GEMINI_API_KEY environment variable)')
    parser.add_argument('--base-url', help='Custom Gemini API base URL (or set GOOGLE_GEMINI_BASE_URL)')

    # Debug option
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

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

    # Determine rawdata directory
    rawdata_dir = args.rawdata_dir
    if rawdata_dir is None and args.output_dir:
        # Default: use output_dir/rawdata
        rawdata_dir = os.path.join(args.output_dir, 'rawdata')
        print(f"📝 Raw data will be recorded to: {rawdata_dir}")

    try:
        # Initialize orchestrator
        print(f"🚀 Initializing {args.format.upper()} converter...")
        orchestrator = ConverterOrchestrator(
            output_format=args.format,
            manual_metadata=manual_metadata,
            api_key=args.api_key,
            base_url=args.base_url,
            debug=args.debug,
            rawdata_dir=rawdata_dir
        )

        # Process images
        if args.image:
            # Single image mode
            orchestrator.process_single_image(
                image_path=args.image,
                output_path=args.output,
                output_dir=args.output_dir
            )

        elif args.range:
            # Range mode
            if not args.output_dir:
                parser.error("--output-dir required when using --range")

            start_name, end_name = args.range
            orchestrator.process_range(
                start_name=start_name,
                end_name=end_name,
                image_dir=args.image_dir,
                output_dir=args.output_dir
            )

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
