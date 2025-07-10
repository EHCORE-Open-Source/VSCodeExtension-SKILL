#!/usr/bin/env python3
"""
XML-based SKILL Function Extractor
Accurately extracts function names using structured positional information from pdftohtml XML output.
Avoids inaccuracies from later filtering steps.
"""

import re
import json
import argparse
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
from pathlib import Path

@dataclass
class WordPosition:
    """Word position information from XML"""
    text: str
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    font_size: float
    page_number: int
    
    @property
    def center_x(self) -> float:
        return (self.x_min + self.x_max) / 2
    
    @property
    def center_y(self) -> float:
        return (self.y_min + self.y_max) / 2

@dataclass
class FunctionSignature:
    """Complete function signature with position info"""
    name: str
    parameters: List[str]
    return_type: str
    signature_text: str
    position: WordPosition
    confidence: float

class XMLFunctionExtractor:
    """基於 XML 位置資訊的精確 function name 萃取器"""
    
    def __init__(self):
        self.skill_function_patterns = [
            # SKILL naming patterns
            r'^[a-z]+[A-Z][a-zA-Z]*$',      # camelCase
            r'^[a-z]+$',                     # lowercase
            r'^[a-z]+[0-9]+$',              # with numbers
            r'^ipc[A-Z][a-zA-Z]*$',         # IPC functions
            r'^db[A-Z][a-zA-Z]*$',          # Database functions
            r'^car+$|^cdr+$',               # car/cdr series
            r'^c[ad]+r$',                   # complex car/cdr
            r'^setf_[a-z-]+$',              # setf helpers
            r'^make_[a-zA-Z_]+$',           # make templates
            r'^copy_[a-zA-Z_]+$',           # copy templates
            r'^vi[il]?$',                   # vi, vii, vil series
        ]
        
        self.function_indicators = [
            '(', ')', '=>', 'returns', 'Returns'
        ]
    
    def extract_from_xml(self, xml_file: str) -> List[FunctionSignature]:
        """從 XML 檔案萃取 function signatures"""
        with open(xml_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'xml')
        
        functions = []
        
        # Process each page
        for page in soup.find_all('page'):
            page_num = int(page.get('number', 1))
            words = self._extract_words_from_page(page, page_num)
            page_functions = self._extract_functions_from_words(words)
            functions.extend(page_functions)
        
        return functions
    
    def _extract_words_from_page(self, page, page_num: int) -> List[WordPosition]:
        """萃取頁面上的所有文字位置"""
        words = []
        
        for word_elem in page.find_all('word'):
            text = word_elem.get_text().strip()
            if not text:
                continue
            
            try:
                x_min = float(word_elem.get('xmin', 0))
                y_min = float(word_elem.get('ymin', 0))
                x_max = float(word_elem.get('xmax', 0))
                y_max = float(word_elem.get('ymax', 0))
                font_size = y_max - y_min
                
                word_pos = WordPosition(
                    text=text,
                    x_min=x_min,
                    y_min=y_min,
                    x_max=x_max,
                    y_max=y_max,
                    font_size=font_size,
                    page_number=page_num
                )
                words.append(word_pos)
                
            except (ValueError, TypeError):
                continue
        
        # Sort by position for sequential processing
        words.sort(key=lambda w: (w.page_number, -w.y_min, w.x_min))
        return words
    
    def _extract_functions_from_words(self, words: List[WordPosition]) -> List[FunctionSignature]:
        """基於位置資訊萃取 function signatures"""
        functions = []
        
        for i, word in enumerate(words):
            if self._is_potential_function_name(word):
                func_sig = self._parse_function_signature(words, i)
                if func_sig:
                    functions.append(func_sig)
        
        return functions
    
    def _is_potential_function_name(self, word: WordPosition) -> bool:
        """判斷是否為潛在的 function name"""
        text = word.text
        
        # Position criteria - functions typically appear at left margin
        if word.x_min > 120:  # Too far right
            return False
        
        # Font size criteria - too small likely not a function name
        if word.font_size < 10:
            return False
        
        # Pattern matching
        for pattern in self.skill_function_patterns:
            if re.match(pattern, text):
                return True
        
        # Additional checks for common SKILL functions
        if text in {'append', 'list', 'cons', 'car', 'cdr', 'length', 'reverse',
                   'strcat', 'substring', 'sprintf', 'printf', 'println',
                   'when', 'unless', 'cond', 'if', 'let', 'prog', 'return'}:
            return True
        
        return False
    
    def _parse_function_signature(self, words: List[WordPosition], start_idx: int) -> Optional[FunctionSignature]:
        """解析完整的 function signature"""
        if start_idx >= len(words):
            return None
            
        func_word = words[start_idx]
        func_name = func_word.text
        
        # Look for opening parenthesis
        paren_idx = self._find_next_token(words, start_idx + 1, '(')
        if paren_idx == -1:
            return None
        
        # Parse parameters
        params, closing_paren_idx = self._parse_parameters(words, paren_idx)
        if closing_paren_idx == -1:
            return None
        
        # Look for return type (=> pattern)
        return_type = self._parse_return_type(words, closing_paren_idx + 1)
        
        # Build signature text
        signature_parts = []
        for i in range(start_idx, min(closing_paren_idx + 3, len(words))):
            if words[i].text in ['=>', 'returns']:
                signature_parts.append(words[i].text)
                if i + 1 < len(words):
                    signature_parts.append(words[i + 1].text)
                break
            signature_parts.append(words[i].text)
        
        signature_text = ' '.join(signature_parts)
        
        # Calculate confidence based on pattern matching
        confidence = self._calculate_confidence(func_name, params, return_type, signature_text)
        
        return FunctionSignature(
            name=func_name,
            parameters=params,
            return_type=return_type,
            signature_text=signature_text,
            position=func_word,
            confidence=confidence
        )
    
    def _find_next_token(self, words: List[WordPosition], start_idx: int, token: str) -> int:
        """找到下一個指定的 token"""
        for i in range(start_idx, len(words)):
            if words[i].text == token:
                # Check if it's close enough (same line)
                if abs(words[i].y_min - words[start_idx - 1].y_min) < 20:
                    return i
        return -1
    
    def _parse_parameters(self, words: List[WordPosition], start_idx: int) -> Tuple[List[str], int]:
        """解析函數參數"""
        params = []
        paren_count = 1
        current_param = []
        
        i = start_idx + 1
        while i < len(words) and paren_count > 0:
            word = words[i]
            
            if word.text == '(':
                paren_count += 1
                current_param.append(word.text)
            elif word.text == ')':
                paren_count -= 1
                if paren_count == 0:
                    if current_param:
                        params.append(' '.join(current_param))
                    return params, i
                else:
                    current_param.append(word.text)
            elif word.text in ['[', ']', '...', '?']:
                # SKILL special parameter syntax
                current_param.append(word.text)
            else:
                # Check if starting new parameter (type prefix pattern)
                if self._is_parameter_start(word.text) and current_param:
                    params.append(' '.join(current_param))
                    current_param = [word.text]
                else:
                    current_param.append(word.text)
            
            i += 1
        
        return params, -1
    
    def _is_parameter_start(self, text: str) -> bool:
        """判斷是否為參數開始 (SKILL type prefix)"""
        type_prefixes = [
            'l_', 't_', 'n_', 'f_', 'g_', 's_', 'S_', 'o_', 'r_', 'p_', 'x_', 'u_',
            'd_', 'e_', 'b_', 'c_', 'h_', 'i_', 'k_', 'w_', 'v_', 'y_', 'z_'
        ]
        return any(text.startswith(prefix) for prefix in type_prefixes)
    
    def _parse_return_type(self, words: List[WordPosition], start_idx: int) -> str:
        """解析返回類型"""
        # Look for => or returns
        for i in range(start_idx, min(start_idx + 5, len(words))):
            if words[i].text in ['=>', 'returns']:
                if i + 1 < len(words):
                    return words[i + 1].text
        return "unknown"
    
    def _calculate_confidence(self, func_name: str, params: List[str], return_type: str, signature: str) -> float:
        """計算萃取信心度"""
        confidence = 0.0
        
        # Function name pattern match
        for pattern in self.skill_function_patterns:
            if re.match(pattern, func_name):
                confidence += 0.3
                break
        
        # Parameter structure
        if params:
            confidence += 0.2
        
        # Return type present
        if return_type and return_type != "unknown":
            confidence += 0.2
        
        # Signature completeness
        if '(' in signature and ')' in signature:
            confidence += 0.2
        
        # Common SKILL indicators
        if any(indicator in signature for indicator in self.function_indicators):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def filter_high_confidence_functions(self, functions: List[FunctionSignature], min_confidence: float = 0.7) -> List[FunctionSignature]:
        """過濾高信心度的函數"""
        return [f for f in functions if f.confidence >= min_confidence]
    
    def export_to_json(self, functions: List[FunctionSignature], output_file: str):
        """匯出到 JSON 檔案"""
        data = {
            'extraction_method': 'xml_position_based',
            'total_functions': len(functions),
            'functions': [asdict(f) for f in functions]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description='XML-based SKILL Function Extractor')
    parser.add_argument('--input', '-i', required=True, help='Input XML file from pdftohtml')
    parser.add_argument('--output', '-o', required=True, help='Output JSON file')
    parser.add_argument('--min-confidence', '-c', type=float, default=0.7, help='Minimum confidence threshold')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    extractor = XMLFunctionExtractor()
    
    if args.verbose:
        print(f"正在處理 XML 檔案: {args.input}")
    
    # Extract functions
    functions = extractor.extract_from_xml(args.input)
    
    if args.verbose:
        print(f"萃取到 {len(functions)} 個潛在函數")
    
    # Filter by confidence
    high_confidence_functions = extractor.filter_high_confidence_functions(functions, args.min_confidence)
    
    if args.verbose:
        print(f"高信心度函數 (>= {args.min_confidence}): {len(high_confidence_functions)}")
    
    # Export results
    extractor.export_to_json(high_confidence_functions, args.output)
    
    if args.verbose:
        print(f"結果已儲存到: {args.output}")
        
        # Print sample results
        print("\n前 5 個高信心度函數:")
        for i, func in enumerate(high_confidence_functions[:5]):
            print(f"  {i+1}. {func.name} ({func.confidence:.2f})")
            print(f"     {func.signature_text}")


if __name__ == "__main__":
    main()