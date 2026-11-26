#!/usr/bin/env python3
"""
SKILL Completion Format Converter

Converts the skill.completion.json functions array from nested array format
to simplified object format for better readability and maintainability.

Conversion Rules:
1. description: Flatten nested arrays, join inner arrays with space
2. arguments: Convert from array of objects to object (argument -> key)
3. return: Convert from array of objects to object (result -> key)
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Union


def convert_description(description: List[Any]) -> List[str]:
    """
    Convert nested description arrays to flat string array.

    Input:  [ [str1, str2], [str3], [str4, str5] ]
    Output: [ "str1 str2", "str3", "str4 str5" ]
    """
    result = []
    for item in description:
        if isinstance(item, list):
            # Join array elements with space
            result.append(" ".join(item))
        elif isinstance(item, str):
            # Keep string as-is
            result.append(item)
    return result


def convert_arguments(arguments: Union[List[Dict], Dict]) -> Dict[str, str]:
    """
    Convert arguments from array format to object format.

    Input:  [ {argument: "name", description: "desc"}, ... ]
    Output: { "name": "desc", ... }
    """
    if isinstance(arguments, dict):
        # Already in object format
        return arguments

    result = {}
    for arg in arguments:
        if isinstance(arg, dict) and "argument" in arg and "description" in arg:
            result[arg["argument"]] = arg["description"]
    return result


def convert_return(return_value: Union[List[Dict], Dict]) -> Dict[str, str]:
    """
    Convert return from array format to object format.

    Input:  [ {result: "name", description: "desc"} ]
    Output: { "name": "desc" }
    """
    if isinstance(return_value, dict):
        # Already in object format
        return return_value

    result = {}
    for ret in return_value:
        if isinstance(ret, dict) and "result" in ret and "description" in ret:
            result[ret["result"]] = ret["description"]
    return result


def convert_argument_combination(arg_combo: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a single argument_combination entry.
    """
    converted = {}

    if "arguments" in arg_combo:
        converted["arguments"] = convert_arguments(arg_combo["arguments"])

    if "return" in arg_combo:
        converted["return"] = convert_return(arg_combo["return"])

    return converted


def convert_function_entry(func_entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a single function entry in the functions array.
    """
    converted = {}

    # Keep name_collection as-is
    if "name_collection" in func_entry:
        converted["name_collection"] = func_entry["name_collection"]

    # Convert description
    if "description" in func_entry:
        converted["description"] = convert_description(func_entry["description"])

    # Convert argument_combination
    if "argument_combination" in func_entry:
        converted["argument_combination"] = [
            convert_argument_combination(combo)
            for combo in func_entry["argument_combination"]
        ]

    return converted


def convert_definitions(definitions: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
    """
    Convert all function definitions within a category.
    """
    converted = {}
    for category, func_list in definitions.items():
        converted[category] = [
            convert_function_entry(func) for func in func_list
        ]
    return converted


def convert_functions_array(functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert the entire functions array.
    """
    converted = []
    for func_group in functions:
        converted_group = {}

        # Keep comment as-is
        if "comment" in func_group:
            converted_group["comment"] = func_group["comment"]

        # Convert definitions
        if "definitions" in func_group:
            converted_group["definitions"] = convert_definitions(func_group["definitions"])

        converted.append(converted_group)

    return converted


def convert_skill_completion_json(input_path: Path, output_path: Path) -> None:
    """
    Convert skill.completion.json from old format to new format.
    """
    print(f"📖 Reading: {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if "functions" not in data:
        print("❌ Error: 'functions' key not found in JSON")
        sys.exit(1)

    print("🔄 Converting functions array...")
    data["functions"] = convert_functions_array(data["functions"])

    print(f"💾 Writing: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✅ Conversion completed successfully!")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"  {sys.argv[0]} <input.json> [output.json]")
        print()
        print("Examples:")
        print(f"  {sys.argv[0]} skill.completion.json")
        print(f"  {sys.argv[0]} skill.completion.json skill.completion.new.json")
        sys.exit(1)

    input_path = Path(sys.argv[1])

    if not input_path.exists():
        print(f"❌ Error: File not found: {input_path}")
        sys.exit(1)

    # Default output: add .converted before extension
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = input_path.parent / f"{input_path.stem}.converted{input_path.suffix}"

    # Backup original file
    backup_path = input_path.parent / f"{input_path.stem}.backup{input_path.suffix}"
    if not backup_path.exists():
        print(f"💾 Creating backup: {backup_path}")
        import shutil
        shutil.copy2(input_path, backup_path)

    convert_skill_completion_json(input_path, output_path)

    print()
    print(f"📄 Original file: {input_path}")
    print(f"📄 Backup file:   {backup_path}")
    print(f"📄 Output file:   {output_path}")


if __name__ == "__main__":
    main()
