-- ============================================================================
-- SKILL Function Database Schema
-- ============================================================================
-- Version: 3.5
-- Date: 2025-10-10
-- Reference: SKILL_DATABASE_TABLE_DESIGN.md v3.5
-- Changes from v3.4:
--   - Removed all created_at/updated_at timestamp fields
--   - Added product_id to documents table
--   - Added product_id and status to function_details table
--   - Optimized function_syntax table (removed syntax_index, split return_syntax)
--   - Simplified function_arguments (parameter_type INTEGER replaces boolean fields)
--   - Simplified product_releases table (removed unused fields)
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ============================================================================
-- 1. CORE DATA TABLES
-- ============================================================================

-- 1.1 SKILL Data Type Definitions
CREATE TABLE data_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prefix TEXT UNIQUE NOT NULL,            -- 'l', 'g', 'n', 'x', 't', 'f', 's', 'S', 'o', etc.
    internal_name TEXT,                     -- 'list', 'general', 'number', 'string'
    type_description TEXT                   -- '鏈結列表', '任意資料型別'
);

CREATE INDEX idx_datatype_prefix ON data_types(prefix);

-- 1.2 Product Hierarchy (v3.4: Single inheritance mechanism)
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,              -- 'SKILL', 'Virtuoso', 'Allegro', 'IC', 'ICADV', 'ICADVM', 'SPB'
    name TEXT NOT NULL,                     -- 'SKILL Core', 'Virtuoso Family', 'Virtuoso IC'
    hierarchy_level INTEGER NOT NULL,       -- 0=SKILL Core, 1=Virtuoso/Allegro, 2=IC/ICADV/ICADVM/SPB
    parent_product_id INTEGER,              -- Inheritance relationship (NULL = root)
    description TEXT,

    FOREIGN KEY (parent_product_id) REFERENCES products(id)
);

CREATE INDEX idx_product_hierarchy ON products(hierarchy_level);
CREATE INDEX idx_product_parent ON products(parent_product_id);

-- ============================================================================
-- 2. VERSION CONTROL TABLES
-- ============================================================================

-- 2.1 Version Numbers (Five-segment version system)
CREATE TABLE versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Five-segment version number
    major INTEGER NOT NULL,                 -- 5, 6, 18, 23, 25
    minor INTEGER NOT NULL,                 -- 1
    patch INTEGER NOT NULL DEFAULT 0,       -- 4, 8
    revision INTEGER DEFAULT NULL,          -- 1 (for 5.1.4.1)
    hotfix INTEGER DEFAULT NULL,            -- 1, 2, 500

    -- Complete version string
    version_string TEXT UNIQUE NOT NULL,    -- '5.1.4.1', '6.1.8', '23.1'

    UNIQUE(major, minor, patch, revision, hotfix)
);

CREATE INDEX idx_version_string ON versions(version_string);
CREATE INDEX idx_version_sort ON versions(major, minor, patch, revision, hotfix);

-- 2.2 Product Releases (v3.5: Simplified)
CREATE TABLE product_releases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,            -- Product ID
    version_id INTEGER NOT NULL,            -- Version ID

    -- Product abbreviation (auto-generated or manually specified)
    abbreviation TEXT UNIQUE NOT NULL,      -- 'IC618', 'ICADV618', 'IC231'

    -- Official name
    official_name TEXT,                     -- 'Cadence Virtuoso 6.1.8'

    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (version_id) REFERENCES versions(id),
    UNIQUE(product_id, version_id)
);

CREATE INDEX idx_release_product ON product_releases(product_id);
CREATE INDEX idx_release_version ON product_releases(version_id);
CREATE INDEX idx_release_abbr ON product_releases(abbreviation);

-- ============================================================================
-- 3. DOCUMENT AND CATEGORY TABLES
-- ============================================================================

-- 3.1 Documents (v3.5: Added product_id)
CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,                    -- 'Cadence SKILL Language Reference'
    product_id INTEGER,                     -- Corresponding product (generic document level)
    product_release_id INTEGER,             -- Specific product release version
    source_type TEXT DEFAULT 'manual',      -- 'manual', 'builtin', 'custom'

    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (product_release_id) REFERENCES product_releases(id),

    CHECK (
        -- Scenario 1: Generic document (all products/versions)
        (product_id IS NULL AND product_release_id IS NULL) OR
        -- Scenario 2: Product-level document (e.g., Virtuoso family)
        (product_id IS NOT NULL AND product_release_id IS NULL) OR
        -- Scenario 3: Version-specific document (e.g., ICADV 6.1.8)
        (product_id IS NULL AND product_release_id IS NOT NULL)
    )
);

CREATE INDEX idx_document_product ON documents(product_id);
CREATE INDEX idx_document_release ON documents(product_release_id);
CREATE INDEX idx_document_type ON documents(source_type);

-- 3.2 Categories (Hierarchical classification)
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,                    -- Owning document
    name TEXT NOT NULL,                     -- 'List Functions', 'Waveform Window Functions'
    parent_category_id INTEGER,             -- Support for sub-categories

    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_category_id) REFERENCES categories(id) ON DELETE SET NULL
);

CREATE INDEX idx_category_document ON categories(document_id);
CREATE INDEX idx_category_parent ON categories(parent_category_id);

-- ============================================================================
-- 4. FUNCTION CORE TABLES
-- ============================================================================

-- 4.1 Function Name Registry (v3.1: Simplified design)
CREATE TABLE functions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL               -- Function name (unique)
);

CREATE INDEX idx_function_name ON functions(name);

-- 4.2 Function Details (v3.5: Optimized)
CREATE TABLE function_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    function_id INTEGER NOT NULL,           -- Corresponding function ID (not unique, supports multi-version)
    product_id INTEGER,                     -- Corresponding product (NULL = generic, applies to all products)
    product_release_id INTEGER,             -- Corresponding product release version (NULL = generic, applies to all versions)
    description TEXT,                       -- Function description (Markdown format)
    notes TEXT,                             -- Additional notes/warnings
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'deprecated', 'removed')),
    verified BOOLEAN DEFAULT 0,             -- Verification status

    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (product_release_id) REFERENCES product_releases(id),

    -- Unique constraint: One detail per function per product/version
    UNIQUE(function_id, product_id, product_release_id),

    CHECK (
        -- Scenario 1: Generic description (all products/versions)
        (product_id IS NULL AND product_release_id IS NULL) OR
        -- Scenario 2: Product-level description (e.g., Virtuoso family)
        (product_id IS NOT NULL AND product_release_id IS NULL) OR
        -- Scenario 3: Version-specific description (e.g., ICADV 6.1.8)
        (product_id IS NULL AND product_release_id IS NOT NULL)
    )
);

CREATE INDEX idx_detail_function ON function_details(function_id);
CREATE INDEX idx_detail_product ON function_details(product_id);
CREATE INDEX idx_detail_release ON function_details(product_release_id);
CREATE INDEX idx_detail_status ON function_details(status);
CREATE INDEX idx_detail_verified ON function_details(verified);

-- 4.3 Function Categories (v3.3: Junction table)
CREATE TABLE function_categories (
    function_id INTEGER NOT NULL,           -- Function ID
    category_id INTEGER NOT NULL,           -- Category ID

    PRIMARY KEY (function_id, category_id),
    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

CREATE INDEX idx_func_cat_function ON function_categories(function_id);
CREATE INDEX idx_func_cat_category ON function_categories(category_id);

-- 4.4 Function Aliases
CREATE TABLE function_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    function_id INTEGER NOT NULL,           -- Main function definition
    alias_name TEXT NOT NULL UNIQUE,        -- Alias ('caar', 'cadr', 'cdar')

    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE
);

CREATE INDEX idx_alias_function ON function_aliases(function_id);
CREATE INDEX idx_alias_name ON function_aliases(alias_name);

-- 4.5 Function Syntax (v3.5: Optimized)
CREATE TABLE function_syntax (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    function_id INTEGER NOT NULL,           -- Owning function
    product_release_id INTEGER,             -- Corresponding product release version (NULL = generic syntax)
    syntax_string TEXT NOT NULL,            -- Function call syntax (without return value)
    return_syntax TEXT,                     -- Return value syntax
    description TEXT,                       -- Description of this syntax

    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE,
    FOREIGN KEY (product_release_id) REFERENCES product_releases(id),
    UNIQUE(function_id, product_release_id, syntax_string)
);

CREATE INDEX idx_syntax_function ON function_syntax(function_id);
CREATE INDEX idx_syntax_release ON function_syntax(product_release_id);

-- 4.6 Function Arguments (v3.5: Optimized)
CREATE TABLE function_arguments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    function_syntax_id INTEGER NOT NULL,    -- Corresponding specific syntax
    name TEXT NOT NULL,                     -- Parameter name ('l_list', '?expr l_exprList')
    type_prefix TEXT,                       -- Type prefix ('l', 'g', 'n')
    type_description TEXT,                  -- Human-readable type description
    description TEXT,                       -- Parameter description
    parameter_type INTEGER DEFAULT 0 CHECK(parameter_type IN (0, 1, 2, 3)),  -- 0=required, 1=keyword, 2=optional, 3=rest
    default_value TEXT,                     -- Default value (if any)
    position INTEGER NOT NULL,              -- Parameter order (0-based)

    FOREIGN KEY (function_syntax_id) REFERENCES function_syntax(id) ON DELETE CASCADE,
    FOREIGN KEY (type_prefix) REFERENCES data_types(prefix)
);

CREATE INDEX idx_argument_syntax ON function_arguments(function_syntax_id);
CREATE INDEX idx_argument_position ON function_arguments(function_syntax_id, position);

-- 4.7 Function Return Values (v3.5: Preserved position field)
CREATE TABLE function_return_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    function_syntax_id INTEGER NOT NULL,    -- Corresponding specific syntax
    type_name TEXT,                         -- Return value name ('t', 'nil', 'l_result')
    type_prefix TEXT,                       -- Type prefix ('t', 'l', 'x')
    description TEXT,                       -- Return value description
    position INTEGER,                       -- Display order (0=primary, 1=secondary, 2=error)

    FOREIGN KEY (function_syntax_id) REFERENCES function_syntax(id) ON DELETE CASCADE,
    FOREIGN KEY (type_prefix) REFERENCES data_types(prefix)
);

CREATE INDEX idx_return_syntax ON function_return_values(function_syntax_id);
CREATE INDEX idx_return_position ON function_return_values(function_syntax_id, position);

-- 4.8 Function Examples
CREATE TABLE function_examples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    function_id INTEGER NOT NULL,           -- Owning function
    code TEXT NOT NULL,                     -- Example code
    description TEXT,                       -- Example description
    position INTEGER,                       -- Display order

    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE
);

CREATE INDEX idx_example_function ON function_examples(function_id);
CREATE INDEX idx_example_position ON function_examples(function_id, position);

-- 4.9 Function Sources (Source tracking)
CREATE TABLE function_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    function_id INTEGER NOT NULL,           -- Function ID
    source_file TEXT,                       -- Source file (PDF/HTML/MD)
    start_page_number INTEGER,              -- Start page number
    end_page_number INTEGER,                -- End page number (can equal start_page_number or be NULL for single page)

    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE
);

CREATE INDEX idx_source_function ON function_sources(function_id);
CREATE INDEX idx_source_file ON function_sources(source_file);

-- ============================================================================
-- 5. FUNCTION AVAILABILITY CONTROL (v3.4: Simplified inheritance)
-- ============================================================================

-- 5.1 Function Availability (v3.4: Using recursive CTE for inheritance)
CREATE TABLE function_availability (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    function_id INTEGER NOT NULL,           -- Function ID

    -- Product level (for generic functions)
    product_id INTEGER,                     -- NULL = SKILL Core (all products)

    -- Specific product release version (for version-specific functions)
    product_release_id INTEGER,             -- Specific product release version (IC618, ICADV618)

    -- Status (read from documentation or user-confirmed)
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'deprecated', 'removed')),

    -- Metadata
    notes TEXT,

    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (product_release_id) REFERENCES product_releases(id),

    -- Unique constraint: One record per function per product/version
    UNIQUE(function_id, product_id, product_release_id),

    CHECK (
        -- Scenario 1: SKILL Core generic function (all products/versions)
        (product_id IS NULL AND product_release_id IS NULL) OR
        -- Scenario 2: Product-level function (e.g., Virtuoso family)
        (product_id IS NOT NULL AND product_release_id IS NULL) OR
        -- Scenario 3: Version-specific function (e.g., ICADV 6.1.8)
        (product_id IS NULL AND product_release_id IS NOT NULL) OR
        -- Scenario 4: Product-level with specific version
        (product_id IS NOT NULL AND product_release_id IS NOT NULL)
    )
);

CREATE INDEX idx_availability_function ON function_availability(function_id);
CREATE INDEX idx_availability_product ON function_availability(product_id);
CREATE INDEX idx_availability_release ON function_availability(product_release_id);
CREATE INDEX idx_availability_status ON function_availability(status);

-- ============================================================================
-- End of Schema Definition
-- ============================================================================

-- Summary:
-- Total Tables: 15
-- - Core: data_types, products (2)
-- - Version: versions, product_releases (2)
-- - Document: documents, categories (2)
-- - Function: functions, function_details, function_categories, function_aliases,
--             function_syntax, function_arguments, function_return_values,
--             function_examples, function_sources (9)
-- - Availability: function_availability (1)
--
-- Key Features:
-- - Single inheritance mechanism using products.parent_product_id
-- - Multi-version function management (function_details, function_syntax)
-- - No timestamp fields (removed in v3.5)
-- - Simplified parameter types (parameter_type INTEGER)
-- - Split syntax (syntax_string + return_syntax)
-- - CHECK constraints for data consistency
