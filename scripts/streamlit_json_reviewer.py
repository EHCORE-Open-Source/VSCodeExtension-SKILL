#!/usr/bin/env python3
"""
Streamlit JSON Review & Validation UI with Full Editing Support

Purpose: Review, edit, and validate JSON files extracted by Gemini before database import
Input: JSON files from gemini_manual_image_converter.py
Output: Validated JSON files ready for database import

Features:
- Full inline editing of all fields
- Markdown preview for description
- Argument and return value editing
- Example editing and addition
- Real-time validation

Usage:
    streamlit run scripts/streamlit_json_reviewer.py

Author: Claude Code
Version: 1.2 (with editing support)
Date: 2025-10-11
"""

import streamlit as st
import json
import os
import copy
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
CONFIG_FILENAME = "streamlit_json_reviewer.config.json"


def load_app_config() -> Dict:
    """Load optional application configuration from known locations."""
    config: Dict = {}
    env_path = os.environ.get("STREAMLIT_JSON_REVIEWER_CONFIG", "").strip()
    candidate_paths = []

    if env_path:
        candidate_paths.append(Path(env_path).expanduser())

    candidate_paths.append(Path.cwd() / CONFIG_FILENAME)
    candidate_paths.append(Path(__file__).resolve().with_name(CONFIG_FILENAME))

    for path in candidate_paths:
        if not path:
            continue
        try:
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    raw_config = json.load(f)
                if isinstance(raw_config, dict):
                    config = raw_config
                    config['_config_source'] = str(path)
                    default_file = config.get('default_json_file')
                    if isinstance(default_file, str):
                        config['default_json_file'] = Path(default_file).name
                break
        except Exception as exc:
            print(f"[streamlit_json_reviewer] Failed to load config from {path}: {exc}")

    return config


APP_CONFIG = load_app_config()
DEFAULT_JSON_DIR = APP_CONFIG.get('json_directory', "test_output/")
DEFAULT_IMAGE_DIR = APP_CONFIG.get('image_directory', "docs/cadence_manual/images/")
DEFAULT_JSON_FILE = APP_CONFIG.get('default_json_file')

# Initialize session state
if 'current_file' not in st.session_state:
    st.session_state.current_file = None
if 'current_function_idx' not in st.session_state:
    st.session_state.current_function_idx = 0
if 'json_data' not in st.session_state:
    st.session_state.json_data = None
if 'original_json_data' not in st.session_state:
    st.session_state.original_json_data = None  # Store original data for discard changes
if 'modified' not in st.session_state:
    st.session_state.modified = False
if 'json_dir' not in st.session_state:
    st.session_state.json_dir = DEFAULT_JSON_DIR
if 'image_dir' not in st.session_state:
    st.session_state.image_dir = DEFAULT_IMAGE_DIR
if 'json_format' not in st.session_state:
    st.session_state.json_format = 'batch'  # 'batch' or 'single'
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False  # Toggle editing on/off
if 'default_json_file' not in st.session_state:
    st.session_state.default_json_file = DEFAULT_JSON_FILE
if 'selected_json_file' not in st.session_state:
    st.session_state.selected_json_file = None
if '_config_source' not in st.session_state and APP_CONFIG.get('_config_source'):
    st.session_state._config_source = APP_CONFIG['_config_source']


def load_json_file(json_path: str):
    """Load JSON file and store in session state (supports both batch and single function formats)"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        # Detect format: single function or batch format
        if 'manual_metadata' in raw_data and 'functions' in raw_data:
            # Batch format (e.g., sklangref_sklangref-031_to_sklangref-038.json)
            st.session_state.json_data = raw_data
            st.session_state.json_format = 'batch'
        elif 'function_name' in raw_data:
            # Single function format (e.g., append.json)
            # Convert to batch format for consistent processing
            st.session_state.json_data = {
                'manual_metadata': {
                    'manual_code': 'unknown',
                    'product_code': raw_data.get('availability', {}).get('product_code', 'SKILL'),
                    'product_hierarchy_level': 0,
                    'version': 'unknown',
                    'document_title': f"Single Function: {raw_data.get('function_name', 'unknown')}",
                    'source_type': 'manual',
                    'total_functions': 1,
                    'processing_timestamp': datetime.now().isoformat() + 'Z'
                },
                'functions': [raw_data]
            }
            st.session_state.json_format = 'single'
            st.session_state.single_function_data = raw_data  # Store original for saving
        else:
            st.error("❌ Unknown JSON format. Expected either batch format (with manual_metadata) or single function format (with function_name)")
            return False

        # Store a deep copy of original data for discard changes functionality
        st.session_state.original_json_data = copy.deepcopy(st.session_state.json_data)

        st.session_state.current_file = json_path
        st.session_state.current_function_idx = 0
        st.session_state.modified = False
        return True
    except Exception as e:
        st.error(f"❌ Failed to load JSON: {e}")
        return False


def save_json_file(json_data: dict, json_path: str):
    """Save modified JSON file (handles both batch and single function formats)"""
    try:
        # Create backup
        backup_path = json_path + ".backup"
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                backup_data = f.read()
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(backup_data)

        # Determine what to save based on format
        if st.session_state.get('json_format') == 'single':
            # For single function format, save only the function data (not the wrapper)
            save_data = json_data['functions'][0]
        else:
            # For batch format, save everything
            save_data = json_data

        # Save new data
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)

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

    config_source = st.session_state.get('_config_source')
    if config_source:
        st.sidebar.caption(f"Config: {config_source}")

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
            # Determine default selection based on config or previous user choice
            current_selection = st.session_state.get('selected_json_file')
            default_pref = st.session_state.get('default_json_file')

            if current_selection not in json_files:
                if default_pref and default_pref in json_files:
                    current_selection = default_pref
                else:
                    current_selection = json_files[0]
                st.session_state.selected_json_file = current_selection

            default_index = json_files.index(st.session_state.selected_json_file) if st.session_state.selected_json_file in json_files else 0

            selected_file = st.sidebar.selectbox(
                "Select JSON File",
                json_files,
                index=default_index,
                help="Choose a JSON file to review",
                key="selected_json_file"
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

        # Custom CSS for button colors - must be before buttons
        st.markdown("""
        <style>
        /* Blue Save button - ensure primary button is blue */
        [data-testid="stSidebar"] button[kind="primary"]:not(:disabled),
        [data-testid="stSidebar"] button[data-testid="baseButton-primary"]:not(:disabled) {
            background-color: #003f8c !important;
            background: #003f8c !important;
            color: #ffffff !important;
            border: 1px solid #003575 !important;
        }
        [data-testid="stSidebar"] button[kind="primary"]:hover:not(:disabled),
        [data-testid="stSidebar"] button[data-testid="baseButton-primary"]:hover:not(:disabled) {
            background-color: #002e66 !important;
            background: #002e66 !important;
            border-color: #002856 !important;
        }
        [data-testid="stSidebar"] button[kind="primary"]:disabled,
        [data-testid="stSidebar"] button[data-testid="baseButton-primary"]:disabled,
        [data-testid="stSidebar"] button[data-testid="baseButton-primary"][disabled] {
            background-color: #ffffff !important;
            background: #ffffff !important;
            color: #6c757d !important;
            border: 1px solid #d1d5db !important;
            opacity: 1 !important;
        }

        /* Red Discard button - secondary button should be red */
        [data-testid="stSidebar"] button[kind="secondary"]:not(:disabled),
        [data-testid="stSidebar"] button[data-testid="baseButton-secondary"]:not(:disabled) {
            background-color: #a11222 !important;
            background: #a11222 !important;
            color: #ffffff !important;
            border: 1px solid #8c101d !important;
        }
        [data-testid="stSidebar"] button[kind="secondary"]:hover:not(:disabled),
        [data-testid="stSidebar"] button[data-testid="baseButton-secondary"]:hover:not(:disabled) {
            background-color: #7d0c18 !important;
            background: #7d0c18 !important;
            border-color: #720a15 !important;
        }
        [data-testid="stSidebar"] button[kind="secondary"]:disabled,
        [data-testid="stSidebar"] button[data-testid="baseButton-secondary"]:disabled,
        [data-testid="stSidebar"] button[data-testid="baseButton-secondary"][disabled] {
            background-color: #ffffff !important;
            background: #ffffff !important;
            color: #6c757d !important;
            border: 1px solid #d1d5db !important;
            opacity: 1 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # Save and Discard buttons (vertical layout)
        if st.sidebar.button("💾 Save Changes", type="primary", disabled=not st.session_state.modified, use_container_width=True, key="save_btn"):
            if save_json_file(st.session_state.json_data, st.session_state.current_file):
                st.sidebar.success("✅ Saved!")
                st.rerun()

        if st.sidebar.button("❌ Discard Changes", type="secondary", disabled=not st.session_state.modified, use_container_width=True, key="discard_btn"):
            # Restore original data from deep copy
            st.session_state.json_data = copy.deepcopy(st.session_state.original_json_data)
            st.session_state.modified = False
            st.session_state.edit_mode = False  # Exit edit mode when discarding
            st.sidebar.info("✅ Changes discarded!")
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
    """Render function details tab with FULL editing capabilities"""
    functions = json_data.get('functions', [])

    if not functions:
        st.warning("No functions found in JSON file")
        return

    # Title and function navigation
    col_title, col_nav1, col_nav2, col_nav3 = st.columns([2, 1, 2, 1])
    with col_title:
        st.title("🔍 Function Details & Editing")
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
    edit_mode = st.session_state.edit_mode

    # Two-column layout
    col1, col2 = st.columns([1.2, 1])

    with col1:
        # Function Data header with Edit Mode toggle
        col_data_title, col_edit_toggle = st.columns([3, 1])
        with col_data_title:
            st.subheader("📝 Function Data")
        with col_edit_toggle:
            # Edit mode toggle
            if st.button("✏️ Edit Mode" if not st.session_state.edit_mode else "👁️ View Mode"):
                st.session_state.edit_mode = not st.session_state.edit_mode
                st.rerun()

        # Basic info (editable)
        st.markdown("### Basic Information")
        new_func_name = st.text_input(
            "Function Name",
            value=func['function_name'],
            disabled=not edit_mode,
            key="func_name"
        )
        if edit_mode and new_func_name != func['function_name']:
            func['function_name'] = new_func_name
            st.session_state.modified = True

        new_category = st.text_input(
            "Category",
            value=func.get('category', 'Uncategorized'),
            disabled=not edit_mode,
            key="func_category"
        )
        if edit_mode and new_category != func.get('category', 'Uncategorized'):
            func['category'] = new_category
            st.session_state.modified = True

        # Primary syntax (editable)
        st.markdown("### Primary Syntax")
        new_syntax_string = st.text_input(
            "Syntax String",
            value=func['primary_syntax']['syntax_string'],
            disabled=not edit_mode,
            key="syntax_string"
        )
        if edit_mode and new_syntax_string != func['primary_syntax']['syntax_string']:
            func['primary_syntax']['syntax_string'] = new_syntax_string
            st.session_state.modified = True

        new_return_syntax = st.text_input(
            "Return Syntax",
            value=func['primary_syntax']['return_syntax'],
            disabled=not edit_mode,
            key="return_syntax"
        )
        if edit_mode and new_return_syntax != func['primary_syntax']['return_syntax']:
            func['primary_syntax']['return_syntax'] = new_return_syntax
            st.session_state.modified = True

        # Description with Markdown Preview
        st.markdown("### Description")

        if edit_mode:
            # Edit mode: Text area for editing
            col_desc1, col_desc2 = st.columns(2)

            with col_desc1:
                st.markdown("**✏️ Edit (Markdown)**")
                new_description = st.text_area(
                    "Edit Description",
                    value=func.get('description', ''),
                    height=300,
                    label_visibility="collapsed",
                    key="description_edit"
                )
                if new_description != func.get('description', ''):
                    func['description'] = new_description
                    st.session_state.modified = True

            with col_desc2:
                st.markdown("**👁️ Preview (Rendered)**")
                # Show rendered markdown preview
                st.markdown(new_description if new_description else "*No description*")
        else:
            # View mode: Show rendered markdown
            st.markdown(func.get('description', '*No description*'))

        # Arguments (editable with data_editor)
        st.markdown("### Arguments")
        if func['primary_syntax'].get('arguments'):
            args_df = pd.DataFrame(func['primary_syntax']['arguments'])

            if edit_mode:
                edited_args = st.data_editor(
                    args_df,
                    use_container_width=True,
                    num_rows="dynamic",
                    column_config={
                        "name": st.column_config.TextColumn("Name", required=True),
                        "type_prefix": st.column_config.SelectboxColumn(
                            "Type Prefix",
                            options=VALID_TYPE_PREFIXES,
                            required=True
                        ),
                        "type_description": st.column_config.TextColumn("Type Desc"),
                        "parameter_type": st.column_config.SelectboxColumn(
                            "Param Type",
                            options=[0, 1, 2, 3],
                            help="0=required, 1=keyword, 2=optional, 3=rest",
                            required=True
                        ),
                        "description": st.column_config.TextColumn("Description", width="large"),
                        "position": st.column_config.NumberColumn("Position", min_value=0),
                        "is_keyword": st.column_config.CheckboxColumn("Keyword"),
                        "default_value": st.column_config.TextColumn("Default")
                    },
                    hide_index=True,
                    key="args_editor"
                )

                # Update function data if changed
                if not edited_args.equals(args_df):
                    func['primary_syntax']['arguments'] = edited_args.to_dict('records')
                    st.session_state.modified = True
            else:
                st.dataframe(
                    args_df[['name', 'type_prefix', 'type_description', 'parameter_type', 'description']],
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.info("No arguments")

        # Return values (editable)
        st.markdown("### Return Values")
        if func['primary_syntax'].get('return_values'):
            ret_df = pd.DataFrame(func['primary_syntax']['return_values'])

            if edit_mode:
                edited_ret = st.data_editor(
                    ret_df,
                    use_container_width=True,
                    num_rows="dynamic",
                    column_config={
                        "type_name": st.column_config.TextColumn("Type Name", required=True),
                        "type_prefix": st.column_config.SelectboxColumn(
                            "Type Prefix",
                            options=VALID_TYPE_PREFIXES,
                            required=True
                        ),
                        "type_description": st.column_config.TextColumn("Type Desc"),
                        "description": st.column_config.TextColumn("Description", width="large"),
                        "position": st.column_config.NumberColumn("Position", min_value=0)
                    },
                    hide_index=True,
                    key="return_editor"
                )

                if not edited_ret.equals(ret_df):
                    func['primary_syntax']['return_values'] = edited_ret.to_dict('records')
                    st.session_state.modified = True
            else:
                st.dataframe(
                    ret_df[['type_name', 'type_prefix', 'type_description', 'description']],
                    use_container_width=True,
                    hide_index=True
                )

        # Overloads (display only for now - can be expanded)
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

        # Examples (editable)
        st.markdown("### Examples")
        if func.get('examples'):
            for idx, example in enumerate(func['examples']):
                with st.expander(f"Example {idx + 1}", expanded=edit_mode):
                    if edit_mode:
                        new_code = st.text_area(
                            "Code",
                            value=example.get('code', ''),
                            height=150,
                            key=f"example_{idx}_code"
                        )
                        if new_code != example.get('code', ''):
                            example['code'] = new_code
                            st.session_state.modified = True

                        new_example_desc = st.text_area(
                            "Description",
                            value=example.get('description', ''),
                            key=f"example_{idx}_desc"
                        )
                        if new_example_desc != example.get('description', ''):
                            example['description'] = new_example_desc
                            st.session_state.modified = True

                        if st.button(f"🗑️ Delete Example {idx + 1}", key=f"delete_example_{idx}"):
                            func['examples'].pop(idx)
                            st.session_state.modified = True
                            st.rerun()
                    else:
                        st.code(example.get('code', ''), language="scheme")
                        if example.get('description'):
                            st.markdown(f"**Description:** {example['description']}")
        else:
            st.info("No examples")

        if edit_mode and st.button("➕ Add New Example"):
            if 'examples' not in func:
                func['examples'] = []
            func['examples'].append({
                'code': '',
                'description': '',
                'position': len(func['examples'])
            })
            st.session_state.modified = True
            st.rerun()

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

        # Metadata (editable)
        st.markdown("### Metadata")
        metadata = func.get('metadata', {})

        if edit_mode:
            col_meta1, col_meta2 = st.columns(2)
            with col_meta1:
                new_verified = st.checkbox("Verified", value=metadata.get('verified', False), key="meta_verified")
                if new_verified != metadata.get('verified', False):
                    metadata['verified'] = new_verified
                    st.session_state.modified = True
            with col_meta2:
                new_needs_review = st.checkbox("Needs Review", value=metadata.get('needs_review', False), key="meta_review")
                if new_needs_review != metadata.get('needs_review', False):
                    metadata['needs_review'] = new_needs_review
                    st.session_state.modified = True

            new_confidence = st.slider(
                "Extraction Confidence",
                0.0, 1.0,
                value=metadata.get('extraction_confidence', 0.0),
                step=0.01,
                key="meta_confidence"
            )
            if abs(new_confidence - metadata.get('extraction_confidence', 0.0)) > 0.001:
                metadata['extraction_confidence'] = new_confidence
                st.session_state.modified = True
        else:
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

        if st.button("✅ Mark as Verified", use_container_width=True, disabled=edit_mode):
            func['metadata']['verified'] = True
            func['metadata']['needs_review'] = False
            st.session_state.modified = True
            st.success("✅ Marked as verified!")
            st.rerun()

        if st.button("⚠️ Flag for Review", use_container_width=True, disabled=edit_mode):
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
