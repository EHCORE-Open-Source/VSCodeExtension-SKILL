-- ============================================================================
-- SKILL Function Database Seed Data
-- ============================================================================
-- Version: 3.5
-- Date: 2025-10-10
-- Reference: SKILL_DATABASE_TABLE_DESIGN.md v3.5
-- Purpose: Initial data for testing and development
-- ============================================================================

-- ============================================================================
-- 1. DATA TYPES (SKILL Type System)
-- ============================================================================

INSERT INTO data_types (prefix, internal_name, type_description) VALUES
    -- Basic types
    ('l', 'list', 'Linked list'),
    ('g', 'general', 'Any data type'),
    ('n', 'number', 'Integer or floating-point number'),
    ('x', 'integer', 'Integer number'),
    ('f', 'flonum', 'Floating-point number'),
    ('t', 'string', 'Character string'),
    ('s', 'symbol', 'Symbol'),
    ('S', 'stringSymbol', 'Symbol or string'),

    -- User-defined types
    ('o', 'userType', 'User-defined type'),
    ('r', 'defstruct', 'Defstruct'),
    ('a', 'array', 'Array'),

    -- Database types
    ('d', 'dbobject', 'Database object'),
    ('e', 'environment', 'Environment'),

    -- UI types
    ('w', 'wtype', 'Window type'),
    ('p', 'port', 'I/O port'),
    ('u', 'function', 'Function object'),

    -- Special types
    ('b', 'ddpiObject', 'DDPI object'),
    ('c', 'class', 'Class object'),
    ('h', 'handle', 'Handle'),
    ('i', 'instance', 'Instance'),
    ('k', 'keyword', 'Keyword'),
    ('m', 'method', 'Method'),
    ('v', 'vector', 'Vector'),
    ('y', 'property', 'Property'),
    ('z', 'context', 'Context');

-- ============================================================================
-- 2. PRODUCT HIERARCHY (v3.4: Single inheritance using parent_product_id)
-- ============================================================================

-- Level 0: SKILL Core
INSERT INTO products (id, code, name, hierarchy_level, parent_product_id, description) VALUES
    (0, 'SKILL', 'SKILL Core', 0, NULL, 'Core SKILL language - universal functions available to all products');

-- Level 1: Product Families
INSERT INTO products (id, code, name, hierarchy_level, parent_product_id, description) VALUES
    (1, 'Virtuoso', 'Virtuoso Family', 1, 0, 'Virtuoso product family - IC design tools'),
    (2, 'Allegro', 'Allegro Family', 1, 0, 'Allegro product family - PCB design tools');

-- Level 2: Specific Products
INSERT INTO products (id, code, name, hierarchy_level, parent_product_id, description) VALUES
    -- Virtuoso products
    (3, 'IC', 'Virtuoso IC', 2, 1, 'Virtuoso Integrated Circuit Design'),
    (4, 'ICADV', 'Virtuoso Advanced', 2, 1, 'Virtuoso Advanced with Visualization and Analysis'),
    (5, 'ICADVM', 'Virtuoso Advanced Maestro', 2, 1, 'Virtuoso Advanced with Maestro analog simulation'),

    -- Allegro products
    (6, 'SPB', 'SPB Foundation', 2, 2, 'System-in-Package and Board Design Foundation'),
    (7, 'AllegroDesigner', 'Allegro PCB Designer', 2, 2, 'Allegro PCB Design Tool');

-- ============================================================================
-- 3. VERSIONS (Five-segment version system)
-- ============================================================================

INSERT INTO versions (major, minor, patch, revision, hotfix, version_string) VALUES
    -- Old versions
    (5, 1, 4, 1, NULL, '5.1.4.1'),
    (5, 1, 4, 1, 1, '5.1.4.1.1'),
    (6, 1, 5, NULL, NULL, '6.1.5'),
    (6, 1, 6, NULL, NULL, '6.1.6'),
    (6, 1, 7, NULL, NULL, '6.1.7'),
    (6, 1, 8, NULL, NULL, '6.1.8'),
    (6, 1, 8, 500, NULL, '6.1.8.500'),

    -- Modern versions
    (18, 1, 0, NULL, NULL, '18.1'),
    (22, 1, 0, NULL, NULL, '22.1'),
    (23, 1, 0, NULL, NULL, '23.1'),
    (23, 1, 1, NULL, NULL, '23.1.1'),
    (24, 1, 0, NULL, NULL, '24.1'),
    (25, 1, 0, NULL, NULL, '25.1');

-- ============================================================================
-- 4. PRODUCT RELEASES (v3.5: Simplified)
-- ============================================================================

-- IC releases
INSERT INTO product_releases (product_id, version_id, abbreviation, official_name) VALUES
    (3, (SELECT id FROM versions WHERE version_string='5.1.4.1'), 'IC5141', 'Cadence Virtuoso IC 5.1.4.1'),
    (3, (SELECT id FROM versions WHERE version_string='6.1.5'), 'IC615', 'Cadence Virtuoso IC 6.1.5'),
    (3, (SELECT id FROM versions WHERE version_string='6.1.6'), 'IC616', 'Cadence Virtuoso IC 6.1.6'),
    (3, (SELECT id FROM versions WHERE version_string='6.1.7'), 'IC617', 'Cadence Virtuoso IC 6.1.7'),
    (3, (SELECT id FROM versions WHERE version_string='6.1.8'), 'IC618', 'Cadence Virtuoso IC 6.1.8'),
    (3, (SELECT id FROM versions WHERE version_string='18.1'), 'IC181', 'Cadence Virtuoso IC 18.1'),
    (3, (SELECT id FROM versions WHERE version_string='22.1'), 'IC221', 'Cadence Virtuoso IC 22.1'),
    (3, (SELECT id FROM versions WHERE version_string='23.1'), 'IC231', 'Cadence Virtuoso IC 23.1');

-- ICADV releases
INSERT INTO product_releases (product_id, version_id, abbreviation, official_name) VALUES
    (4, (SELECT id FROM versions WHERE version_string='6.1.5'), 'ICADV615', 'Cadence Virtuoso Advanced 6.1.5'),
    (4, (SELECT id FROM versions WHERE version_string='6.1.6'), 'ICADV616', 'Cadence Virtuoso Advanced 6.1.6'),
    (4, (SELECT id FROM versions WHERE version_string='6.1.7'), 'ICADV617', 'Cadence Virtuoso Advanced 6.1.7'),
    (4, (SELECT id FROM versions WHERE version_string='6.1.8'), 'ICADV618', 'Cadence Virtuoso Advanced 6.1.8'),
    (4, (SELECT id FROM versions WHERE version_string='18.1'), 'ICADV181', 'Cadence Virtuoso Advanced 18.1'),
    (4, (SELECT id FROM versions WHERE version_string='23.1'), 'ICADV231', 'Cadence Virtuoso Advanced 23.1');

-- ICADVM releases
INSERT INTO product_releases (product_id, version_id, abbreviation, official_name) VALUES
    (5, (SELECT id FROM versions WHERE version_string='6.1.8'), 'ICADVM618', 'Cadence Virtuoso Advanced Maestro 6.1.8'),
    (5, (SELECT id FROM versions WHERE version_string='23.1'), 'ICADVM231', 'Cadence Virtuoso Advanced Maestro 23.1');

-- SPB releases
INSERT INTO product_releases (product_id, version_id, abbreviation, official_name) VALUES
    (6, (SELECT id FROM versions WHERE version_string='22.1'), 'SPB221', 'Cadence SPB Foundation 22.1'),
    (6, (SELECT id FROM versions WHERE version_string='23.1'), 'SPB231', 'Cadence SPB Foundation 23.1');

-- Allegro releases
INSERT INTO product_releases (product_id, version_id, abbreviation, official_name) VALUES
    (7, (SELECT id FROM versions WHERE version_string='22.1'), 'Allegro221', 'Cadence Allegro PCB Designer 22.1'),
    (7, (SELECT id FROM versions WHERE version_string='23.1'), 'Allegro231', 'Cadence Allegro PCB Designer 23.1');

-- ============================================================================
-- 5. SAMPLE DOCUMENTS
-- ============================================================================

-- SKILL Core documentation (generic for all products) - Scenario 1: product_id=0, product_release_id=NULL is INVALID
-- Must use: (NULL, NULL) OR (product_id, NULL) OR (NULL, product_release_id)
INSERT INTO documents (title, product_id, product_release_id, source_type) VALUES
    ('Cadence SKILL Language Reference', NULL, NULL, 'manual'),  -- Scenario 1: Generic
    ('SKILL Development Guide', NULL, NULL, 'manual');           -- Scenario 1: Generic

-- Virtuoso family documentation - Scenario 2: product-level
INSERT INTO documents (title, product_id, product_release_id, source_type) VALUES
    ('Virtuoso Common Functions', 1, NULL, 'manual');  -- Scenario 2: Virtuoso family

-- ICADV specific documentation - Scenario 3: version-specific
INSERT INTO documents (title, product_id, product_release_id, source_type) VALUES
    ('Virtuoso Visualization and Analysis XL SKILL Reference',
     NULL, (SELECT id FROM product_releases WHERE abbreviation='ICADV618'), 'manual');  -- Scenario 3: Version-specific

-- ============================================================================
-- 6. SAMPLE CATEGORIES
-- ============================================================================

-- SKILL Language Reference categories
INSERT INTO categories (document_id, name, parent_category_id) VALUES
    (1, 'List Functions', NULL),
    (1, 'Arithmetic Functions', NULL),
    (1, 'String Functions', NULL),
    (1, 'Control Flow', NULL);

-- Virtuoso specific categories
INSERT INTO categories (document_id, name, parent_category_id) VALUES
    (3, 'Database Functions', NULL),
    (3, 'Layout Functions', NULL);

-- ICADV specific categories
INSERT INTO categories (document_id, name, parent_category_id) VALUES
    (4, 'Waveform Window Functions', NULL),
    (4, 'Data Analysis Functions', NULL);

-- ============================================================================
-- 7. SAMPLE FUNCTIONS (Testing data)
-- ============================================================================

-- Example 1: SKILL Core function (universal) - Scenario 1: (NULL, NULL)
INSERT INTO functions (name) VALUES ('append');
INSERT INTO function_details (function_id, product_id, product_release_id, description, status) VALUES
    (1, NULL, NULL, 'Appends two lists together.\n\nReturns a new list with all elements from both input lists.', 'active');

INSERT INTO function_categories (function_id, category_id) VALUES (1, 1);

INSERT INTO function_syntax (function_id, product_release_id, syntax_string, return_syntax) VALUES
    (1, NULL, 'append(l_list1 l_list2)', 'l_result');

INSERT INTO function_arguments (function_syntax_id, name, type_prefix, description, parameter_type, position) VALUES
    (1, 'l_list1', 'l', 'First list', 0, 0),
    (1, 'l_list2', 'l', 'Second list', 0, 1);

INSERT INTO function_return_values (function_syntax_id, type_name, type_prefix, description, position) VALUES
    (1, 'l_result', 'l', 'Combined list containing all elements from both lists', 0);

INSERT INTO function_availability (function_id, product_id, product_release_id, status) VALUES
    (1, NULL, NULL, 'active');

-- Example 2: Virtuoso family function - Scenario 2: (product_id, NULL)
INSERT INTO functions (name) VALUES ('dbOpenCellView');
INSERT INTO function_details (function_id, product_id, product_release_id, description, status) VALUES
    (2, 1, NULL, 'Opens a cellview from the database.\n\nThis function is available in all Virtuoso products.', 'active');

INSERT INTO function_categories (function_id, category_id) VALUES (2, 5);

INSERT INTO function_syntax (function_id, product_release_id, syntax_string, return_syntax) VALUES
    (2, NULL, 'dbOpenCellView(t_libName t_cellName t_viewName)', 'd_cellView/nil');

INSERT INTO function_arguments (function_syntax_id, name, type_prefix, description, parameter_type, position) VALUES
    (2, 't_libName', 't', 'Library name', 0, 0),
    (2, 't_cellName', 't', 'Cell name', 0, 1),
    (2, 't_viewName', 't', 'View name', 0, 2);

INSERT INTO function_return_values (function_syntax_id, type_name, type_prefix, description, position) VALUES
    (2, 'd_cellView', 'd', 'Database cellview object', 0),
    (2, 'nil', NULL, 'Returns nil if cellview not found', 1);

INSERT INTO function_availability (function_id, product_id, product_release_id, status) VALUES
    (2, 1, NULL, 'active');

-- Example 3: ICADV specific function (version-specific) - Scenario 3: (NULL, product_release_id)
INSERT INTO functions (name) VALUES ('awvAppendList');
INSERT INTO function_details (
    function_id,
    product_id,
    product_release_id,
    description,
    notes,
    status
) VALUES (
    3,
    NULL,  -- Changed from 4 to NULL for CHECK constraint
    (SELECT id FROM product_releases WHERE abbreviation='ICADV618'),
    'Plots a list of y-values in a waveform window.\n\nSupports multiple parameter combinations for flexible plotting.',
    'This function requires an active waveform window.',
    'active'
);

INSERT INTO function_categories (function_id, category_id) VALUES (3, 7);

-- First syntax variant
INSERT INTO function_syntax (function_id, product_release_id, syntax_string, return_syntax) VALUES
    (3, (SELECT id FROM product_releases WHERE abbreviation='ICADV618'),
     'awvAppendList(w_windowID l_yList l_xList)', 'nil');

INSERT INTO function_arguments (function_syntax_id, name, type_prefix, description, parameter_type, position) VALUES
    (3, 'w_windowID', 'w', 'Waveform window ID', 0, 0),
    (3, 'l_yList', 'l', 'List of y-values', 0, 1),
    (3, 'l_xList', 'l', 'List of x-values', 0, 2);

INSERT INTO function_return_values (function_syntax_id, type_name, description, position) VALUES
    (3, 'nil', 'Always returns nil', 0);

-- Second syntax variant (with keyword parameters)
INSERT INTO function_syntax (function_id, product_release_id, syntax_string, return_syntax) VALUES
    (3, (SELECT id FROM product_releases WHERE abbreviation='ICADV618'),
     'awvAppendList(w_windowID ?expr l_exprList)', 'nil');

INSERT INTO function_arguments (function_syntax_id, name, type_prefix, description, parameter_type, position) VALUES
    (4, 'w_windowID', 'w', 'Waveform window ID', 0, 0),
    (4, 'l_exprList', 'l', 'List of waveform expressions', 1, 1);  -- parameter_type=1 for keyword

INSERT INTO function_return_values (function_syntax_id, type_name, description, position) VALUES
    (4, 'nil', 'Always returns nil', 0);

-- Function availability (ICADV family)
INSERT INTO function_availability (function_id, product_id, product_release_id, status) VALUES
    (3, 4, NULL, 'active');

-- Example code
INSERT INTO function_examples (function_id, code, description, position) VALUES
    (3, 'win = awvCreatePlotWindow()\nawvAppendList(win list(1 2 3 4) list(0 1 2 3))',
     'Create a window and plot a simple line', 0);

-- Source tracking
INSERT INTO function_sources (function_id, source_file, start_page_number, end_page_number) VALUES
    (3, 'vivaxlskill.pdf', 46, 47);

-- ============================================================================
-- End of Seed Data
-- ============================================================================
