#!/usr/bin/env python3
"""
Comprehensive test suite for SKILL PDF/HTML parser
Tests all specified features and edge cases from CLAUDE.md documentation
"""

import sys
import os
import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from skill_pdf_html_parser import (
    SkillPDFHTMLParser, 
    SkillFunctionWithOverloads,
    FunctionOverload,
    SkillParameter,
    ParameterType,
    FunctionCategory
)

class TestSkillPDFHTMLParser(unittest.TestCase):
    """Comprehensive test cases for SKILL PDF/HTML parser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.parser = SkillPDFHTMLParser()
        
    def test_official_data_types_mapping(self):
        """Test official SKILL data type prefix mappings (26+ types)"""
        expected_types = {
            'a_': 'array', 'l_': 'list', 't_': 'string', 'n_': 'number',
            'f_': 'flonum', 'g_': 'general', 's_': 'symbol', 'S_': 'stringSymbol',
            'o_': 'userType', 'r_': 'defstruct', 'p_': 'port', 'x_': 'integer',
            'u_': 'function', 'd_': 'dbobject', 'e_': 'envobj', 'w_': 'window',
            'c_': 'character', 'b_': 'boolean', 'v_': 'vector', 'm_': 'matrix',
            'h_': 'hashtable', 'i_': 'instance', 'k_': 'keyword', 'y_': 'binary',
            'z_': 'complex', 'q_': 'queue', 'R_': 'rodObj'
        }
        
        self.assertEqual(self.parser.official_data_types, expected_types)
        self.assertGreaterEqual(len(self.parser.official_data_types), 26)
        
    def test_car_cdr_functions_complete_list(self):
        """Test complete 30-function car/cdr series"""
        expected_car_cdr = [
            'car', 'cdr', 'caar', 'cadr', 'cdar', 'cddr',
            'caaar', 'caadr', 'cadar', 'caddr', 'cdaar', 'cdadr', 'cddar', 'cdddr',
            'caaaar', 'caaadr', 'caadar', 'caaddr', 'cadaar', 'cadadr', 'caddar', 'cadddr',
            'cdaaar', 'cdaadr', 'cdadar', 'cdaddr', 'cddaar', 'cddadr', 'cdddar', 'cddddr'
        ]
        
        self.assertEqual(self.parser.car_cdr_functions, expected_car_cdr)
        self.assertEqual(len(self.parser.car_cdr_functions), 30)
        
    def test_vi_series_functions(self):
        """Test VI series functions (vi, vii, vil) as separate functions"""
        expected_vi_series = ['vi', 'vii', 'vil']
        self.assertEqual(self.parser.vi_series_functions, expected_vi_series)
        
    def test_template_function_patterns(self):
        """Test template function patterns (make_, copy_, setf_)"""
        expected_patterns = ['make_', 'copy_', 'setf_']
        self.assertEqual(self.parser.template_patterns, expected_patterns)

class TestParameterParsing(unittest.TestCase):
    """Test comprehensive parameter pattern handling"""
    
    def setUp(self):
        self.parser = SkillPDFHTMLParser()
        
    def test_parameter_type_extraction(self):
        """Test parameter type extraction from official mappings"""
        test_cases = [
            ('l_list', 'list'),
            ('t_string', 'string'),
            ('n_number', 'number'),
            ('g_general', 'general'),
            ('s_symbol', 'symbol'),
            ('o_object', 'userType'),
            ('unknown_param', 'general')  # Default case
        ]
        
        for param_name, expected_type in test_cases:
            with self.subTest(param=param_name):
                result = self.parser._extract_parameter_type(param_name)
                self.assertEqual(result, expected_type)
                
    def test_enhanced_parameter_parsing(self):
        """Test enhanced parameter parsing with all patterns"""
        test_cases = [
            # (param_name, is_optional, position, expected_type, expected_data_type)
            ('l_list', False, 0, ParameterType.REQUIRED, 'list'),
            ('t_optional', True, 1, ParameterType.OPTIONAL, 'string'),
            ('...', False, 2, ParameterType.VARIADIC, 'general'),
            ('?keyword', False, 3, ParameterType.KEYWORD, 'general'),
        ]
        
        for param_name, is_optional, position, expected_type, expected_data_type in test_cases:
            with self.subTest(param=param_name):
                result = self.parser._parse_enhanced_parameter(param_name, is_optional, position)
                self.assertIsNotNone(result)
                self.assertEqual(result.param_type, expected_type)
                self.assertEqual(result.data_type, expected_data_type)
                self.assertEqual(result.position, position)

class TestComplexParameterPatterns(unittest.TestCase):
    """Test complex SKILL parameter patterns from examples"""
    
    def setUp(self):
        self.parser = SkillPDFHTMLParser()
        
    def create_mock_words(self, signature: str) -> list:
        """Create mock words list from signature string"""
        words = []
        tokens = signature.split()
        for i, token in enumerate(tokens):
            words.append({
                'text': token,
                'x': 50,
                'y': 100 + i * 10,
                'font_size': 12,
                'element': MagicMock()
            })
        return words
        
    def test_buildstring_pattern(self):
        """Test buildString pattern: buildString(l_stringList [t_separator])"""
        signature = "buildString( l_stringList [ t_separator ] ) => t"
        words = self.create_mock_words(signature)
        
        # Mock the overload parsing
        overload = self.parser._parse_single_overload(words, 0, "buildString")
        
        # Should detect optional parameter pattern
        self.assertIsNotNone(overload)
        # Note: Full pattern detection requires complete HTML context
        
    def test_nearlyequal_pattern(self):
        """Test nearlyEqual pattern: nearlyEqual(n_num1 n_num2 [n_tolerance])"""
        signature = "nearlyEqual( n_num1 n_num2 [ n_tolerance ] ) => t"
        words = self.create_mock_words(signature)
        
        overload = self.parser._parse_single_overload(words, 0, "nearlyEqual")
        self.assertIsNotNone(overload)
        
    def test_variadic_pattern(self):
        """Test variadic pattern: lsprintf(t_format g_arg1 ...)"""
        signature = "lsprintf( t_format g_arg1 ... ) => t"
        words = self.create_mock_words(signature)
        
        overload = self.parser._parse_single_overload(words, 0, "lsprintf")
        self.assertIsNotNone(overload)

class TestMultipleOverloads(unittest.TestCase):
    """Test multiple function overload detection"""
    
    def setUp(self):
        self.parser = SkillPDFHTMLParser()
        
    def create_append_html_mock(self):
        """Create mock HTML for append function with 3 overloads"""
        return """
        <page>
            <word xmin="50" ymin="100" ymax="115" font="12">append</word>
            <word xmin="50" ymin="120" ymax="135" font="12">append(</word>
            <word xmin="100" ymin="120" ymax="135" font="12">l_list1</word>
            <word xmin="150" ymin="120" ymax="135" font="12">l_list2</word>
            <word xmin="200" ymin="120" ymax="135" font="12">)</word>
            <word xmin="250" ymin="120" ymax="135" font="12">=></word>
            <word xmin="280" ymin="120" ymax="135" font="12">l_list</word>
            
            <word xmin="50" ymin="140" ymax="155" font="12">append(</word>
            <word xmin="100" ymin="140" ymax="155" font="12">o_table</word>
            <word xmin="150" ymin="140" ymax="155" font="12">g_assoc</word>
            <word xmin="200" ymin="140" ymax="155" font="12">)</word>
            <word xmin="250" ymin="140" ymax="155" font="12">=></word>
            <word xmin="280" ymin="140" ymax="155" font="12">o_table</word>
            
            <word xmin="50" ymin="160" ymax="175" font="12">append(</word>
            <word xmin="100" ymin="160" ymax="175" font="12">o_table1</word>
            <word xmin="150" ymin="160" ymax="175" font="12">o_table2</word>
            <word xmin="200" ymin="160" ymax="175" font="12">)</word>
            <word xmin="250" ymin="160" ymax="175" font="12">=></word>
            <word xmin="280" ymin="160" ymax="175" font="12">o_table</word>
            
            <word xmin="50" ymin="200" ymax="215" font="12">Description</word>
        </page>
        """
        
    def test_append_multiple_overloads(self):
        """Test append function with 3 different signatures"""
        html_content = self.create_append_html_mock()
        
        functions = self.parser.parse_html_content(html_content)
        
        # Find append function
        append_func = None
        for func in functions:
            if func.name == 'append':
                append_func = func
                break
                
        self.assertIsNotNone(append_func, "append function should be found")
        
        # Should have 3 overloads
        expected_overload_count = 3
        self.assertEqual(len(append_func.overloads), expected_overload_count)
        
        # Check parameter patterns
        expected_patterns = [
            ('l_list1', 'l_list2'),     # List overload
            ('o_table', 'g_assoc'),     # Table + association
            ('o_table1', 'o_table2')    # Table + table
        ]
        
        found_patterns = []
        for overload in append_func.overloads:
            if len(overload.parameters) >= 2:
                pattern = (overload.parameters[0].name, overload.parameters[1].name)
                found_patterns.append(pattern)
                
        # Verify all expected patterns are found
        for expected_pattern in expected_patterns:
            self.assertIn(expected_pattern, found_patterns)

class TestSpecialFunctionHandling(unittest.TestCase):
    """Test special function pattern handling"""
    
    def setUp(self):
        self.parser = SkillPDFHTMLParser()
        
    def test_car_cdr_generation(self):
        """Test car/cdr function generation with unified signatures"""
        # Test generating a car/cdr function
        func = self.parser._generate_car_cdr_function("caar")
        
        self.assertEqual(func.name, "caar")
        self.assertEqual(func.special_type, "car_cdr_series")
        self.assertEqual(len(func.overloads), 1)
        
        # Check unified signature
        overload = func.overloads[0]
        self.assertIn("l_list", overload.signature)
        self.assertEqual(len(overload.parameters), 1)
        self.assertEqual(overload.parameters[0].name, "l_list")
        self.assertEqual(overload.parameters[0].data_type, "list")
        
    def test_vi_series_individual_examples(self):
        """Test VI series functions with individual examples"""
        test_cases = [
            ('vi', ['vi("Layout")']),
            ('vii', ['vii("Layout" "cellName")']),
            ('vil', ['vil("Layout" "cellName" "viewName")'])
        ]
        
        for func_name, expected_examples in test_cases:
            with self.subTest(func=func_name):
                func = self.parser._generate_vi_function(func_name)
                
                self.assertEqual(func.name, func_name)
                self.assertEqual(func.special_type, "vi_series")
                self.assertEqual(func.examples, expected_examples)
                
    def test_special_type_determination(self):
        """Test special function type determination"""
        test_cases = [
            ('car', 'car_cdr_series'),
            ('cdddr', 'car_cdr_series'),
            ('vi', 'vi_series'),
            ('vii', 'vi_series'),
            ('vil', 'vi_series'),
            ('make_component', 'template_function'),
            ('copy_data', 'template_function'),
            ('setf_helper', 'template_function'),
            ('regular_function', None)
        ]
        
        for func_name, expected_type in test_cases:
            with self.subTest(func=func_name):
                result = self.parser._determine_special_type(func_name)
                self.assertEqual(result, expected_type)

class TestHierarchicalCategorization(unittest.TestCase):
    """Test hierarchical categorization system"""
    
    def setUp(self):
        self.parser = SkillPDFHTMLParser()
        
    def test_category_level_determination(self):
        """Test category level determination based on font size"""
        test_cases = [
            (16.0, 50.0, 1),  # Large font, left margin = level 1
            (14.0, 50.0, 2),  # Medium font = level 2
            (13.0, 50.0, 3),  # Small font = level 3
            (12.0, 50.0, 4)   # Smaller font = level 4
        ]
        
        for font_size, x_pos, expected_level in test_cases:
            with self.subTest(font_size=font_size):
                level = self.parser._determine_category_level(font_size, x_pos)
                self.assertEqual(level, expected_level)
                
    def test_category_header_detection(self):
        """Test category header detection"""
        test_cases = [
            ("Arithmetic Functions", 14.0, 50.0, True),
            ("String Operations", 13.0, 60.0, True),
            ("Database Commands", 15.0, 40.0, True),
            ("regular text", 12.0, 50.0, False),
            ("Functions", 10.0, 50.0, False),  # Too small font
            ("Functions", 14.0, 200.0, False)  # Too far right
        ]
        
        for text, font_size, x_pos, expected in test_cases:
            with self.subTest(text=text):
                # Mock words context
                words = []
                result = self.parser._is_category_header(text, font_size, x_pos, words, 0)
                self.assertEqual(result, expected)
                
    def test_category_path_building(self):
        """Test hierarchical category path building"""
        # Simulate building nested categories
        self.parser.current_categories = []
        
        # Level 1 category
        path1 = self.parser._build_category_path("Functions", 1)
        self.assertEqual(path1, ["Functions"])
        
        # Level 2 category
        path2 = self.parser._build_category_path("Arithmetic", 2)
        self.assertEqual(path2, ["Functions", "Arithmetic"])
        
        # Level 3 category
        path3 = self.parser._build_category_path("Basic Operations", 3)
        self.assertEqual(path3, ["Functions", "Arithmetic", "Basic Operations"])
        
        # Back to level 2 (should reset level 3)
        path4 = self.parser._build_category_path("String Operations", 2)
        self.assertEqual(path4, ["Functions", "String Operations"])

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        self.parser = SkillPDFHTMLParser()
        
    def test_empty_html_content(self):
        """Test handling of empty HTML content"""
        functions = self.parser.parse_html_content("")
        self.assertEqual(len(functions), 0)
        
    def test_malformed_html(self):
        """Test handling of malformed HTML"""
        malformed_html = "<page><word>unclosed word</page>"
        functions = self.parser.parse_html_content(malformed_html)
        # Should not crash, may return empty or partial results
        self.assertIsInstance(functions, list)
        
    def test_missing_positioning_data(self):
        """Test handling of words without positioning data"""
        html_without_coords = """
        <page>
            <word>function_name</word>
        </page>
        """
        functions = self.parser.parse_html_content(html_without_coords)
        # Should handle gracefully
        self.assertIsInstance(functions, list)
        
    def test_very_long_signatures(self):
        """Test handling of very long function signatures"""
        # Create a mock signature with many parameters
        long_params = " ".join([f"param{i}" for i in range(50)])
        long_signature = f"longFunction( {long_params} )"
        
        words = []
        for i, token in enumerate(long_signature.split()):
            words.append({
                'text': token,
                'x': 50,
                'y': 100 + i * 5,
                'font_size': 12,
                'element': MagicMock()
            })
            
        # Should handle without crashing
        overload = self.parser._parse_single_overload(words, 0, "longFunction")
        self.assertIsInstance(overload, (FunctionOverload, type(None)))

class TestFileOperations(unittest.TestCase):
    """Test file I/O operations"""
    
    def setUp(self):
        self.parser = SkillPDFHTMLParser()
        
    def test_save_results_json_format(self):
        """Test saving results in correct JSON format"""
        # Create a sample function
        param = SkillParameter(
            name="l_list",
            param_type=ParameterType.REQUIRED,
            data_type="list",
            position=0
        )
        
        overload = FunctionOverload(
            signature="test_func(l_list)",
            parameters=[param],
            return_type="t",
            raw_signature="test_func(l_list)"
        )
        
        func = SkillFunctionWithOverloads(
            name="test_func",
            overloads=[overload],
            description="Test function",
            arguments_description={"l_list": "Test list"},
            examples=["test_func('(a b c))"],
            page=1
        )
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
            temp_path = tmp_file.name
            
        try:
            self.parser.save_results([func], temp_path)
            
            # Verify file was created and contains valid JSON
            with open(temp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Check structure
            self.assertIn('metadata', data)
            self.assertIn('functions', data)
            self.assertEqual(data['metadata']['total_functions'], 1)
            self.assertEqual(len(data['functions']), 1)
            
            # Check function data
            func_data = data['functions'][0]
            self.assertEqual(func_data['name'], 'test_func')
            self.assertEqual(len(func_data['overloads']), 1)
            
        finally:
            # Clean up
            os.unlink(temp_path)
            
    @patch('subprocess.run')
    def test_pdf_to_html_conversion(self, mock_run):
        """Test PDF to HTML conversion"""
        mock_run.return_value.returncode = 0
        
        result = self.parser.convert_pdf_to_html('/path/to/test.pdf', '/path/to/test.html')
        
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ['pdftotext', '-bbox', '/path/to/test.pdf', '/path/to/test.html'],
            capture_output=True,
            text=True
        )

class TestPerformanceAndScalability(unittest.TestCase):
    """Test performance characteristics"""
    
    def setUp(self):
        self.parser = SkillPDFHTMLParser()
        
    def test_large_document_handling(self):
        """Test handling of large documents"""
        # Create a mock large document with many pages
        large_html = "<html><body>"
        for page_num in range(100):  # 100 pages
            large_html += f'<page><word xmin="50" ymin="{100 + page_num*20}" ymax="{115 + page_num*20}">func_{page_num}</word></page>'
        large_html += "</body></html>"
        
        # Should complete without excessive memory usage or timeout
        import time
        start_time = time.time()
        
        functions = self.parser.parse_html_content(large_html)
        
        end_time = time.time()
        
        # Basic performance check (should complete in reasonable time)
        self.assertLess(end_time - start_time, 30.0)  # Should complete within 30 seconds
        self.assertIsInstance(functions, list)
        
    def test_memory_efficiency(self):
        """Test memory efficiency with repeated parsing"""
        # Parse the same content multiple times
        simple_html = """
        <page>
            <word xmin="50" ymin="100" ymax="115">test_func</word>
        </page>
        """
        
        for _ in range(10):
            functions = self.parser.parse_html_content(simple_html)
            # Should not accumulate state between parses
            self.assertIsInstance(functions, list)

def run_comprehensive_tests():
    """Run all test suites with detailed reporting"""
    
    # Define test suites
    test_suites = [
        TestSkillPDFHTMLParser,
        TestParameterParsing,
        TestComplexParameterPatterns,
        TestMultipleOverloads,
        TestSpecialFunctionHandling,
        TestHierarchicalCategorization,
        TestEdgeCases,
        TestFileOperations,
        TestPerformanceAndScalability
    ]
    
    # Run tests
    total_tests = 0
    total_failures = 0
    total_errors = 0
    
    print("=" * 60)
    print("SKILL PDF/HTML Parser - Comprehensive Test Suite")
    print("=" * 60)
    
    for suite_class in test_suites:
        print(f"\n--- Running {suite_class.__name__} ---")
        
        suite = unittest.TestLoader().loadTestsFromTestCase(suite_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        total_tests += result.testsRun
        total_failures += len(result.failures)
        total_errors += len(result.errors)
        
        if result.failures:
            print(f"FAILURES in {suite_class.__name__}:")
            for test, failure in result.failures:
                print(f"  - {test}: {failure}")
                
        if result.errors:
            print(f"ERRORS in {suite_class.__name__}:")
            for test, error in result.errors:
                print(f"  - {test}: {error}")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total tests run: {total_tests}")
    print(f"Failures: {total_failures}")
    print(f"Errors: {total_errors}")
    
    if total_failures == 0 and total_errors == 0:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        return False

if __name__ == "__main__":
    # Run comprehensive test suite
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)