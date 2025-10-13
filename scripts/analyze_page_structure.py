#!/usr/bin/env python3
"""
Analyze SKILL manual page structure to identify patterns for rule-based detection
"""
import os
import sys
from PIL import Image
from google import genai

# Configuration
GEMINI_MODEL = "gemini-2.5-flash-lite"
API_KEY = os.getenv("GEMINI_API_KEY")
BASE_URL = os.getenv("GOOGLE_GEMINI_BASE_URL")

def analyze_page_structure(image_path: str) -> dict:
    """
    Extract structural information from a page to identify patterns
    """
    if BASE_URL:
        client = genai.Client(api_key=API_KEY, http_options={'base_url': BASE_URL})
    else:
        client = genai.Client(api_key=API_KEY)

    image = Image.open(image_path)

    prompt = """
Analyze this SKILL documentation page and extract STRUCTURAL information only.

Return a JSON object with these fields:

{
  "has_function_heading": true/false,  // Does this page have a FUNCTION NAME as a heading? (e.g., "append", "car", "cdr")
  "function_name": "name or null",     // Extract the function name if present
  "has_syntax_section": true/false,    // Does it have a "Syntax" section?
  "has_arguments_section": true/false, // Does it have an "Arguments" section?
  "has_examples_section": true/false,  // Does it have an "Examples" section?
  "has_notes_section": true/false,     // Does it have "Notes" or "Important" section?
  "has_return_section": true/false,    // Does it have "Value Returned" or "Returns" section?
  "has_function_list": true/false,     // Does it show a list of multiple functions?
  "first_heading_text": "text or null", // The first major heading on the page
  "page_number": integer or null       // Page number if visible
}

Focus on STRUCTURE detection, not content interpretation.
Return ONLY the JSON object.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[prompt, image]
    )

    # Clean and parse response
    text = response.text.strip()
    if text.startswith('```json'):
        text = text[7:]
    elif text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]

    import json
    return json.loads(text.strip())


def main():
    """Test pages: 032-033, 202-204"""
    test_pages = [
        "docs/cadence_manual/images/sklangref/sklangref-032.png",
        "docs/cadence_manual/images/sklangref/sklangref-033.png",
        "docs/cadence_manual/images/sklangref/sklangref-202.png",
        "docs/cadence_manual/images/sklangref/sklangref-203.png",
        "docs/cadence_manual/images/sklangref/sklangref-204.png",
    ]

    print("=" * 80)
    print("SKILL Manual Page Structure Analysis")
    print("=" * 80)

    results = []

    for page_path in test_pages:
        page_name = os.path.basename(page_path)

        if not os.path.exists(page_path):
            print(f"\n⚠️  {page_name}: NOT FOUND")
            continue

        print(f"\n📄 Analyzing: {page_name}")

        try:
            structure = analyze_page_structure(page_path)
            results.append({
                "page": page_name,
                "structure": structure
            })

            # Display results
            print(f"  Function Heading:  {'✅' if structure['has_function_heading'] else '❌'}")
            if structure['function_name']:
                print(f"    → Function Name: {structure['function_name']}")
            print(f"  First Heading:     {structure.get('first_heading_text', 'N/A')}")
            print(f"  Syntax Section:    {'✅' if structure['has_syntax_section'] else '❌'}")
            print(f"  Arguments Section: {'✅' if structure['has_arguments_section'] else '❌'}")
            print(f"  Examples Section:  {'✅' if structure['has_examples_section'] else '❌'}")
            print(f"  Notes Section:     {'✅' if structure['has_notes_section'] else '❌'}")
            print(f"  Return Section:    {'✅' if structure['has_return_section'] else '❌'}")
            print(f"  Function List:     {'✅' if structure['has_function_list'] else '❌'}")

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print("\n" + "=" * 80)
    print("PATTERN ANALYSIS")
    print("=" * 80)

    # Analyze patterns
    print("\n🔍 Detecting Patterns:")
    print("\nRule-based detection logic:")
    print("1. NEW FUNCTION PAGE:")
    print("   - has_function_heading = true")
    print("   - has_syntax_section = true")
    print("   - first_heading_text = function name")
    print("\n2. CONTINUATION PAGE:")
    print("   - has_function_heading = false")
    print("   - has_syntax_section = false")
    print("   - has_examples_section = true OR has_notes_section = true")
    print("\n3. CATEGORY PAGE:")
    print("   - has_function_list = true")
    print("   - has_syntax_section = false")

    # Print summary table
    print("\n" + "=" * 80)
    print("SUMMARY TABLE")
    print("=" * 80)
    print(f"{'Page':<20} {'Func Head':<12} {'Syntax':<10} {'Examples':<10} {'→ Type':<20}")
    print("-" * 80)

    for result in results:
        page = result['page']
        s = result['structure']

        # Apply rules
        if s['has_function_heading'] and s['has_syntax_section']:
            page_type = "NEW FUNCTION"
        elif not s['has_function_heading'] and not s['has_syntax_section'] and (s['has_examples_section'] or s['has_notes_section']):
            page_type = "CONTINUATION"
        elif s['has_function_list']:
            page_type = "CATEGORY"
        else:
            page_type = "OTHER"

        print(f"{page:<20} {'✅' if s['has_function_heading'] else '❌':<12} {'✅' if s['has_syntax_section'] else '❌':<10} {'✅' if s['has_examples_section'] else '❌':<10} {page_type:<20}")

    print("=" * 80)


if __name__ == '__main__':
    if not API_KEY:
        print("❌ Error: GEMINI_API_KEY not set")
        sys.exit(1)

    main()
