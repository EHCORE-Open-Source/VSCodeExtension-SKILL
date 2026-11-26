#!/usr/bin/env python3
"""
PDF to PNG Conversion Tool for SKILL Documentation
==================================================

This tool converts PDF files to PNG images for processing with Gemini Vision API.

Features:
- Convert PDF files to high-quality PNG images
- Organize images by document name
- Generate metadata files for tracking
- Support for batch processing
- Resume capability (skip already converted files)

Usage:
    # Convert all PDFs in directory
    python3 scripts/pdf_to_png_converter.py --dir docs/cadence_manual --output images/skill_manuals

    # Convert specific file
    python3 scripts/pdf_to_png_converter.py --file docs/cadence_manual/sklangref.pdf --output images/skill_manuals

    # Convert files matching pattern (wildcard support)
    python3 scripts/pdf_to_png_converter.py --file "docs/cadence_manual/sk*.pdf" --output images/skill_manuals
    python3 scripts/pdf_to_png_converter.py --file "docs/cadence_manual/{sklang,skui}*.pdf" --output images/skill_manuals

    # List PDFs in directory
    python3 scripts/pdf_to_png_converter.py --list-pdfs docs/cadence_manual

    # Legacy input parameter (same as --dir)
    python3 scripts/pdf_to_png_converter.py --input docs/cadence_manual --output images/skill_manuals
"""

import os
import sys
import json
import argparse
import subprocess
import glob
import threading
import atexit
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import SimpleQueue
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Callable

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - optional dependency
    tqdm = None

try:
    import termios  # type: ignore
    import tty  # type: ignore
except ImportError:  # pragma: no cover - platform without termios
    termios = None  # type: ignore
    tty = None  # type: ignore


class ConversionAborted(Exception):
    """Raised when the user requests to stop the conversion."""


class PDFToPNGConverter:
    """Converts PDF files to PNG images with metadata tracking"""

    def __init__(self, output_dir: str, dpi: int = 300, quality: int = 95):
        """
        Initialize converter

        Args:
            output_dir: Base output directory for images
            dpi: DPI for image conversion (higher = better quality)
            quality: PNG compression quality (0-100)
        """
        self.output_dir = Path(output_dir)
        self.dpi = dpi
        self.quality = quality
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Metadata file for tracking conversions
        self.metadata_file = self.output_dir / "conversion_metadata.json"
        self.metadata = self._load_metadata()
        self.metadata_lock = threading.Lock()

        # Interactive abort handling
        self._stop_event = threading.Event()
        self._abort_message_shown = False
        self._abort_hint_shown = False
        self._interactive_input = sys.stdin.isatty()
        self._input_thread: Optional[threading.Thread] = None
        self._stdin_fd: Optional[int] = None
        self._terminal_settings = None
        self._raw_input_mode = False

        if self._interactive_input:
            self._start_input_monitor()

    def _load_metadata(self) -> Dict:
        """Load existing conversion metadata"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load metadata file: {e}")
                return {}
        return {}

    def _save_metadata(self):
        """Save conversion metadata"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Warning: Could not save metadata file: {e}")
 
    def _start_input_monitor(self):
        """Configure terminal input and start monitoring for abort requests."""
        try:
            self._stdin_fd = sys.stdin.fileno()
        except (ValueError, OSError):
            self._stdin_fd = None

        if self._stdin_fd is not None and termios is not None and tty is not None:
            try:
                if os.isatty(self._stdin_fd):
                    self._terminal_settings = termios.tcgetattr(self._stdin_fd)
                    tty.setcbreak(self._stdin_fd)
                    self._raw_input_mode = True
                    atexit.register(self._restore_terminal_settings)
            except Exception:
                self._terminal_settings = None
                self._raw_input_mode = False

        self._input_thread = threading.Thread(
            target=self._monitor_user_input,
            name="pdf-to-png-input-monitor",
            daemon=True
        )
        self._input_thread.start()

    def _restore_terminal_settings(self):
        """Restore terminal settings if raw mode was enabled."""
        if self._raw_input_mode and self._stdin_fd is not None and termios is not None:
            try:
                termios.tcsetattr(self._stdin_fd, termios.TCSADRAIN, self._terminal_settings)
            except Exception:
                pass
        self._raw_input_mode = False
        self._terminal_settings = None

    def _monitor_user_input(self):
        """Listen for user input to allow graceful aborts."""
        while not self._stop_event.is_set():
            try:
                if self._raw_input_mode:
                    user_input = sys.stdin.read(1)
                else:
                    user_input = sys.stdin.readline()
            except Exception:
                break

            if not user_input:
                break

            if user_input.strip().lower().startswith('q'):
                self._stop_event.set()
                break

    def _announce_abort(self, log):
        """Announce the abort event once."""
        if not self._abort_message_shown:
            log("🛑 Aborting conversion (q pressed). Finishing current task before exiting...")
            self._abort_message_shown = True
            self._restore_terminal_settings()

    def _check_for_abort(self, log):
        """Raise if an abort has been requested."""
        if self._stop_event.is_set():
            self._announce_abort(log)
            raise ConversionAborted()

    def _show_abort_hint(self, log):
        """Display a hint for how to abort the process once."""
        if self._interactive_input and not self._abort_hint_shown:
            if self._raw_input_mode:
                log("➡️  Press 'q' to abort conversion.")
            else:
                log("➡️  Press 'q' then Enter to abort conversion.")
            self._abort_hint_shown = True

    def has_announced_abort(self) -> bool:
        """Return whether the abort announcement has been shown."""
        return self._abort_message_shown

    def get_pdf_info(self, pdf_path: Path) -> Dict:
        """Get PDF information using pdfinfo"""
        try:
            result = subprocess.run(
                ['pdfinfo', str(pdf_path)],
                capture_output=True,
                text=True,
                check=True
            )

            info = {}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    info[key.strip().lower()] = value.strip()

            return info

        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not get PDF info for {pdf_path}: {e}")
            return {}

    def convert_pdf_to_png(
        self,
        pdf_path: Path,
        force: bool = False,
        progress_position: Optional[int] = None,
        pdf_info: Optional[Dict] = None,
        page_count_override: Optional[int] = None,
        progress_callback: Optional[Callable[[int], None]] = None,
        progress_leave: Optional[bool] = None,
        log_function: Optional[Callable[[str], None]] = None,
        show_abort_hint: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Convert PDF to PNG images

        Args:
            pdf_path: Path to PDF file
            force: Force reconversion even if images exist
            progress_position: tqdm position for per-file progress bars
            pdf_info: Optional precomputed pdfinfo dictionary
            page_count_override: Optional explicit page count
            progress_callback: Callback invoked after each converted page
            progress_leave: Override tqdm leave behaviour when using per-file bars

        Returns:
            Tuple of (success, list_of_generated_image_paths)
        """

        # Create output directory for this PDF
        pdf_name = pdf_path.stem
        pdf_output_dir = self.output_dir / pdf_name
        pdf_output_dir.mkdir(parents=True, exist_ok=True)

        if log_function is not None:
            log = log_function
        else:
            use_tqdm_logging = tqdm is not None and progress_position is not None
            log = tqdm.write if use_tqdm_logging else print

        if show_abort_hint:
            self._show_abort_hint(log)
        self._check_for_abort(log)

        # Check if already converted and not forcing
        if not force and pdf_name in self.metadata:
            existing_images = self.metadata[pdf_name].get('images', [])
            if existing_images and all(Path(img).exists() for img in existing_images):
                log(f"✅ {pdf_name}: Already converted ({len(existing_images)} images)")
                return True, existing_images

        if progress_callback is None:
            log(f"🔄 Converting {pdf_name}...")

        # Get PDF info
        if pdf_info is None:
            pdf_info = self.get_pdf_info(pdf_path)

        try:
            page_count = int(pdf_info.get('pages', 0))
        except (TypeError, ValueError):
            page_count = 0

        if page_count_override is not None:
            page_count = page_count_override

        if page_count == 0:
            log(f"❌ {pdf_name}: Could not determine page count")
            return False, []

        output_prefix = pdf_output_dir / pdf_name
        use_page_progress = tqdm is not None and page_count > 0 and progress_callback is None
        manual_page_progress = not use_page_progress and page_count > 1
        page_bar = None

        try:
            if use_page_progress:
                bar_kwargs = {
                    'total': page_count,
                    'desc': pdf_name,
                    'unit': 'page',
                    'dynamic_ncols': True
                }
                if progress_position is not None:
                    bar_kwargs['position'] = progress_position
                if progress_leave is not None:
                    bar_kwargs['leave'] = progress_leave
                elif progress_position is not None:
                    bar_kwargs['leave'] = False
                else:
                    bar_kwargs['leave'] = True
                page_bar = tqdm(**bar_kwargs)
            elif manual_page_progress:
                print(f"   Pages: 0/{page_count}", end="\r", flush=True)

            for page_number in range(1, page_count + 1):
                self._check_for_abort(log)
                cmd = [
                    'pdftoppm',
                    '-png',
                    '-r', str(self.dpi),
                    '-cropbox',
                    '-f', str(page_number),
                    '-l', str(page_number),
                    str(pdf_path),
                    str(output_prefix)
                ]

                subprocess.run(cmd, capture_output=True, text=True, check=True)

                if page_bar is not None:
                    page_bar.update(1)
                if progress_callback is not None:
                    progress_callback(1)
                elif manual_page_progress:
                    print(f"   Pages: {page_number}/{page_count}", end="\r", flush=True)

            if page_bar is not None:
                page_bar.close()
            elif manual_page_progress:
                print()  # Move to next line after carriage return

            self._check_for_abort(log)

            # Find generated images
            generated_images = list(pdf_output_dir.glob(f"{pdf_name}-*.png"))
            generated_images.sort()  # Sort by filename

            if not generated_images:
                log(f"❌ {pdf_name}: No images generated")
                return False, []

            # Update metadata
            image_paths = [str(img) for img in generated_images]
            with self.metadata_lock:
                self.metadata[pdf_name] = {
                    'pdf_path': str(pdf_path),
                    'images': image_paths,
                    'page_count': len(generated_images),
                    'pdf_pages': page_count,
                    'conversion_date': datetime.now().isoformat(),
                    'dpi': self.dpi,
                    'pdf_info': pdf_info
                }
                self._save_metadata()

            log(f"✅ {pdf_name}: Converted {len(generated_images)} pages")
            return True, image_paths

        except ConversionAborted:
            if page_bar is not None:
                page_bar.close()
            elif manual_page_progress:
                print()
            raise

        except subprocess.CalledProcessError as e:
            if page_bar is not None:
                page_bar.close()
            elif manual_page_progress:
                print()
            log(f"❌ {pdf_name}: Conversion failed - {e}")
            if e.stderr:
                log(f"   Error: {e.stderr}")
            return False, []

    def convert_directory(self, input_dir: Path, force: bool = False, threads: int = 1) -> Dict[str, bool]:
        """Convert all PDF files in a directory"""

        pdf_files = list(input_dir.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in {input_dir}")
            return {}

        total_requested_pdfs = len(pdf_files)

        print(f"Found {total_requested_pdfs} PDF files in {input_dir}")
        print("=" * 60)

        results = {}
        total_images = 0
        threads = max(1, threads)

        if threads == 1:
            use_progress = tqdm is not None and len(pdf_files) > 1

            progress_bar = None
            if use_progress:
                progress_bar = tqdm(
                    total=len(pdf_files),
                    desc="Converting PDFs",
                    unit="file",
                    position=0,
                    leave=False,
                    dynamic_ncols=True
                )
                iterator = enumerate(pdf_files, 1)
            else:
                iterator = enumerate(pdf_files, 1)

            progress_log = tqdm.write if use_progress else print

            try:
                for i, pdf_path in iterator:
                    self._check_for_abort(progress_log)

                    if use_progress:
                        progress_bar.set_postfix_str(pdf_path.name)
                    else:
                        print(f"[{i}/{len(pdf_files)}] Processing {pdf_path.name}...")

                    success, images = self.convert_pdf_to_png(
                        pdf_path,
                        force=force,
                        progress_position=1 if use_progress else None
                    )
                    results[pdf_path.name] = success

                    if success:
                        total_images += len(images)

                    if use_progress:
                        progress_bar.update(1)
            except ConversionAborted:
                if progress_bar is not None:
                    progress_bar.close()
                raise

            if progress_bar is not None:
                progress_bar.close()

            self._check_for_abort(progress_log)

        else:
            progress_log = tqdm.write if tqdm is not None else print
            self._show_abort_hint(progress_log)

            master_bar = tqdm(
                total=len(pdf_files),
                desc="Converting PDFs",
                unit="file",
                position=0,
                leave=True,
                dynamic_ncols=True
            ) if tqdm is not None else None

            slot_pool: Optional[SimpleQueue] = None
            if tqdm is not None:
                slot_pool = SimpleQueue()
                for slot in range(1, threads + 1):
                    slot_pool.put(slot)

            def worker(pdf_path: Path) -> Tuple[str, Tuple[bool, List[str]], Optional[Exception]]:
                self._check_for_abort(progress_log)
                slot = None
                if slot_pool is not None:
                    slot = slot_pool.get()

                try:
                    result = self.convert_pdf_to_png(
                        pdf_path,
                        force=force,
                        progress_position=slot if slot is not None else None,
                        progress_leave=False if slot is not None else None,
                        log_function=progress_log,
                        show_abort_hint=False
                    )
                    return pdf_path.name, result, None
                except ConversionAborted:
                    raise
                except Exception as exc:
                    return pdf_path.name, (False, []), exc
                finally:
                    if slot is not None:
                        slot_pool.put(slot)

            with ThreadPoolExecutor(max_workers=threads) as executor:
                futures = [executor.submit(worker, pdf_path) for pdf_path in pdf_files]

                try:
                    for future in as_completed(futures):
                        try:
                            pdf_name, (success, images), error = future.result()
                        except ConversionAborted:
                            executor.shutdown(wait=False, cancel_futures=True)
                            if master_bar is not None:
                                master_bar.clear()
                                master_bar.close()
                            raise
                        except Exception as exc:
                            progress_log(f"❌ Unexpected error during conversion: {exc}")
                            continue

                        if error is not None:
                            progress_log(f"❌ {pdf_name}: Conversion failed - {error}")
                            success = False
                            images = []

                        results[pdf_name] = success
                        if success:
                            total_images += len(images)
                            if master_bar is not None:
                                master_bar.set_postfix_str(pdf_name)
                        else:
                            progress_log(f"❌ {pdf_name}: Conversion failed")

                        if master_bar is not None:
                            master_bar.update(1)
                            master_bar.refresh()
                finally:
                    if master_bar is not None:
                        master_bar.clear()
                        master_bar.close()

            self._check_for_abort(progress_log)

        print("=" * 60)
        print(f"📊 Conversion Summary:")
        print(f"   Total PDFs: {total_requested_pdfs}")
        print(f"   Successful: {sum(results.values())}")
        print(f"   Failed: {total_requested_pdfs - sum(results.values())}")
        print(f"   Total images: {total_images}")

        return results

    def list_pdfs(self, input_dir: Path) -> List[Dict]:
        """List all PDF files with basic information"""

        pdf_files = list(input_dir.glob("*.pdf"))
        pdf_info_list = []

        print(f"📚 Found {len(pdf_files)} PDF files in {input_dir}:")
        print("-" * 80)

        for pdf_path in sorted(pdf_files):
            file_size = pdf_path.stat().st_size
            size_mb = file_size / (1024 * 1024)

            # Get PDF info
            pdf_info = self.get_pdf_info(pdf_path)
            pages = pdf_info.get('pages', 'Unknown')
            title = pdf_info.get('title', pdf_path.stem)

            info = {
                'filename': pdf_path.name,
                'size_mb': round(size_mb, 2),
                'pages': pages,
                'title': title,
                'path': str(pdf_path)
            }

            pdf_info_list.append(info)

            # Check if already converted
            conversion_status = ""
            if pdf_path.stem in self.metadata:
                image_count = len(self.metadata[pdf_path.stem].get('images', []))
                conversion_status = f" (✅ {image_count} images)"

            print(f"{pdf_path.name:<25} {size_mb:>6.1f} MB  {pages:>4} pages{conversion_status}")
            if title != pdf_path.stem:
                print(f"  📖 {title}")

        return pdf_info_list

    def get_conversion_stats(self) -> Dict:
        """Get conversion statistics"""
        if not self.metadata:
            return {'total_pdfs': 0, 'total_images': 0, 'total_pages': 0}

        total_images = sum(len(doc.get('images', [])) for doc in self.metadata.values())
        total_pages = sum(doc.get('pdf_pages', 0) for doc in self.metadata.values())

        return {
            'total_pdfs': len(self.metadata),
            'total_images': total_images,
            'total_pages': total_pages,
            'conversion_details': self.metadata
        }

    def expand_file_patterns(self, file_pattern: str) -> List[Path]:
        """
        Expand file patterns with wildcards to actual file paths

        Args:
            file_pattern: File pattern (can include wildcards like *, ?, [] and {})

        Returns:
            List of matching PDF file paths
        """
        # Handle brace expansion manually since Python glob doesn't support it
        if '{' in file_pattern and '}' in file_pattern:
            # Simple brace expansion: {a,b,c} -> [a, b, c]
            import re
            brace_pattern = re.search(r'\{([^}]+)\}', file_pattern)
            if brace_pattern:
                options = brace_pattern.group(1).split(',')
                all_patterns = []
                for option in options:
                    expanded_pattern = file_pattern.replace(brace_pattern.group(0), option.strip())
                    all_patterns.append(expanded_pattern)

                # Recursively expand each pattern
                all_files = []
                for pattern in all_patterns:
                    all_files.extend(self.expand_file_patterns(pattern))
                return list(set(all_files))  # Remove duplicates

        # Handle both absolute and relative patterns
        if os.path.isabs(file_pattern):
            pattern = file_pattern
        else:
            pattern = os.path.abspath(file_pattern)

        # Use glob to expand wildcards
        matched_files = glob.glob(pattern)

        # Filter to only PDF files and convert to Path objects
        pdf_files = []
        for file_path in matched_files:
            path = Path(file_path)
            if path.is_file() and path.suffix.lower() == '.pdf':
                pdf_files.append(path)

        # Sort for consistent ordering
        pdf_files.sort()

        return pdf_files

    def convert_files_by_pattern(self, file_pattern: str, force: bool = False, threads: int = 1) -> Dict[str, bool]:
        """
        Convert PDF files matching a pattern

        Args:
            file_pattern: File pattern (can include wildcards)
            force: Force reconversion even if images exist
            threads: Number of worker threads to use (1 = sequential)

        Returns:
            Dict mapping filename to success status
        """
        pdf_files = self.expand_file_patterns(file_pattern)

        if not pdf_files:
            print(f"No PDF files found matching pattern: {file_pattern}")
            return {}

        total_requested_pdfs = len(pdf_files)

        print(f"Found {total_requested_pdfs} PDF files matching pattern: {file_pattern}")
        for pdf_file in pdf_files:
            print(f"  • {pdf_file.name}")
        print("=" * 60)

        results = {}
        total_images = 0
        threads = max(1, threads)

        if threads == 1:
            use_progress = tqdm is not None and len(pdf_files) > 1

            progress_bar = None
            if use_progress:
                progress_bar = tqdm(
                    total=len(pdf_files),
                    desc="Converting PDFs",
                    unit="file",
                    position=0,
                    leave=False,
                    dynamic_ncols=True
                )
                iterator = enumerate(pdf_files, 1)
            else:
                iterator = enumerate(pdf_files, 1)

            progress_log = tqdm.write if use_progress else print

            try:
                for i, pdf_path in iterator:
                    self._check_for_abort(progress_log)

                    if use_progress:
                        progress_bar.set_postfix_str(pdf_path.name)
                    else:
                        print(f"[{i}/{len(pdf_files)}] Processing {pdf_path.name}...")

                    success, images = self.convert_pdf_to_png(
                        pdf_path,
                        force=force,
                        progress_position=1 if use_progress else None
                    )
                    results[pdf_path.name] = success

                    if success:
                        total_images += len(images)

                    if use_progress:
                        progress_bar.update(1)
            except ConversionAborted:
                if progress_bar is not None:
                    progress_bar.close()
                raise

            if progress_bar is not None:
                progress_bar.close()

            self._check_for_abort(progress_log)

        else:
            progress_log = tqdm.write if tqdm is not None else print
            self._show_abort_hint(progress_log)

            master_bar = tqdm(
                total=len(pdf_files),
                desc="Converting PDFs",
                unit="file",
                position=0,
                leave=True,
                dynamic_ncols=True
            ) if tqdm is not None else None

            slot_pool: Optional[SimpleQueue] = None
            if tqdm is not None:
                slot_pool = SimpleQueue()
                for slot in range(1, threads + 1):
                    slot_pool.put(slot)

            def worker(pdf_path: Path) -> Tuple[str, Tuple[bool, List[str]], Optional[Exception]]:
                self._check_for_abort(progress_log)
                slot = None
                if slot_pool is not None:
                    slot = slot_pool.get()

                try:
                    result = self.convert_pdf_to_png(
                        pdf_path,
                        force=force,
                        progress_position=slot if slot is not None else None,
                        progress_leave=False if slot is not None else None,
                        log_function=progress_log,
                        show_abort_hint=False
                    )
                    return pdf_path.name, result, None
                except ConversionAborted:
                    raise
                except Exception as exc:
                    return pdf_path.name, (False, []), exc
                finally:
                    if slot is not None:
                        slot_pool.put(slot)

            with ThreadPoolExecutor(max_workers=threads) as executor:
                futures = [executor.submit(worker, pdf_path) for pdf_path in pdf_files]

                try:
                    for future in as_completed(futures):
                        try:
                            pdf_name, (success, images), error = future.result()
                        except ConversionAborted:
                            executor.shutdown(wait=False, cancel_futures=True)
                            if master_bar is not None:
                                master_bar.clear()
                                master_bar.close()
                            raise
                        except Exception as exc:
                            progress_log(f"❌ Unexpected error during conversion: {exc}")
                            continue

                        if error is not None:
                            progress_log(f"❌ {pdf_name}: Conversion failed - {error}")
                            success = False
                            images = []

                        results[pdf_name] = success
                        if success:
                            total_images += len(images)
                            if master_bar is not None:
                                master_bar.set_postfix_str(pdf_name)
                        else:
                            progress_log(f"❌ {pdf_name}: Conversion failed")

                        if master_bar is not None:
                            master_bar.update(1)
                            master_bar.refresh()
                finally:
                    if master_bar is not None:
                        master_bar.clear()
                        master_bar.close()

            self._check_for_abort(progress_log)

        print("=" * 60)
        print(f"📊 Conversion Summary:")
        print(f"   Pattern: {file_pattern}")
        print(f"   Total PDFs: {total_requested_pdfs}")
        print(f"   Successful: {sum(results.values())}")
        print(f"   Failed: {total_requested_pdfs - sum(results.values())}")
        print(f"   Total images: {total_images}")

        return results


def main():
    parser = argparse.ArgumentParser(
        description="""
🔄 PDF 轉 PNG 轉換工具 for SKILL 文檔處理
========================================

這個工具能夠將 PDF 檔案轉換為高品質的 PNG 圖像，專為 SKILL 文檔處理和
後續的 Gemini Vision API 分析而設計。支援單檔轉換、批次處理、通配符
匹配和斷點續傳功能。
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 使用範例：
============

📋 1. 查看目錄中的 PDF 檔案
   python3 %(prog)s --list-pdfs docs/cadence_manual

📁 2. 轉換整個目錄中的所有 PDF
   python3 %(prog)s --dir docs/cadence_manual --output images/skill_manuals

📄 3. 轉換單一 PDF 檔案
   python3 %(prog)s --file docs/cadence_manual/sklangref.pdf --output images/skill_manuals

🔍 4. 使用通配符批次轉換
   # 轉換所有以 sk 開頭的 PDF
   python3 %(prog)s --file "docs/cadence_manual/sk*.pdf" --output images/skill_manuals

   # 轉換特定檔案（大括號展開）
   python3 %(prog)s --file "docs/cadence_manual/{sklang,skui,skdev}*.pdf" --output images/skill_manuals

🔄 5. 強制重新轉換（覆蓋現有檔案）
   python3 %(prog)s --dir docs/cadence_manual --output images/skill_manuals --force

🎨 6. 高品質轉換（提高 DPI）
   python3 %(prog)s --dir docs/cadence_manual --output images/skill_manuals --dpi 450

📊 7. 查看轉換統計
   python3 %(prog)s --stats --output images/skill_manuals

🧵 8. 多緒加速轉換
   python3 %(prog)s --dir docs/cadence_manual --output images/skill_manuals --threads 4

💡 提示：
========
• 預設 DPI 為 300，適合一般用途
• 使用 --force 會覆蓋所有現有的 PNG 檔案
• 工具會自動追蹤轉換進度，支援斷點續傳
• 大檔案轉換可能需要較長時間，請耐心等待
• 轉換過程會生成詳細的元資料記錄
        """
    )

    parser.add_argument('--input', '-i', type=str,
                       help='📂 輸入目錄路徑（包含 PDF 檔案）- 舊版參數，建議使用 --dir')
    parser.add_argument('--dir', '-d', type=str,
                       help='📂 輸入目錄路徑（包含 PDF 檔案）- 轉換該目錄中的所有 PDF')
    parser.add_argument('--file', '-f', type=str,
                       help='📄 要轉換的 PDF 檔案路徑（支援通配符，如 *.pdf, {file1,file2}.pdf）')
    parser.add_argument('--output', '-o', type=str,
                       help='📁 PNG 圖像輸出目錄路徑')
    parser.add_argument('--list-pdfs', type=str,
                       help='📋 列出指定目錄中的 PDF 檔案（不進行轉換）')
    parser.add_argument('--dpi', type=int, default=300,
                       help='🎨 圖像轉換的 DPI 設定（預設: 300, 建議: 300-600）')
    parser.add_argument('--force', action='store_true',
                       help='🔄 強制重新轉換（覆蓋現有的 PNG 檔案）')
    parser.add_argument('--threads', '--mt', type=int, default=1, dest='threads',
                       help='🧵 多緒轉換：指定同時執行的轉換數量（預設：1）')
    parser.add_argument('--stats', action='store_true',
                       help='📊 顯示轉換統計資訊')
    parser.add_argument('--version', action='version', version='%(prog)s 1.0.0',
                       help='顯示版本資訊')

    args = parser.parse_args()

    # Check if output is required (not needed for list-pdfs or stats)
    if not args.list_pdfs and not args.stats and not args.output:
        parser.error("the following arguments are required: --output/-o")

    # Create converter (skip if only listing PDFs)
    if not args.list_pdfs and not args.stats:
        converter = PDFToPNGConverter(
            output_dir=args.output,
            dpi=args.dpi
        )
    else:
        # For list-pdfs and stats, create with dummy output dir
        converter = PDFToPNGConverter(
            output_dir=args.output or "/tmp",
            dpi=args.dpi
        )

    try:
        # Handle different modes
        if args.list_pdfs:
            input_dir = Path(args.list_pdfs)
            if not input_dir.exists():
                print(f"Error: Directory {input_dir} does not exist")
                sys.exit(1)
            converter.list_pdfs(input_dir)

        elif args.stats:
            stats = converter.get_conversion_stats()
            print("📊 Conversion Statistics:")
            print(f"   Total PDFs converted: {stats['total_pdfs']}")
            print(f"   Total images generated: {stats['total_images']}")
            print(f"   Total PDF pages: {stats['total_pages']}")

        elif args.file:
            # Handle file patterns (including wildcards)
            file_pattern = args.file

            # Check if it's a simple single file (no wildcards)
            if not any(char in file_pattern for char in ['*', '?', '[', '{']):
                # Simple single file case
                pdf_path = Path(file_pattern)
                if not pdf_path.exists():
                    print(f"Error: File {pdf_path} does not exist")
                    sys.exit(1)
                if not pdf_path.suffix.lower() == '.pdf':
                    print(f"Error: File {pdf_path} is not a PDF")
                    sys.exit(1)

                success, images = converter.convert_pdf_to_png(pdf_path, force=args.force)
                if success:
                    print(f"✅ Successfully converted {pdf_path.name} to {len(images)} images")
                else:
                    print(f"❌ Failed to convert {pdf_path.name}")
                    sys.exit(1)
            else:
                # Pattern matching case (wildcards)
                results = converter.convert_files_by_pattern(
                    file_pattern,
                    force=args.force,
                    threads=args.threads
                )
                if not results:
                    print(f"❌ No files found matching pattern: {file_pattern}")
                    sys.exit(1)

                failed_pdfs = [name for name, success in results.items() if not success]
                if failed_pdfs:
                    print(f"\n❌ Failed conversions: {', '.join(failed_pdfs)}")
                    sys.exit(1)
                else:
                    print(f"\n✅ All PDFs converted successfully!")

        elif args.dir or args.input:
            # Use --dir if provided, otherwise fall back to --input (legacy)
            input_dir_str = args.dir or args.input
            input_dir = Path(input_dir_str)

            if not input_dir.exists():
                print(f"Error: Directory {input_dir} does not exist")
                sys.exit(1)
            if not input_dir.is_dir():
                print(f"Error: {input_dir} is not a directory")
                sys.exit(1)

            results = converter.convert_directory(
                input_dir,
                force=args.force,
                threads=args.threads
            )
            failed_pdfs = [name for name, success in results.items() if not success]

            if failed_pdfs:
                print(f"\n❌ Failed conversions: {', '.join(failed_pdfs)}")
                sys.exit(1)
            else:
                print(f"\n✅ All PDFs converted successfully!")

        else:
            parser.print_help()
            sys.exit(1)
    except ConversionAborted:
        if not converter.has_announced_abort():
            print("\n🛑 Conversion aborted by user (q).")
        sys.exit(0)


if __name__ == "__main__":
    main()
