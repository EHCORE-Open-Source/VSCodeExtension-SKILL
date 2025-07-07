#!/usr/bin/env python3
"""
Advanced SKILL Function Search Tool
Searches through the comprehensive function database and provides
detailed information for Claude Code usage.

Usage: python3 search_skill_advanced.py <function_name>
       python3 search_skill_advanced.py --category <category_name>
       python3 search_skill_advanced.py --fuzzy <partial_name>
"""

import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any
from difflib import get_close_matches

class SkillSearcher:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.database = self.load_database()
    
    def load_database(self) -> Dict[str, Any]:
        """Load the JSON function database"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Database file {self.db_path} not found")
            print("Please run extract_skill_functions.py first")
            sys.exit(1)
    
    def search_exact(self, function_name: str) -> Dict[str, Any]:
        """Search for exact function match"""
        functions = self.database.get('functions', {})
        return functions.get(function_name)
    
    def search_fuzzy(self, partial_name: str) -> List[str]:
        """Search for functions matching partial name"""
        functions = self.database.get('functions', {})
        all_names = list(functions.keys())
        
        # Direct substring matches first
        exact_matches = [name for name in all_names if partial_name.lower() in name.lower()]
        
        # Then fuzzy matches
        fuzzy_matches = get_close_matches(partial_name, all_names, n=10, cutoff=0.6)
        
        # Combine and remove duplicates while preserving order
        matches = []
        for name in exact_matches + fuzzy_matches:
            if name not in matches:
                matches.append(name)
        
        return matches[:15]  # Limit to 15 results
    
    def search_by_category(self, category: str) -> List[str]:
        """Search functions by category"""
        by_category = self.database.get('by_category', {})
        
        # Find matching categories (case insensitive)
        matching_categories = [cat for cat in by_category.keys() 
                             if category.lower() in cat.lower()]
        
        functions = []
        for cat in matching_categories:
            functions.extend(by_category[cat])
        
        return functions
    
    def format_function_info(self, func_name: str, func_data: Dict[str, Any]) -> str:
        """Format function information for display"""
        output = []
        output.append(f"# {func_name}")
        output.append("=" * (len(func_name) + 2))
        output.append("")
        
        # Basic info
        output.append(f"**Syntax:** `{func_data.get('syntax', 'N/A')}`")
        output.append("")
        
        if func_data.get('purpose'):
            output.append(f"**Purpose:** {func_data['purpose']}")
            output.append("")
        
        # Category and source
        output.append(f"**Category:** {func_data.get('category', 'Unknown')}")
        output.append(f"**Source:** {func_data.get('source_file', 'Unknown')}")
        output.append("")
        
        # Arguments
        arguments = func_data.get('arguments', {})
        if arguments:
            output.append("**Arguments:**")
            for arg_name, arg_desc in arguments.items():
                output.append(f"- `{arg_name}`: {arg_desc}")
            output.append("")
        
        # Return values
        returns = func_data.get('returns', {})
        if returns:
            output.append("**Returns:**")
            for ret_key, ret_desc in returns.items():
                output.append(f"- {ret_desc}")
            output.append("")
        
        # Examples
        examples = func_data.get('examples', [])
        if examples:
            output.append("**Examples:**")
            for i, example in enumerate(examples[:3], 1):
                output.append(f"```skill")
                output.append(example)
                output.append("```")
                if i < len(examples[:3]):
                    output.append("")
            output.append("")
        
        # Related functions
        related = func_data.get('related_functions', [])
        if related:
            output.append(f"**Related Functions:** {', '.join(related)}")
            output.append("")
        
        return "\n".join(output)
    
    def search_and_display(self, query: str, search_type: str = "exact"):
        """Main search function"""
        if search_type == "exact":
            func_data = self.search_exact(query)
            if func_data:
                print(self.format_function_info(query, func_data))
            else:
                print(f"Function '{query}' not found. Trying fuzzy search...")
                matches = self.search_fuzzy(query)
                if matches:
                    print("\nDid you mean one of these?")
                    for i, match in enumerate(matches[:10], 1):
                        print(f"{i:2d}. {match}")
                else:
                    print("No similar functions found.")
        
        elif search_type == "fuzzy":
            matches = self.search_fuzzy(query)
            if matches:
                print(f"Functions matching '{query}':")
                print("=" * 40)
                for i, match in enumerate(matches, 1):
                    func_data = self.search_exact(match)
                    purpose = func_data.get('purpose', 'No description') if func_data else 'No description'
                    # Truncate long descriptions
                    if len(purpose) > 80:
                        purpose = purpose[:77] + "..."
                    print(f"{i:2d}. {match:<25} - {purpose}")
            else:
                print(f"No functions found matching '{query}'")
        
        elif search_type == "category":
            functions = self.search_by_category(query)
            if functions:
                print(f"Functions in category containing '{query}':")
                print("=" * 50)
                for i, func_name in enumerate(functions[:20], 1):  # Limit to 20
                    func_data = self.search_exact(func_name)
                    purpose = func_data.get('purpose', 'No description') if func_data else 'No description'
                    if len(purpose) > 60:
                        purpose = purpose[:57] + "..."
                    print(f"{i:2d}. {func_name:<25} - {purpose}")
                
                if len(functions) > 20:
                    print(f"\n... and {len(functions) - 20} more functions")
            else:
                print(f"No category found containing '{query}'")
    
    def show_statistics(self):
        """Show database statistics"""
        metadata = self.database.get('metadata', {})
        categories = self.database.get('categories', {})
        
        print("SKILL Function Database Statistics")
        print("=" * 40)
        print(f"Total Functions: {metadata.get('total_functions', 0)}")
        print(f"Total Categories: {metadata.get('total_categories', 0)}")
        print(f"Source Files: {len(metadata.get('source_files', []))}")
        print("")
        
        print("Categories:")
        for category, info in categories.items():
            count = info.get('function_count', 0) if isinstance(info, dict) else 0
            print(f"  {category:<30} {count:>4} functions")
    
    def show_categories(self):
        """Show all available categories"""
        categories = self.database.get('categories', {})
        by_category = self.database.get('by_category', {})
        
        print("Available Categories")
        print("=" * 30)
        for category in sorted(categories.keys()):
            count = len(by_category.get(category, []))
            print(f"{category:<35} ({count} functions)")

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 search_skill_advanced.py <function_name>")
        print("  python3 search_skill_advanced.py --category <category_name>") 
        print("  python3 search_skill_advanced.py --fuzzy <partial_name>")
        print("  python3 search_skill_advanced.py --stats")
        print("  python3 search_skill_advanced.py --categories")
        print("")
        print("Examples:")
        print("  python3 search_skill_advanced.py createDir")
        print("  python3 search_skill_advanced.py --fuzzy create")
        print("  python3 search_skill_advanced.py --category layout")
        sys.exit(1)
    
    db_path = "/mnt/d/git/bvSkill/docs/complete-skill-functions.json"
    searcher = SkillSearcher(db_path)
    
    if sys.argv[1] == "--stats":
        searcher.show_statistics()
    elif sys.argv[1] == "--categories":
        searcher.show_categories()
    elif sys.argv[1] == "--category" and len(sys.argv) > 2:
        searcher.search_and_display(sys.argv[2], "category")
    elif sys.argv[1] == "--fuzzy" and len(sys.argv) > 2:
        searcher.search_and_display(sys.argv[2], "fuzzy")
    else:
        searcher.search_and_display(sys.argv[1], "exact")

if __name__ == "__main__":
    main()