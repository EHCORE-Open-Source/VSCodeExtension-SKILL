#!/usr/bin/env python3
"""
Streamlit JSON Review & Validation UI

Purpose: Review and validate JSON files extracted by Gemini before database import
Input: JSON files from gemini_manual_image_converter.py
Output: Validated JSON files ready for database import

Usage:
    streamlit run scripts/streamlit_json_reviewer.py

Author: Claude Code
Version: 1.0
Date: 2025-10-11
"""

import streamlit as st
import json
import os
from pathlib import Path
import pandas as pd
from PIL import Image
from typing import Dict, List, Optional
from datetime import datetime

# Configuration
st.set_page_config(
    page_title="SKILL JSON Reviewer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
VALID_TYPE_PREFIXES = ['l', 'g', 'n', 'x', 'f', 't', 's', 'S', 'o', 'd', 'w', 'p', 'u', 'r', 'a']
PARAMETER_TYPES = {
    0: "Required",
    1: "Keyword",
    2: "Optional",
    3: "Rest"
}

# Initialize session state
if 'current_file' not in st.session_state:
    st.session_state.current_file = None
if 'current_function_idx' not in st.session_state:
    st.session_state.current_function_idx = 0
if 'json_data' not in st.session_state:
    st.session_state.json_data = None
if 'modified' not in st.session_state:
    st.session_state.modified = False
if 'json_dir' not in st.session_state:
    st.session_state.json_dir = "test_output/"
if 'image_dir' not in st.session_state:
    st.session_state.image_dir = "docs/cadence_manual/images/"


def load_json_file(json_path: str):
    """Load JSON file and store in session state"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            st.session_state.json_data = json.load(f)
        st.session_state.current_file = json_path
        st.session_state.current_function_idx = 0
        st.session_state.modified = False
        return True
    except Exception as e:
        st.error(f"❌ Failed to load JSON: {e}")
        return False


def save_json_file(json_data: dict, json_path: str):
    """Save modified JSON file"""
    try:
        # Create backup
        backup_path = json_path + ".backup"
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                backup_data = f.read()
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(backup_data)

        # Save new data
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)

        st.session_state.modified = False
        return True
    except Exception as e:
        st.error(f"❌ Failed to save JSON: {e}")
        return False


def validate_json_schema(json_data: dict) -> Dict:
    """Validate JSON against schema"""
    errors = []
    warnings = []

    # Check required top-level fields
    if 'manual_metadata' not in json_data:
        errors.append("Missing 'manual_metadata' field")
    if 'functions' not in json_data:
        errors.append("Missing 'functions' field")

    if errors:
        return {'valid': False, 'errors': errors, 'warnings': warnings}

    # Validate manual_metadata
    metadata = json_data.get('manual_metadata', {})
    required_meta_fields = ['manual_code', 'product_code', 'version', 'document_title']
    for field in required_meta_fields:
        if field not in metadata:
            errors.append(f"Missing manual_metadata.{field}")

    # Validate functions
    functions = json_data.get('functions', [])
    for idx, func in enumerate(functions):
        func_name = func.get('function_name', f'function[{idx}]')

        # Check required function fields
        if 'function_name' not in func:
            errors.append(f"Function {idx}: Missing 'function_name'")
        if 'primary_syntax' not in func:
            errors.append(f"{func_name}: Missing 'primary_syntax'")
        elif 'syntax_string' not in func['primary_syntax']:
            errors.append(f"{func_name}: Missing 'primary_syntax.syntax_string'")

        # Check type prefixes
        if 'primary_syntax' in func:
            for arg in func['primary_syntax'].get('arguments', []):
                if arg['type_prefix'] not in VALID_TYPE_PREFIXES:
                    warnings.append(f"{func_name}: Invalid type prefix '{arg['type_prefix']}' in argument '{arg['name']}'")

        # Check parameter types
        if 'primary_syntax' in func:
            for arg in func['primary_syntax'].get('arguments', []):
                if arg['parameter_type'] not in [0, 1, 2, 3]:
                    warnings.append(f"{func_name}: Invalid parameter_type {arg['parameter_type']} in argument '{arg['name']}'")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


def get_quality_issues(json_data: dict) -> List[Dict]:
    """Check for data quality issues"""
    issues = []
    functions = json_data.get('functions', [])

    for func in functions:
        func_name = func.get('function_name', 'unknown')

        # Missing or short description
        if not func.get('description') or len(func.get('description', '')) < 10:
            issues.append({
                'Function': func_name,
                'Issue': 'Missing or short description',
                'Severity': '⚠️ Warning',
                'Field': 'description'
            })

        # Low confidence
        confidence = func.get('metadata', {}).get('extraction_confidence', 0)
        if confidence < 0.7:
            issues.append({
                'Function': func_name,
                'Issue': f'Low confidence: {confidence:.2f}',
                'Severity': '⚠️ Warning',
                'Field': 'metadata.extraction_confidence'
            })

        # No examples
        if not func.get('examples') or len(func.get('examples', [])) == 0:
            issues.append({
                'Function': func_name,
                'Issue': 'No examples provided',
                'Severity': 'ℹ️ Info',
                'Field': 'examples'
            })

        # Invalid type prefix
        for arg in func.get('primary_syntax', {}).get('arguments', []):
            if arg['type_prefix'] not in VALID_TYPE_PREFIXES:
                issues.append({
                    'Function': func_name,
                    'Issue': f"Invalid type prefix: {arg['type_prefix']} in argument {arg['name']}",
                    'Severity': '❌ Error',
                    'Field': f"primary_syntax.arguments[{arg['position']}].type_prefix"
                })

    return issues


def render_sidebar():
    """Render sidebar with navigation and statistics"""
    st.sidebar.title("📚 JSON Review System")

    # Directory settings
    st.session_state.json_dir = st.sidebar.text_input(
        "JSON Directory",
        value=st.session_state.json_dir,
        help="Directory containing JSON files to review"
    )

    st.session_state.image_dir = st.sidebar.text_input(
        "Image Directory",
        value=st.session_state.image_dir,
        help="Directory containing source PNG images"
    )

    # File selector
    if os.path.exists(st.session_state.json_dir):
        json_files = sorted([f for f in os.listdir(st.session_state.json_dir) if f.endswith('.json')])

        if json_files:
            selected_file = st.sidebar.selectbox(
                "Select JSON File",
                json_files,
                help="Choose a JSON file to review"
            )

            json_path = os.path.join(st.session_state.json_dir, selected_file)

            if json_path != st.session_state.current_file:
                if st.session_state.modified:
                    st.sidebar.warning("⚠️ Unsaved changes will be lost!")
                    if st.sidebar.button("Load anyway"):
                        load_json_file(json_path)
                else:
                    load_json_file(json_path)
        else:
            st.sidebar.warning("⚠️ No JSON files found in directory")
    else:
        st.sidebar.error(f"❌ Directory not found: {st.session_state.json_dir}")

    # Statistics
    if st.session_state.json_data:
        st.sidebar.divider()
        json_data = st.session_state.json_data
        functions = json_data.get('functions', [])

        total_functions = len(functions)
        needs_review_count = sum(1 for f in functions if f.get('metadata', {}).get('needs_review', False))
        verified_count = sum(1 for f in functions if f.get('metadata', {}).get('verified', False))
        avg_confidence = sum(f.get('metadata', {}).get('extraction_confidence', 0) for f in functions) / max(total_functions, 1)

        st.sidebar.metric("Total Functions", total_functions)
        st.sidebar.metric("Verified", verified_count)
        st.sidebar.metric("Needs Review", needs_review_count, delta_color="inverse")
        st.sidebar.metric("Avg Confidence", f"{avg_confidence:.2f}")

        # Modified indicator
        if st.session_state.modified:
            st.sidebar.warning("⚠️ Unsaved changes")

        # Save button
        if st.sidebar.button("💾 Save Changes", type="primary", disabled=not st.session_state.modified):
            if save_json_file(st.session_state.json_data, st.session_state.current_file):
                st.sidebar.success("✅ Saved successfully!")
                st.rerun()


def render_overview_tab(json_data: dict):
    """Render overview tab"""
    st.title("📊 JSON Overview")

    metadata = json_data.get('manual_metadata', {})
    functions = json_data.get('functions', [])

    # Manual metadata
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Manual Code", metadata.get('manual_code', 'N/A'))
    with col2:
        st.metric("Product", metadata.get('product_code', 'N/A'))
    with col3:
        st.metric("Version", metadata.get('version', 'N/A'))
    with col4:
        st.metric("Total Functions", len(functions))

    st.info(f"📖 {metadata.get('document_title', 'N/A')}")

    # Function list
    st.divider()
    st.subheader("Functions")

    # Filters
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        category_filter = st.multiselect(
            "Filter by Category",
            options=list(set(f.get('category', 'Uncategorized') for f in functions))
        )
    with col_filter2:
        min_confidence = st.slider("Min Confidence", 0.0, 1.0, 0.0, 0.1)
    with col_filter3:
        show_only_review = st.checkbox("Only show items needing review")

    # Apply filters
    filtered_functions = functions
    if category_filter:
        filtered_functions = [f for f in filtered_functions if f.get('category') in category_filter]
    if min_confidence > 0:
        filtered_functions = [f for f in filtered_functions if f.get('metadata', {}).get('extraction_confidence', 0) >= min_confidence]
    if show_only_review:
        filtered_functions = [f for f in filtered_functions if f.get('metadata', {}).get('needs_review', False)]

    # Create dataframe
    df = pd.DataFrame([{
        'Function': f['function_name'],
        'Category': f.get('category', 'Uncategorized'),
        'Overloads': len(f.get('overloads', [])),
        'Examples': len(f.get('examples', [])),
        'Confidence': f'{f.get("metadata", {}).get("extraction_confidence", 0):.2f}',
        'Status': '⚠️ Review' if f.get('metadata', {}).get('needs_review') else ('✅ Verified' if f.get('metadata', {}).get('verified') else '⏳ Pending'),
        'Pages': f"{f.get('sources', {}).get('start_page', '?')}-{f.get('sources', {}).get('end_page', '?')}"
    } for f in filtered_functions])

    if not df.empty:
        # Display dataframe with selection
        event = st.dataframe(
            df,
            use_container_width=True,
            height=400,
            on_select="rerun",
            selection_mode="single-row"
        )

        # Handle row selection
        if event.selection and 'rows' in event.selection and len(event.selection['rows']) > 0:
            selected_idx = event.selection['rows'][0]
            # Find the actual index in the original functions list
            selected_func_name = filtered_functions[selected_idx]['function_name']
            for idx, func in enumerate(functions):
                if func['function_name'] == selected_func_name:
                    st.session_state.current_function_idx = idx
                    break
    else:
        st.info("No functions match the current filters")


def render_function_details_tab(json_data: dict, image_dir: str):
    """Render function details tab with editing capabilities"""
    st.title("🔍 Function Details")

    functions = json_data.get('functions', [])

    if not functions:
        st.warning("No functions found in JSON file")
        return

    # Function navigation
    col_nav1, col_nav2, col_nav3 = st.columns([1, 3, 1])
    with col_nav1:
        if st.button("⬅️ Previous", disabled=st.session_state.current_function_idx == 0):
            st.session_state.current_function_idx = max(0, st.session_state.current_function_idx - 1)
            st.rerun()
    with col_nav2:
        st.markdown(f"### Function {st.session_state.current_function_idx + 1} of {len(functions)}")
    with col_nav3:
        if st.button("Next ➡️", disabled=st.session_state.current_function_idx >= len(functions) - 1):
            st.session_state.current_function_idx = min(len(functions) - 1, st.session_state.current_function_idx + 1)
            st.rerun()

    func = functions[st.session_state.current_function_idx]

    # Two-column layout
    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader("📝 Function Data")

        # Basic info
        st.text_input("Function Name", value=func['function_name'], disabled=True)
        st.text_input("Category", value=func.get('category', 'Uncategorized'), disabled=True)

        # Primary syntax
        st.markdown("### Primary Syntax")
        st.code(func['primary_syntax']['syntax_string'], language="scheme")
        st.code(f"=> {func['primary_syntax']['return_syntax']}", language="scheme")

        # Description
        st.markdown("### Description")
        st.text_area(
            "Description",
            value=func.get('description', ''),
            height=150,
            label_visibility="collapsed",
            disabled=True
        )

        # Arguments
        st.markdown("### Arguments")
        if func['primary_syntax'].get('arguments'):
            args_df = pd.DataFrame(func['primary_syntax']['arguments'])
            st.dataframe(
                args_df[['name', 'type_prefix', 'type_description', 'parameter_type', 'description']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No arguments")

        # Return values
        st.markdown("### Return Values")
        if func['primary_syntax'].get('return_values'):
            ret_df = pd.DataFrame(func['primary_syntax']['return_values'])
            st.dataframe(
                ret_df[['type_name', 'type_prefix', 'type_description', 'description']],
                use_container_width=True,
                hide_index=True
            )

        # Overloads
        st.markdown("### Overloads")
        if func.get('overloads'):
            for idx, overload in enumerate(func['overloads']):
                with st.expander(f"Overload {idx + 1}: {overload['syntax_string']}"):
                    st.code(overload['syntax_string'], language="scheme")
                    st.code(f"=> {overload['return_syntax']}", language="scheme")
                    if overload.get('description'):
                        st.markdown(f"**Description:** {overload['description']}")
        else:
            st.info("No overloads")

        # Examples
        st.markdown("### Examples")
        if func.get('examples'):
            for idx, example in enumerate(func['examples']):
                with st.expander(f"Example {idx + 1}"):
                    st.code(example.get('code', ''), language="scheme")
                    if example.get('description'):
                        st.markdown(f"**Description:** {example['description']}")
        else:
            st.info("No examples")

    with col2:
        st.subheader("🖼️ Source Images")

        # Get manual code for image path
        manual_code = json_data.get('manual_metadata', {}).get('manual_code', '')
        full_image_dir = os.path.join(image_dir, manual_code)

        # Show source images
        for img_name in func.get('sources', {}).get('source_images', []):
            img_path = os.path.join(full_image_dir, img_name)
            if os.path.exists(img_path):
                try:
                    img = Image.open(img_path)
                    st.image(img, caption=img_name, use_column_width=True)
                except Exception as e:
                    st.error(f"❌ Failed to load image: {e}")
            else:
                st.warning(f"⚠️ Image not found: {img_name}")
                st.text(f"Expected path: {img_path}")

        st.divider()

        # Metadata
        st.markdown("### Metadata")
        metadata = func.get('metadata', {})

        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            verified = metadata.get('verified', False)
            st.markdown(f"**Verified:** {'✅ Yes' if verified else '❌ No'}")
        with col_meta2:
            needs_review = metadata.get('needs_review', False)
            st.markdown(f"**Needs Review:** {'⚠️ Yes' if needs_review else '✅ No'}")

        confidence = metadata.get('extraction_confidence', 0)
        st.metric("Extraction Confidence", f"{confidence:.2f}")

        # Source info
        st.divider()
        st.markdown("### Source Information")
        sources = func.get('sources', {})
        st.text(f"File: {sources.get('source_file', 'N/A')}")
        st.text(f"Pages: {sources.get('start_page', '?')}-{sources.get('end_page', '?')}")

        # Action buttons
        st.divider()
        st.markdown("### Actions")

        if st.button("✅ Mark as Verified", use_container_width=True):
            func['metadata']['verified'] = True
            func['metadata']['needs_review'] = False
            st.session_state.modified = True
            st.success("✅ Marked as verified!")
            st.rerun()

        if st.button("⚠️ Flag for Review", use_container_width=True):
            func['metadata']['needs_review'] = True
            func['metadata']['verified'] = False
            st.session_state.modified = True
            st.warning("⚠️ Flagged for review!")
            st.rerun()


def render_validation_tab(json_data: dict):
    """Render validation report tab"""
    st.title("✅ Validation Report")

    # Schema compliance check
    st.subheader("Schema Compliance")
    validation_result = validate_json_schema(json_data)

    if validation_result['valid']:
        st.success("✅ JSON schema is valid")
    else:
        st.error("❌ Schema validation failed")
        for error in validation_result['errors']:
            st.error(f"- {error}")

    if validation_result['warnings']:
        st.warning(f"⚠️ {len(validation_result['warnings'])} warnings found")
        with st.expander("Show warnings"):
            for warning in validation_result['warnings']:
                st.warning(f"- {warning}")

    # Data quality checks
    st.divider()
    st.subheader("Data Quality Issues")

    issues = get_quality_issues(json_data)

    if issues:
        issues_df = pd.DataFrame(issues)
        st.dataframe(issues_df, use_container_width=True, hide_index=True)
        st.warning(f"⚠️ Found {len(issues)} quality issues")
    else:
        st.success("✅ No quality issues found!")


def render_batch_operations_tab(json_data: dict):
    """Render batch operations tab"""
    st.title("⚡ Batch Operations")

    st.info("Quickly process multiple functions at once")

    functions = json_data.get('functions', [])

    # Batch verification
    st.subheader("Batch Verification")
    verification_confidence = st.slider(
        "Auto-verify functions with confidence >=",
        0.0, 1.0, 0.9, 0.05,
        help="Functions with this confidence or higher will be automatically marked as verified"
    )

    eligible_count = sum(1 for f in functions if f.get('metadata', {}).get('extraction_confidence', 0) >= verification_confidence)
    st.info(f"📊 {eligible_count} functions eligible for auto-verification")

    if st.button("✅ Batch Verify High-Confidence Functions"):
        verified_count = 0
        for func in functions:
            if func.get('metadata', {}).get('extraction_confidence', 0) >= verification_confidence:
                func['metadata']['verified'] = True
                func['metadata']['needs_review'] = False
                verified_count += 1

        st.session_state.modified = True
        st.success(f"✅ Verified {verified_count} functions")
        st.rerun()

    # Statistics
    st.divider()
    st.subheader("📊 Statistics")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Functions", len(functions))
    with col2:
        verified = sum(1 for f in functions if f.get('metadata', {}).get('verified', False))
        st.metric("Verified", verified)
    with col3:
        needs_review = sum(1 for f in functions if f.get('metadata', {}).get('needs_review', False))
        st.metric("Needs Review", needs_review)


def main():
    """Main application entry point"""
    render_sidebar()

    if st.session_state.json_data:
        json_data = st.session_state.json_data

        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Overview",
            "🔍 Function Details",
            "✅ Validation",
            "⚡ Batch Ops"
        ])

        with tab1:
            render_overview_tab(json_data)

        with tab2:
            render_function_details_tab(json_data, st.session_state.image_dir)

        with tab3:
            render_validation_tab(json_data)

        with tab4:
            render_batch_operations_tab(json_data)
    else:
        st.info("👈 Select a JSON file from the sidebar to begin review")


if __name__ == "__main__":
    main()
