#!/usr/bin/env python3
"""
SKILL Function Image Parser using Gemini API

This tool uses Google Gemini API to extract structured function information
from SKILL documentation images (PNG files).

Usage:
    # Parse a single image
    python3 parse_skill_image.py --image vivaxlskill-034.png

    # Parse multiple images as one function (for functions spanning multiple pages)
    python3 parse_skill_image.py --images vivaxlskill-046.png vivaxlskill-047.png vivaxlskill-048.png

    # Parse multiple images with pattern
    python3 parse_skill_image.py --image-pattern "vivaxlskill-*.png"

    # Parse and save to JSON
    python3 parse_skill_image.py --image vivaxlskill-034.png --output functions.json

    # Parse multi-page function and save
    python3 parse_skill_image.py --images vivaxlskill-046.png vivaxlskill-047.png --output awvAppendList.json

    # Parse a range and auto-group by function name
    python3 parse_skill_image.py --range vivaxlskill-034.png vivaxlskill-048.png --output-dir functions/

    # Batch process all images
    python3 parse_skill_image.py --batch --output-dir extracted/
"""

import os
import sys
import json
import argparse
import glob
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from PIL import Image
from google import genai

# Configuration
GEMINI_MODEL = "gemini-2.5-flash-lite"  # Use flash for better accuracy, or flash-lite for speed
API_KEY_ENV = "GEMINI_API_KEY"


class SkillImageParser:
    """Parser for SKILL function documentation images using Gemini API"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the parser with Gemini API client

        Args:
            api_key: Gemini API key (if None, reads from environment variable)
        """
        self.api_key = api_key or os.getenv(API_KEY_ENV)
        if not self.api_key:
            raise ValueError(f"API key not found. Set {API_KEY_ENV} environment variable or pass it as argument.")

        self.client = genai.Client(api_key=self.api_key)

    def parse_image(self, image_path: str) -> Dict:
        """
        Parse a SKILL function documentation image

        Args:
            image_path: Path to the PNG image file

        Returns:
            Dictionary containing structured function information
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Load image using PIL
        image = Image.open(image_path)

        # Construct prompt for structured extraction
        prompt = """
Analyze this SKILL function documentation image and extract the following information in JSON format:

{
  "function_name": "function name",
  "category": "category or section name if visible",
  "syntax": "function signature/syntax",
  "description": "brief description of what the function does",
  "arguments": [
    {
      "name": "argument name",
      "type": "data type if specified",
      "description": "argument description"
    }
  ],
  "return_value": [
    {
      "type": "return type",
      "description": "description of return value"
    }
  ],
  "examples": [
    {
      "code": "example code",
      "description": "example description if any"
    }
  ],
  "notes": "any additional notes or warnings",
  "page_number": "page number if visible",
  "document_title": "document title if visible"
}

Extract all visible information accurately. If a field is not present in the image, use null or empty array.
Return ONLY the JSON object, no additional text.
"""

        # Call Gemini API with image
        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, image]
        )

        # Parse JSON response
        try:
            # Extract JSON from response (may be wrapped in markdown code blocks)
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            function_data = json.loads(response_text.strip())
            function_data['source_image'] = os.path.basename(image_path)

            return function_data
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse JSON response for {image_path}")
            print(f"Response: {response.text}")
            return {
                "error": "JSON parsing failed",
                "raw_response": response.text,
                "source_image": os.path.basename(image_path)
            }

    def parse_multiple_images(self, image_paths: List[str]) -> Dict:
        """
        Parse multiple images of the same function (for functions spanning multiple pages)

        Args:
            image_paths: List of image file paths in order

        Returns:
            Dictionary containing structured function information from all pages
        """
        if not image_paths:
            raise ValueError("No image paths provided")

        # Validate all images exist
        for image_path in image_paths:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")

        # Load all images
        images = [Image.open(path) for path in image_paths]

        # Construct prompt for multi-page extraction
        prompt = f"""
Analyze these {len(images)} consecutive pages of SKILL function documentation and extract the complete information in JSON format:

{{
  "function_name": "function name",
  "category": "category or section name if visible",
  "syntax": "complete function signature/syntax",
  "description": "complete description of what the function does",
  "arguments": [
    {{
      "name": "argument name",
      "type": "data type if specified",
      "description": "complete argument description"
    }}
  ],
  "return_value": [
    {{
      "type": "return type",
      "description": "complete description of return value"
    }}
  ],
  "examples": [
    {{
      "code": "example code",
      "description": "example description if any"
    }}
  ],
  "notes": "any additional notes or warnings",
  "page_numbers": "page numbers if visible (e.g., '46-51')",
  "document_title": "document title if visible"
}}

Important: Combine information from ALL pages. If a section continues across pages, merge the content seamlessly.
Return ONLY the JSON object, no additional text.
"""

        # Build contents array with prompt and all images
        contents = [prompt] + images

        # Call Gemini API with all images
        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents
        )

        # Parse JSON response
        try:
            # Extract JSON from response (may be wrapped in markdown code blocks)
            response_text = response.text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            function_data = json.loads(response_text.strip())
            function_data['source_images'] = [os.path.basename(p) for p in image_paths]

            return function_data
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse JSON response for multiple images")
            print(f"Response: {response.text}")
            return {
                "error": "JSON parsing failed",
                "raw_response": response.text,
                "source_images": [os.path.basename(p) for p in image_paths]
            }

    def parse_image_simple(self, image_path: str) -> str:
        """
        Simple text extraction from image

        Args:
            image_path: Path to the PNG image file

        Returns:
            Extracted text content
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Load image using PIL
        image = Image.open(image_path)

        prompt = "Extract all text content from this SKILL documentation image. Preserve the structure and formatting as much as possible."

        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, image]
        )

        return response.text

    def batch_parse(self, image_pattern: str, output_dir: Optional[str] = None) -> List[Dict]:
        """
        Parse multiple images matching a pattern

        Args:
            image_pattern: Glob pattern for image files (e.g., "vivaxlskill-*.png")
            output_dir: Optional directory to save individual JSON files

        Returns:
            List of parsed function data
        """
        image_files = sorted(glob.glob(image_pattern))

        if not image_files:
            print(f"No images found matching pattern: {image_pattern}")
            return []

        print(f"Found {len(image_files)} images to process")

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        results = []
        for idx, image_file in enumerate(image_files, 1):
            print(f"Processing [{idx}/{len(image_files)}]: {image_file}")

            try:
                function_data = self.parse_image(image_file)
                results.append(function_data)

                # Save individual JSON if output directory specified
                if output_dir:
                    output_file = os.path.join(
                        output_dir,
                        Path(image_file).stem + '.json'
                    )
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(function_data, f, indent=2, ensure_ascii=False)
                    print(f"  Saved to: {output_file}")

            except Exception as e:
                print(f"  Error processing {image_file}: {e}")
                results.append({
                    "error": str(e),
                    "source_image": os.path.basename(image_file)
                })

        return results

    def detect_function_name(self, image_path: str) -> Optional[str]:
        """
        Detect function name from a single page image

        Args:
            image_path: Path to the PNG image file

        Returns:
            Function name or None if not found
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        image = Image.open(image_path)

        prompt = """
Look at this SKILL documentation page and identify the function name.
The function name is usually at the top of the page in a larger font or bold.
Return ONLY the function name, nothing else. If no function name is found, return "NONE".

Examples:
- "awvAddSubwindow"
- "awvAnalog2Digital"
- "NONE"
"""

        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, image]
        )

        function_name = response.text.strip()
        return None if function_name == "NONE" else function_name

    def parse_range_with_grouping(
        self,
        start_image: str,
        end_image: str,
        output_dir: Optional[str] = None
    ) -> Dict[str, Dict]:
        """
        Parse a range of images and automatically group by function name

        Args:
            start_image: Starting image filename (e.g., "vivaxlskill-034.png")
            end_image: Ending image filename (e.g., "vivaxlskill-048.png")
            output_dir: Optional directory to save grouped function JSON files

        Returns:
            Dictionary mapping function names to their data and source images
        """
        # Extract page numbers from filenames
        start_match = re.search(r'-(\d+)\.png$', start_image)
        end_match = re.search(r'-(\d+)\.png$', end_image)

        if not start_match or not end_match:
            raise ValueError("Invalid image filename format. Expected format: prefix-NNN.png")

        prefix = start_image[:start_image.rfind('-')]
        start_num = int(start_match.group(1))
        end_num = int(end_match.group(1))

        print(f"📖 Processing range: {start_image} to {end_image}")
        print(f"   Page numbers: {start_num} to {end_num} ({end_num - start_num + 1} pages)\n")

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # Step 1: Detect function names for each page
        print("🔍 Step 1: Detecting function names...")
        page_to_function = {}
        for page_num in range(start_num, end_num + 1):
            image_file = f"{prefix}-{page_num:03d}.png"

            if not os.path.exists(image_file):
                print(f"  ⚠️  Warning: {image_file} not found, skipping")
                continue

            print(f"  Analyzing: {image_file}...", end=" ")
            function_name = self.detect_function_name(image_file)

            if function_name:
                page_to_function[page_num] = {
                    'function': function_name,
                    'image': image_file
                }
                print(f"✅ {function_name}")
            else:
                # Continuation of previous function
                page_to_function[page_num] = {
                    'function': None,  # Will be filled later
                    'image': image_file
                }
                print("↳ (continuation)")

        # Step 2: Group consecutive pages by function
        print(f"\n📁 Step 2: Grouping pages by function...")
        grouped_functions = {}
        current_function = None

        for page_num in sorted(page_to_function.keys()):
            page_info = page_to_function[page_num]
            detected_function = page_info['function']

            if detected_function:
                # New function starts
                current_function = detected_function
                if current_function not in grouped_functions:
                    grouped_functions[current_function] = []

            if current_function:
                grouped_functions[current_function].append(page_info['image'])

        # Display grouping results
        for func_name, images in grouped_functions.items():
            print(f"  📌 {func_name}: {len(images)} page(s)")
            for img in images:
                print(f"     - {img}")

        # Step 3: Parse each function group
        print(f"\n🔄 Step 3: Parsing grouped functions...")
        results = {}

        for func_name, images in grouped_functions.items():
            print(f"\n  Processing: {func_name} ({len(images)} page(s))")

            try:
                if len(images) == 1:
                    # Single page function
                    function_data = self.parse_image(images[0])
                else:
                    # Multi-page function
                    function_data = self.parse_multiple_images(images)

                results[func_name] = function_data

                # Save to individual JSON file
                if output_dir:
                    output_file = os.path.join(output_dir, f"{func_name}.json")
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(function_data, f, indent=2, ensure_ascii=False)
                    print(f"    ✅ Saved to: {output_file}")

            except Exception as e:
                print(f"    ❌ Error: {e}")
                results[func_name] = {
                    "error": str(e),
                    "source_images": images
                }

        print(f"\n{'='*80}")
        print(f"✅ Completed! Processed {len(results)} function(s)")
        print(f"{'='*80}")

        return results


def main():
    parser = argparse.ArgumentParser(
        description='Parse SKILL function documentation images using Gemini API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--image',
        help='Path to a single image file to parse'
    )

    parser.add_argument(
        '--images',
        nargs='+',
        help='Multiple image files for a function spanning multiple pages (e.g., --images img1.png img2.png img3.png)'
    )

    parser.add_argument(
        '--image-pattern',
        help='Glob pattern for multiple images (e.g., "vivaxlskill-*.png")'
    )

    parser.add_argument(
        '--batch',
        action='store_true',
        help='Batch process all vivaxlskill-*.png images'
    )

    parser.add_argument(
        '--range',
        nargs=2,
        metavar=('START', 'END'),
        help='Parse a range of images and auto-group by function (e.g., --range vivaxlskill-034.png vivaxlskill-048.png)'
    )

    parser.add_argument(
        '--output',
        help='Output JSON file path (for single image or combined batch results)'
    )

    parser.add_argument(
        '--output-dir',
        help='Output directory for individual JSON files (batch mode)'
    )

    parser.add_argument(
        '--simple',
        action='store_true',
        help='Use simple text extraction instead of structured parsing'
    )

    parser.add_argument(
        '--api-key',
        help='Gemini API key (or set GEMINI_API_KEY environment variable)'
    )

    parser.add_argument(
        '--config',
        help='JSON configuration file specifying multiple functions and their images'
    )

    args = parser.parse_args()

    # Validate arguments
    if not any([args.image, args.images, args.image_pattern, args.batch, args.range, args.config]):
        parser.error("Must specify --image, --images, --image-pattern, --batch, --range, or --config")

    try:
        # Initialize parser
        image_parser = SkillImageParser(api_key=args.api_key)

        # Process range with auto-grouping
        if args.range:
            start_image, end_image = args.range
            results = image_parser.parse_range_with_grouping(
                start_image,
                end_image,
                output_dir=args.output_dir
            )

            # Save combined results if --output specified
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                print(f"\n📄 Combined results saved to: {args.output}")

        # Process from JSON configuration file
        elif args.config:
            if not os.path.exists(args.config):
                print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
                sys.exit(1)

            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)

            print(f"Loading configuration from: {args.config}")

            # Support two formats:
            # Format 1: {"function_name": ["img1.png", "img2.png"], ...}
            # Format 2: {"functions": [{"name": "func", "images": [...], "output": "out.json"}, ...]}

            if "functions" in config:
                # Format 2: Detailed configuration
                functions_config = config["functions"]
                print(f"Found {len(functions_config)} functions to process\n")

                results = []
                for idx, func_config in enumerate(functions_config, 1):
                    func_name = func_config.get("name", f"function_{idx}")
                    images = func_config.get("images", [])
                    output_file = func_config.get("output")

                    if not images:
                        print(f"[{idx}/{len(functions_config)}] Skipping {func_name}: No images specified")
                        continue

                    print(f"[{idx}/{len(functions_config)}] Processing {func_name} ({len(images)} images)")

                    try:
                        result = image_parser.parse_multiple_images(images)
                        results.append(result)

                        if output_file:
                            with open(output_file, 'w', encoding='utf-8') as f:
                                json.dump(result, f, indent=2, ensure_ascii=False)
                            print(f"  ✓ Saved to: {output_file}")
                        else:
                            print(f"  ✓ Parsed: {result.get('function_name', 'unknown')}")
                    except Exception as e:
                        print(f"  ✗ Error: {e}")
                        results.append({"error": str(e), "function": func_name})

                    print()

                print(f"{'='*80}")
                print(f"Completed: {len(results)} functions processed")
                print(f"{'='*80}")

                # Save combined results if --output specified
                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False)
                    print(f"Combined results saved to: {args.output}")

            else:
                # Format 1: Simple {"function_name": ["images"]} format
                print(f"Found {len(config)} functions to process\n")

                results = []
                for idx, (func_name, images) in enumerate(config.items(), 1):
                    if not isinstance(images, list):
                        print(f"[{idx}/{len(config)}] Skipping {func_name}: Invalid images format")
                        continue

                    print(f"[{idx}/{len(config)}] Processing {func_name} ({len(images)} images)")

                    try:
                        result = image_parser.parse_multiple_images(images)
                        results.append(result)

                        # Auto-generate output filename
                        output_file = f"{func_name}.json"
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(result, f, indent=2, ensure_ascii=False)
                        print(f"  ✓ Saved to: {output_file}")
                    except Exception as e:
                        print(f"  ✗ Error: {e}")
                        results.append({"error": str(e), "function": func_name})

                    print()

                print(f"{'='*80}")
                print(f"Completed: {len(results)} functions processed")
                print(f"{'='*80}")

        # Process multiple images as one function
        elif args.images:
            print(f"Parsing {len(args.images)} images as one function: {', '.join(args.images)}")

            result = image_parser.parse_multiple_images(args.images)
            print("\n" + "="*80)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("="*80)

            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print(f"\nSaved to: {args.output}")

        # Process single image
        elif args.image:
            print(f"Parsing image: {args.image}")

            if args.simple:
                result = image_parser.parse_image_simple(args.image)
                print("\n" + "="*80)
                print(result)
                print("="*80)
            else:
                result = image_parser.parse_image(args.image)
                print("\n" + "="*80)
                print(json.dumps(result, indent=2, ensure_ascii=False))
                print("="*80)

                if args.output:
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    print(f"\nSaved to: {args.output}")

        # Process multiple images
        elif args.image_pattern or args.batch:
            pattern = args.image_pattern or "vivaxlskill-*.png"
            results = image_parser.batch_parse(pattern, args.output_dir)

            print(f"\n{'='*80}")
            print(f"Processed {len(results)} images")
            print(f"{'='*80}")

            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                print(f"Combined results saved to: {args.output}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
