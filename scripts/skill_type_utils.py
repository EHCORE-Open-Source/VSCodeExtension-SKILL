#!/usr/bin/env python3
"""
SKILL Type System and Parameter Classification Utilities

This module provides utilities for:
1. Extracting SKILL type prefixes from parameter names
2. Classifying parameter types (required/keyword/optional/rest)
3. Validating type prefixes against the data_types table

Usage:
    from skill_type_utils import extract_type_prefix, classify_parameter_type

    # Extract type prefix
    prefix, desc = extract_type_prefix("l_list1")  # Returns ("l", "list")

    # Classify parameter type
    param_type = classify_parameter_type("?expr l_exprList")  # Returns 1 (KEYWORD)
"""

from enum import IntEnum
from typing import Tuple, Optional
import re


class ParameterType(IntEnum):
    """Parameter type enumeration matching database schema v3.5"""
    REQUIRED = 0  # Required parameter
    KEYWORD = 1   # Keyword parameter (?keyword)
    OPTIONAL = 2  # Optional parameter ([ ])
    REST = 3      # Rest/variadic parameter (...)


# SKILL Type Prefix Mapping (from data_types table)
TYPE_PREFIX_MAP = {
    'l': 'list',           # Linked list
    'g': 'general',        # General/any type
    'n': 'number',         # Integer or float
    'x': 'integer',        # Integer
    'f': 'flonum',         # Float
    't': 'string',         # Character string
    's': 'symbol',         # Symbol
    'S': 'stringSymbol',   # String or symbol
    'o': 'userType',       # User-defined type
    'd': 'dbobject',       # Database object
    'w': 'wtype',          # Window type
    'p': 'port',           # I/O port
    'u': 'function',       # Function object
    'r': 'defstruct',      # Defstruct
    'a': 'array',          # Array
    'b': 'ddpiobj',        # DDPI object
    'e': 'environment',    # Environment
    'h': 'hashtable',      # Hash table
    'i': 'instance',       # Instance
    'k': 'package',        # Package
    'm': 'marker',         # Marker
    'v': 'vector',         # Vector
}

# Valid type prefixes (for quick lookup)
VALID_TYPE_PREFIXES = set(TYPE_PREFIX_MAP.keys())


def clean_parameter_name(param_str: str) -> str:
    """
    Clean parameter name by removing special syntax markers

    Args:
        param_str: Raw parameter string (e.g., "?expr l_exprList", "[ x_index ]")

    Returns:
        Cleaned parameter name (e.g., "l_exprList", "x_index")

    Examples:
        >>> clean_parameter_name("?expr l_exprList")
        'l_exprList'
        >>> clean_parameter_name("[ x_index ]")
        'x_index'
        >>> clean_parameter_name("... g_rest")
        'g_rest'
    """
    # Remove optional brackets
    cleaned = param_str.replace('[', '').replace(']', '')

    # Remove rest marker
    cleaned = cleaned.replace('...', '')

    # Remove parentheses
    cleaned = cleaned.replace('(', '').replace(')', '')

    # Strip whitespace
    cleaned = cleaned.strip()

    # Handle keyword parameters: "?keyword param_name" -> "param_name"
    if cleaned.startswith('?'):
        # Split by whitespace and take the last part (the actual parameter name)
        parts = cleaned.split()
        if len(parts) >= 2:
            # Return the part after ?keyword (the actual parameter name)
            cleaned = parts[-1]
        else:
            # Just remove the ? if no parameter name follows
            cleaned = cleaned[1:]

    return cleaned


def extract_type_prefix(param_name: str) -> Tuple[str, str]:
    """
    Extract SKILL type prefix from parameter name

    Args:
        param_name: Parameter name (e.g., "l_list1", "w_windowID", "?expr l_exprList")

    Returns:
        Tuple of (prefix, type_description)

    Examples:
        >>> extract_type_prefix("l_list1")
        ('l', 'list')
        >>> extract_type_prefix("w_windowID")
        ('w', 'wtype')
        >>> extract_type_prefix("?expr l_exprList")
        ('l', 'list')
        >>> extract_type_prefix("[ x_optional ]")
        ('x', 'integer')
        >>> extract_type_prefix("unknown")
        ('g', 'general')
    """
    # Step 1: Clean parameter name
    clean_name = clean_parameter_name(param_name)

    # Step 2: Extract prefix (part before '_')
    if '_' in clean_name:
        prefix = clean_name.split('_')[0]

        # Step 3: Validate against known prefixes
        if prefix in VALID_TYPE_PREFIXES:
            return (prefix, TYPE_PREFIX_MAP[prefix])

    # Step 4: Check if it's a special case without underscore
    # (e.g., "nil", "t", single-letter parameters)
    if len(clean_name) == 1 and clean_name in VALID_TYPE_PREFIXES:
        return (clean_name, TYPE_PREFIX_MAP[clean_name])

    # Step 5: Default to general type
    return ('g', 'general')


def classify_parameter_type(param_str: str) -> int:
    """
    Classify parameter type based on SKILL syntax

    Args:
        param_str: Raw parameter string from syntax

    Returns:
        ParameterType enum value (0=REQUIRED, 1=KEYWORD, 2=OPTIONAL, 3=REST)

    Examples:
        >>> classify_parameter_type("l_list1")
        0
        >>> classify_parameter_type("?expr l_exprList")
        1
        >>> classify_parameter_type("[ x_index ]")
        2
        >>> classify_parameter_type("[ ?optional g_value ]")
        2
        >>> classify_parameter_type("... g_rest")
        3
    """
    # Trim whitespace
    param_str = param_str.strip()

    # Check for rest/variadic parameter (highest priority)
    if param_str.startswith('...') or '...' in param_str:
        return ParameterType.REST

    # Check for optional parameter (has brackets)
    if param_str.startswith('[') or param_str.startswith('[ '):
        return ParameterType.OPTIONAL

    # Check for keyword parameter (starts with ?)
    if param_str.startswith('?'):
        return ParameterType.KEYWORD

    # Default to required parameter
    return ParameterType.REQUIRED


def parse_syntax_arguments(syntax_string: str) -> list[dict]:
    """
    Parse function syntax string and extract arguments with metadata

    Args:
        syntax_string: Function syntax (e.g., "append(l_list1 l_list2)")

    Returns:
        List of argument dictionaries with type and classification

    Examples:
        >>> parse_syntax_arguments("append(l_list1 l_list2)")
        [
            {
                'name': 'l_list1',
                'type_prefix': 'l',
                'type_description': 'list',
                'parameter_type': 0,
                'position': 0,
                'is_keyword': False
            },
            {
                'name': 'l_list2',
                'type_prefix': 'l',
                'type_description': 'list',
                'parameter_type': 0,
                'position': 1,
                'is_keyword': False
            }
        ]
    """
    # Extract arguments from syntax (between parentheses)
    match = re.search(r'\((.*?)\)', syntax_string)
    if not match:
        return []

    args_string = match.group(1).strip()
    if not args_string:
        return []

    # Split arguments (handling nested brackets)
    raw_args = split_arguments(args_string)

    # Process each argument
    arguments = []
    for position, arg_str in enumerate(raw_args):
        param_type = classify_parameter_type(arg_str)
        clean_name = clean_parameter_name(arg_str)
        type_prefix, type_desc = extract_type_prefix(clean_name)
        is_keyword = arg_str.strip().startswith('?')

        arguments.append({
            'name': clean_name,
            'type_prefix': type_prefix,
            'type_description': type_desc,
            'parameter_type': param_type,
            'position': position,
            'is_keyword': is_keyword,
            'default_value': None
        })

    return arguments


def split_arguments(args_string: str) -> list[str]:
    """
    Split argument string into individual arguments, handling nested brackets

    Args:
        args_string: Arguments string (e.g., "l_list1 [ x_opt1 [ x_opt2 ] ] ?key g_val")

    Returns:
        List of argument strings

    Examples:
        >>> split_arguments("l_list1 l_list2")
        ['l_list1', 'l_list2']
        >>> split_arguments("l_list1 [ x_opt ]")
        ['l_list1', '[ x_opt ]']
        >>> split_arguments("w_id ?expr l_list")
        ['w_id', '?expr l_list']
    """
    args = []
    current = []
    bracket_depth = 0
    keyword_marker = None

    tokens = args_string.split()

    for i, token in enumerate(tokens):
        # Track bracket depth
        bracket_depth += token.count('[') - token.count(']')

        # Check if this is a keyword marker
        if token.startswith('?'):
            # Save previous argument if any
            if current:
                args.append(' '.join(current))
                current = []
            keyword_marker = token

        # Check if this is the parameter name after keyword marker
        elif keyword_marker is not None:
            # This is the parameter name, combine with keyword marker
            args.append(f"{keyword_marker} {token}")
            keyword_marker = None
            continue

        # Regular token
        else:
            current.append(token)

            # End of argument when not inside brackets
            if bracket_depth == 0 and current:
                args.append(' '.join(current))
                current = []

    # Add remaining tokens
    if current:
        args.append(' '.join(current))

    # Add remaining keyword marker (malformed syntax)
    if keyword_marker:
        args.append(keyword_marker)

    return args


def parse_syntax_string(full_syntax: str) -> Tuple[str, str]:
    """
    Parse full syntax string and separate into call syntax and return syntax

    Args:
        full_syntax: Full syntax (e.g., "append(l_list1 l_list2) => l_result")

    Returns:
        Tuple of (syntax_string, return_syntax)

    Examples:
        >>> parse_syntax_string("append(l_list1 l_list2) => l_result")
        ('append(l_list1 l_list2)', 'l_result')
        >>> parse_syntax_string("append(l_list1 l_list2)")
        ('append(l_list1 l_list2)', 'g_result')
    """
    # Split by =>
    if '=>' in full_syntax:
        parts = full_syntax.split('=>')
        syntax_string = parts[0].strip()
        return_syntax = parts[1].strip() if len(parts) > 1 else 'g_result'
    else:
        # No return syntax specified, default to general
        syntax_string = full_syntax.strip()
        return_syntax = 'g_result'

    return (syntax_string, return_syntax)


def validate_type_prefix(prefix: str) -> bool:
    """
    Validate if a type prefix is valid

    Args:
        prefix: Type prefix to validate

    Returns:
        True if valid, False otherwise

    Examples:
        >>> validate_type_prefix('l')
        True
        >>> validate_type_prefix('z')
        False
    """
    return prefix in VALID_TYPE_PREFIXES


def get_type_description(prefix: str) -> Optional[str]:
    """
    Get type description for a given prefix

    Args:
        prefix: Type prefix

    Returns:
        Type description or None if invalid

    Examples:
        >>> get_type_description('l')
        'list'
        >>> get_type_description('z')
        None
    """
    return TYPE_PREFIX_MAP.get(prefix)


# Validation functions

def validate_argument(arg_dict: dict) -> list[str]:
    """
    Validate a single argument dictionary

    Args:
        arg_dict: Argument dictionary

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Check required fields
    required_fields = ['name', 'type_prefix', 'parameter_type', 'position']
    for field in required_fields:
        if field not in arg_dict:
            errors.append(f"Missing required field: {field}")

    # Validate parameter_type
    if 'parameter_type' in arg_dict:
        if arg_dict['parameter_type'] not in [0, 1, 2, 3]:
            errors.append(f"Invalid parameter_type: {arg_dict['parameter_type']}")

    # Validate type_prefix
    if 'type_prefix' in arg_dict:
        if not validate_type_prefix(arg_dict['type_prefix']):
            errors.append(f"Invalid type_prefix: {arg_dict['type_prefix']}")

    # Validate position
    if 'position' in arg_dict:
        if not isinstance(arg_dict['position'], int) or arg_dict['position'] < 0:
            errors.append(f"Invalid position: {arg_dict['position']}")

    return errors


def validate_arguments_list(arguments: list[dict]) -> list[str]:
    """
    Validate a list of arguments

    Args:
        arguments: List of argument dictionaries

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Check each argument
    for idx, arg in enumerate(arguments):
        arg_errors = validate_argument(arg)
        for err in arg_errors:
            errors.append(f"Argument {idx}: {err}")

    # Check position sequence
    positions = [arg.get('position') for arg in arguments]
    expected = list(range(len(arguments)))
    if positions != expected:
        errors.append(f"Position sequence not consecutive: {positions}, expected {expected}")

    # Check for duplicate names
    names = [arg.get('name') for arg in arguments]
    if len(names) != len(set(names)):
        duplicates = [name for name in names if names.count(name) > 1]
        errors.append(f"Duplicate argument names: {duplicates}")

    return errors


if __name__ == '__main__':
    # Test cases
    print("=== Type Prefix Extraction Tests ===")
    test_cases = [
        "l_list1",
        "w_windowID",
        "?expr l_exprList",
        "[ x_optional ]",
        "... g_rest",
        "unknown"
    ]

    for test in test_cases:
        prefix, desc = extract_type_prefix(test)
        print(f"{test:25} -> prefix='{prefix}', type='{desc}'")

    print("\n=== Parameter Type Classification Tests ===")
    param_tests = [
        "l_list1",
        "?expr l_exprList",
        "[ x_index ]",
        "[ ?optional g_value ]",
        "... g_rest"
    ]

    for test in param_tests:
        param_type = classify_parameter_type(test)
        print(f"{test:30} -> type={param_type} ({ParameterType(param_type).name})")

    print("\n=== Syntax Parsing Tests ===")
    syntax_tests = [
        "append(l_list1 l_list2)",
        "awvAppendList(w_windowID ?expr l_exprList ?index x_indexList)",
        "buildString(l_strings [ S_glueCharacters ])"
    ]

    for syntax in syntax_tests:
        print(f"\nSyntax: {syntax}")
        args = parse_syntax_arguments(syntax)
        for arg in args:
            print(f"  {arg['position']}: {arg['name']:20} "
                  f"({arg['type_prefix']}) "
                  f"param_type={arg['parameter_type']} "
                  f"keyword={arg['is_keyword']}")

    print("\n=== Syntax String Separation Tests ===")
    full_syntax_tests = [
        "append(l_list1 l_list2) => l_result",
        "awvAppendList(w_windowID ?expr l_exprList) => t/nil",
        "buildString(l_strings)"
    ]

    for syntax in full_syntax_tests:
        call, ret = parse_syntax_string(syntax)
        print(f"{syntax}")
        print(f"  Call:   {call}")
        print(f"  Return: {ret}")
