/**
 * TypeScript interfaces for the SKILL multi-tool, multi-version procedure system.
 * All interfaces support universal procedures, tool-specific procedures, and version ranges.
 * 
 * STRICT REQUIREMENT: All code, comments, and documentation must be in English only.
 */

export enum ProcedureScope {
    UNIVERSAL = 'universal',      // Universal commands (printf, car, cdr, etc.)
    VIRTUOSO = 'virtuoso',        // Virtuoso-specific procedures
    ALLEGRO = 'allegro',          // Allegro-specific procedures  
    CROSS_TOOL = 'cross-tool'     // Cross-tool but not universal procedures
}

export enum ToolType {
    VIRTUOSO = 'virtuoso',
    ALLEGRO = 'allegro'
}

export enum CompatibilityMode {
    STRICT = 'strict',            // Strict version checking
    PERMISSIVE = 'permissive',    // Allow some version mismatches
    UNIVERSAL = 'universal'       // Only allow universal procedures
}

export interface VersionRange {
    pattern: string;              // "6.0.0~6.1.8", "*", "6.*", ">=22.1"
    min_version?: string;         // Parsed minimum version
    max_version?: string;         // Parsed maximum version
    inclusive_min?: boolean;      // Include minimum version
    inclusive_max?: boolean;      // Include maximum version
    description?: string;         // Human-readable description
}

export interface AvailabilityRule {
    scope: ProcedureScope;
    version_range: VersionRange;
    subtool?: string;             // Specific subtool (layout, schematic, pcb, etc.)
    conditions?: string[];        // Additional conditions
    notes?: string;               // Version-specific notes
}

export interface ParameterInfo {
    name: string;
    type?: string;                // Parameter type if known
    required: boolean;            // Whether parameter is required
    default_value?: string;       // Default value if optional
    description: string;          // Parameter description
}

export interface VersionChange {
    version: string;
    type: 'added' | 'modified' | 'deprecated' | 'removed';
    description: string;
    breaking?: boolean;           // Whether this is a breaking change
}

export interface ProcedureDocumentation {
    syntax: string;               // Full syntax specification
    summary: string;              // Brief description
    parameters: ParameterInfo[];  // Parameter documentation
    return_value?: string;        // Return value description
    examples?: string[];          // Usage examples
    notes?: string;               // Important notes
    changes?: VersionChange[];    // Version change history
}

export interface BuiltinProcedureInfo {
    name: string;
    scope: ProcedureScope;
    availability: AvailabilityRule[];
    documentation: ProcedureDocumentation;
    category: string;             // Functional category
    source: string;               // Source documentation file
}

export interface BuiltinProcedureDatabase {
    metadata: {
        version: string;
        total_procedures: number;
        categories: string[];
        supported_tools: {
            [key in ToolType]: string[];  // Supported versions for each tool
        };
        last_updated: string;
    };
    procedures: {
        [procedureName: string]: BuiltinProcedureInfo;
    };
}

export interface ToolVersionInfo {
    version: string;
    version_range?: string;       // Supported version range
    subtools?: string[];          // Available subtools
}

export interface SkillToolConfig {
    primary_tool: ToolType;
    tools: {
        [key in ToolType]?: ToolVersionInfo;
    };
}

export interface CompatibilityConfig {
    mode: CompatibilityMode;
    allow_universal: boolean;     // Allow universal procedures
    allow_cross_tool: boolean;    // Allow cross-tool procedures
    show_version_warnings: boolean;
    show_scope_warnings: boolean;
    minimum_version?: string;     // Minimum supported version
}

export interface SkillConfig {
    auto_complete: boolean;
    search_folder_path: string;
    environment: SkillToolConfig;
    compatibility: CompatibilityConfig;
}

export interface CompatibilityResult {
    status: 'compatible' | 'warning' | 'error';
    severity: 'info' | 'warning' | 'error';
    message: string;
    suggestions?: string[];
    migration_path?: string[];
    scope: ProcedureScope;
}

export interface VersionSuggestion {
    type: 'upgrade' | 'downgrade' | 'alternative' | 'universal';
    title: string;
    description: string;
    target_version?: string;
    alternative_procedure?: string;
    compatibility_scope: string;
    effort: 'low' | 'medium' | 'high';
}

export interface ToolDetection {
    tool: ToolType;
    version?: string;
    path?: string;
    available: boolean;
    subtools?: string[];
}

export interface EnvironmentDetection {
    detected_tools: ToolDetection[];
    recommended_config: SkillConfig;
    warnings: string[];
}