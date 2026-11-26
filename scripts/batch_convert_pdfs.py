#!/usr/bin/env python3
"""
Batch PDF to PNG Conversion Script for SKILL Documentation
==========================================================

This script converts PDF files in priority order for SKILL function extraction.

Priority order:
1. Core SKILL language files (sklangref, skuiref)
2. Design environment files (skdfref, sklayoutref)
3. Specialized tools (vivaxlskill, maeSKILLref)
4. Other SKILL references

Usage:
    python3 scripts/batch_convert_pdfs.py
    python3 scripts/batch_convert_pdfs.py --priority-only
    python3 scripts/batch_convert_pdfs.py --resume
"""

import os
import sys
import time
from pathlib import Path

# Add the scripts directory to Python path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from pdf_to_png_converter import PDFToPNGConverter


def main():
    # Configuration
    input_dir = Path("docs/cadence_manual")
    output_dir = Path("images/skill_manuals")

    # Priority order for conversion
    priority_files = [
        # Tier 1: Core SKILL language (most important)
        "sklangref.pdf",      # SKILL Language Reference (783 pages)
        "skuiref.pdf",        # UI SKILL Reference (1557 pages)

        # Tier 2: Design environment (commonly used)
        "skdfref.pdf",        # Design Environment SKILL (2684 pages)
        "sklayoutref.pdf",    # Layout Suite SKILL (2656 pages)

        # Tier 3: Advanced features (important for specific use cases)
        "vivaxlskill.pdf",    # Visualization and Analysis XL (597 pages)
        "maeSKILLref.pdf",    # ADE SKILL Reference (2124 pages)

        # Tier 4: Specialized components
        "skcompref.pdf",      # Schematic Editor SKILL (498 pages)
        "sktechfile.pdf",     # Technology Data SKILL (598 pages)
        "oceanref.pdf",       # OCEAN Reference (726 pages)

        # Tier 5: Development and utilities
        "skdevref.pdf",       # SKILL Development Reference (223 pages)
        "skpcellref.pdf",     # Parameterized Cell SKILL (206 pages)
        "rodskillref.pdf",    # Relative Object Design SKILL (209 pages)

        # Tier 6: Infrastructure and specialized tools
        "caiskill.pdf",       # Application Infrastructure SKILL (183 pages)
        "verifierSkillRef.pdf", # ADE Verifier SKILL (418 pages)
        "sktransrefOA.pdf",   # Design Data Translators SKILL (152 pages)
        "skoopref.pdf",       # SKILL++ Object System (89 pages)
        "skipcref.pdf",       # Interprocess Communication SKILL (100 pages)
        "ocnxl.pdf",          # OCEAN XL Reference (232 pages)

        # Tier 7: Voltus tools (specialized power integrity)
        "voltusFIL.pdf",      # Voltus-Fi Custom Power Integrity (296 pages)
        "voltusFIXL.pdf",     # Voltus-Fi Custom Power Integrity XL (631 pages)
    ]

    print("🚀 SKILL Documentation PDF to PNG Batch Converter")
    print("=" * 60)

    # Check if all priority files exist
    missing_files = []
    for filename in priority_files:
        if not (input_dir / filename).exists():
            missing_files.append(filename)

    if missing_files:
        print(f"⚠️  Missing files: {missing_files}")
        return False

    # Create converter
    converter = PDFToPNGConverter(output_dir=str(output_dir), dpi=300)

    # Get current conversion status
    stats = converter.get_conversion_stats()
    print(f"📊 Current status: {stats['total_pdfs']} PDFs converted, {stats['total_images']} images")

    # Process files in priority order
    total_files = len(priority_files)
    converted_count = 0
    failed_files = []

    print("\n🔄 Starting conversion in priority order...")
    print("-" * 60)

    for i, filename in enumerate(priority_files, 1):
        pdf_path = input_dir / filename

        # Check if already converted
        pdf_stem = pdf_path.stem
        if pdf_stem in converter.metadata:
            existing_images = converter.metadata[pdf_stem].get('images', [])
            if existing_images and all(Path(img).exists() for img in existing_images):
                print(f"[{i:2d}/{total_files}] ✅ {filename:<20} Already converted ({len(existing_images)} images)")
                converted_count += 1
                continue

        print(f"[{i:2d}/{total_files}] 🔄 {filename:<20} Converting...")

        start_time = time.time()
        success, images = converter.convert_pdf_to_png(pdf_path, force=False)
        end_time = time.time()

        if success:
            duration = end_time - start_time
            print(f"[{i:2d}/{total_files}] ✅ {filename:<20} Success! {len(images)} images ({duration:.1f}s)")
            converted_count += 1
        else:
            print(f"[{i:2d}/{total_files}] ❌ {filename:<20} Failed!")
            failed_files.append(filename)

    # Final summary
    print("=" * 60)
    print(f"📊 Conversion Complete!")
    print(f"   Total files: {total_files}")
    print(f"   Successfully converted: {converted_count}")
    print(f"   Failed: {len(failed_files)}")

    if failed_files:
        print(f"   Failed files: {failed_files}")

    # Get final stats
    final_stats = converter.get_conversion_stats()
    print(f"   Total images generated: {final_stats['total_images']}")
    print(f"   Total PDF pages: {final_stats['total_pages']}")

    return len(failed_files) == 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Batch convert SKILL PDFs to PNG images")
    parser.add_argument('--priority-only', action='store_true',
                       help='Convert only tier 1-3 priority files')
    parser.add_argument('--resume', action='store_true',
                       help='Resume conversion (skip already converted files)')

    args = parser.parse_args()

    success = main()
    sys.exit(0 if success else 1)