/**
 * Compatibility engine for SKILL multi-tool, multi-version support.
 * Handles procedure scope classification and version compatibility checking.
 * 
 * STRICT REQUIREMENT: All code, comments, and documentation must be in English only.
 */

import { 
    ProcedureScope, 
    ToolType, 
    CompatibilityMode,
    BuiltinProcedureInfo, 
    BuiltinProcedureDatabase,
    SkillConfig, 
    CompatibilityResult, 
    VersionSuggestion,
    AvailabilityRule
} from './types';
import { VersionMatcher } from './version-matcher';

export class CompatibilityEngine {
    private versionMatcher: VersionMatcher;
    private builtinDatabase: BuiltinProcedureDatabase | null = null;

    constructor() {
        this.versionMatcher = new VersionMatcher();
    }

    /**
     * Load the builtin procedures database
     */
    async loadBuiltinDatabase(database: BuiltinProcedureDatabase): Promise<void> {
        this.builtinDatabase = database;
    }

    /**
     * Check if a procedure name refers to a universal (built-in) procedure
     */
    isUniversalProcedure(procedureName: string): boolean {
        if (!this.builtinDatabase) {
            return false;
        }

        const procedure = this.builtinDatabase.procedures[procedureName];
        return procedure?.scope === ProcedureScope.UNIVERSAL;
    }

    /**
     * Check if a procedure is available in the current tool configuration
     */
    isToolCompatible(procedureName: string, toolType: ToolType): boolean {
        if (!this.builtinDatabase) {
            return false;
        }

        const procedure = this.builtinDatabase.procedures[procedureName];
        if (!procedure) {
            return false;
        }

        // Universal procedures are compatible with all tools
        if (procedure.scope === ProcedureScope.UNIVERSAL) {
            return true;
        }

        // Check tool-specific compatibility
        return procedure.availability.some(rule => 
            rule.scope === toolType as unknown as ProcedureScope || 
            rule.scope === ProcedureScope.CROSS_TOOL
        );
    }

    /**
     * Check comprehensive procedure compatibility against user configuration
     */
    checkProcedureCompatibility(
        procedureName: string,
        userConfig: SkillConfig
    ): CompatibilityResult {
        // Check if procedure exists in builtin database
        if (!this.builtinDatabase) {
            return {
                status: 'error',
                severity: 'error',
                message: 'Builtin procedure database not loaded',
                scope: ProcedureScope.UNIVERSAL
            };
        }

        const procedure = this.builtinDatabase.procedures[procedureName];
        if (!procedure) {
            // Not a builtin procedure - might be user-defined
            return {
                status: 'compatible',
                severity: 'info',
                message: 'User-defined procedure (not validated)',
                scope: ProcedureScope.UNIVERSAL
            };
        }

        // Universal procedures are always compatible
        if (procedure.scope === ProcedureScope.UNIVERSAL) {
            return {
                status: 'compatible',
                severity: 'info',
                message: 'Universal procedure - compatible with all tools and versions',
                scope: ProcedureScope.UNIVERSAL
            };
        }

        // Check tool compatibility
        const toolCompatibility = this.checkToolCompatibility(procedure, userConfig);
        if (toolCompatibility.status !== 'compatible') {
            return toolCompatibility;
        }

        // Check version compatibility
        const versionCompatibility = this.checkVersionCompatibility(procedure, userConfig);
        if (versionCompatibility.status !== 'compatible') {
            return versionCompatibility;
        }

        // Check strict mode restrictions
        const strictModeCheck = this.checkStrictModeCompliance(procedure, userConfig);
        if (strictModeCheck.status !== 'compatible') {
            return strictModeCheck;
        }

        return {
            status: 'compatible',
            severity: 'info',
            message: `Compatible with ${userConfig.environment.primary_tool}`,
            scope: procedure.scope
        };
    }

    /**
     * Check tool-specific compatibility
     */
    private checkToolCompatibility(
        procedure: BuiltinProcedureInfo,
        userConfig: SkillConfig
    ): CompatibilityResult {
        const primaryTool = userConfig.environment.primary_tool;
        
        // Check if procedure is available for the primary tool
        const compatibleRules = procedure.availability.filter(rule => 
            rule.scope === primaryTool as unknown as ProcedureScope || 
            rule.scope === ProcedureScope.CROSS_TOOL ||
            rule.scope === ProcedureScope.UNIVERSAL
        );

        if (compatibleRules.length === 0) {
            const availableTools = procedure.availability
                .map(rule => rule.scope)
                .filter(scope => scope !== ProcedureScope.UNIVERSAL);

            return {
                status: 'error',
                severity: 'error',
                message: `Procedure '${procedure.name}' is not available in ${primaryTool}`,
                suggestions: [
                    `Available in: ${availableTools.join(', ')}`,
                    `Switch tool configuration to use this procedure`
                ],
                scope: procedure.scope
            };
        }

        return {
            status: 'compatible',
            severity: 'info',
            message: 'Compatible',
            scope: procedure.scope
        };
    }

    /**
     * Check version compatibility for the procedure
     */
    private checkVersionCompatibility(
        procedure: BuiltinProcedureInfo,
        userConfig: SkillConfig
    ): CompatibilityResult {
        const primaryTool = userConfig.environment.primary_tool;
        const toolConfig = userConfig.environment.tools[primaryTool];
        
        if (!toolConfig) {
            return {
                status: 'error',
                severity: 'error',
                message: `No configuration found for tool ${primaryTool}`,
                scope: procedure.scope
            };
        }

        // Find applicable availability rules for the current tool
        const applicableRules = procedure.availability.filter(rule => 
            rule.scope === primaryTool as unknown as ProcedureScope || 
            rule.scope === ProcedureScope.CROSS_TOOL ||
            rule.scope === ProcedureScope.UNIVERSAL
        );

        // Check if any rule matches the current version
        for (const rule of applicableRules) {
            if (this.versionMatcher.isVersionInRange(toolConfig.version, rule.version_range)) {
                return {
            status: 'compatible',
            severity: 'info',
            message: 'Compatible',
            scope: procedure.scope
        };
            }
        }

        // No compatible version found
        const suggestions = this.generateVersionSuggestions(procedure, userConfig);
        
        return {
            status: 'warning',
            severity: 'warning',
            message: `Procedure '${procedure.name}' may not be compatible with ${primaryTool} ${toolConfig.version}`,
            suggestions: suggestions.map(s => s.description),
            scope: procedure.scope
        };
    }

    /**
     * Check strict mode compliance
     */
    private checkStrictModeCompliance(
        procedure: BuiltinProcedureInfo,
        userConfig: SkillConfig
    ): CompatibilityResult {
        const compatibilityConfig = userConfig.compatibility;

        // Universal procedures are always allowed
        if (procedure.scope === ProcedureScope.UNIVERSAL) {
            return {
            status: 'compatible',
            severity: 'info',
            message: 'Compatible',
            scope: procedure.scope
        };
        }

        // Check strict mode restrictions
        if (compatibilityConfig.mode === CompatibilityMode.STRICT) {
            if (procedure.scope === ProcedureScope.CROSS_TOOL && !compatibilityConfig.allow_cross_tool) {
                return {
                    status: 'warning',
                    severity: 'warning',
                    message: 'Cross-tool procedures not allowed in strict mode',
                    suggestions: ['Enable allow_cross_tool in configuration', 'Use tool-specific alternatives'],
                    scope: procedure.scope
                };
            }
        }

        // Universal-only mode
        if (compatibilityConfig.mode === CompatibilityMode.UNIVERSAL) {
            return {
                status: 'error',
                severity: 'error',
                message: 'Only universal procedures allowed in universal mode',
                suggestions: ['Switch to permissive or strict mode', 'Use universal alternatives'],
                scope: procedure.scope
            };
        }

        return {
            status: 'compatible',
            severity: 'info',
            message: 'Compatible',
            scope: procedure.scope
        };
    }

    /**
     * Generate version upgrade/downgrade suggestions
     */
    generateVersionSuggestions(
        procedure: BuiltinProcedureInfo,
        userConfig: SkillConfig
    ): VersionSuggestion[] {
        const suggestions: VersionSuggestion[] = [];
        const primaryTool = userConfig.environment.primary_tool;
        const currentVersion = userConfig.environment.tools[primaryTool]?.version;

        if (!currentVersion) {
            return suggestions;
        }

        // Find minimum compatible version
        const minCompatibleVersion = this.findMinimumCompatibleVersion(procedure, primaryTool);
        if (minCompatibleVersion && this.versionMatcher.compareVersions(currentVersion, minCompatibleVersion) < 0) {
            suggestions.push({
                type: 'upgrade',
                title: `Upgrade to ${minCompatibleVersion}`,
                description: `This procedure requires ${primaryTool} ${minCompatibleVersion} or later`,
                target_version: minCompatibleVersion,
                compatibility_scope: procedure.scope,
                effort: 'medium'
            });
        }

        // Look for universal alternatives
        const universalAlternative = this.findUniversalAlternative(procedure.name);
        if (universalAlternative) {
            suggestions.push({
                type: 'universal',
                title: `Use universal function: ${universalAlternative}`,
                description: 'Works across all tools and versions',
                alternative_procedure: universalAlternative,
                compatibility_scope: 'universal',
                effort: 'low'
            });
        }

        return suggestions;
    }

    /**
     * Find the minimum version that supports this procedure for a given tool
     */
    private findMinimumCompatibleVersion(procedure: BuiltinProcedureInfo, tool: ToolType): string | null {
        const applicableRules = procedure.availability.filter(rule => 
            rule.scope === tool as unknown as ProcedureScope || rule.scope === ProcedureScope.CROSS_TOOL
        );

        let minVersion: string | null = null;

        for (const rule of applicableRules) {
            if (rule.version_range.min_version) {
                if (!minVersion || this.versionMatcher.compareVersions(rule.version_range.min_version, minVersion) < 0) {
                    minVersion = rule.version_range.min_version;
                }
            }
        }

        return minVersion;
    }

    /**
     * Find a universal alternative for a tool-specific procedure
     */
    private findUniversalAlternative(procedureName: string): string | null {
        if (!this.builtinDatabase) {
            return null;
        }

        // Simple mapping for common cases - this could be expanded with a proper mapping database
        const alternativeMap: { [key: string]: string } = {
            'leCreatePath': 'printf', // Example mapping - replace with actual alternatives
            // Add more mappings as needed
        };

        return alternativeMap[procedureName] || null;
    }

    /**
     * Get detailed information about a builtin procedure
     */
    getProcedureInfo(procedureName: string): BuiltinProcedureInfo | null {
        if (!this.builtinDatabase) {
            return null;
        }

        return this.builtinDatabase.procedures[procedureName] || null;
    }

    /**
     * List all procedures available for a specific tool and version
     */
    getAvailableProcedures(toolType: ToolType, version: string): string[] {
        if (!this.builtinDatabase) {
            return [];
        }

        const availableProcedures: string[] = [];

        for (const [name, procedure] of Object.entries(this.builtinDatabase.procedures)) {
            // Universal procedures are always available
            if (procedure.scope === ProcedureScope.UNIVERSAL) {
                availableProcedures.push(name);
                continue;
            }

            // Check tool-specific availability
            const isCompatible = procedure.availability.some(rule => {
                const toolMatches = rule.scope === toolType as unknown as ProcedureScope || rule.scope === ProcedureScope.CROSS_TOOL;
                const versionMatches = this.versionMatcher.isVersionInRange(version, rule.version_range);
                return toolMatches && versionMatches;
            });

            if (isCompatible) {
                availableProcedures.push(name);
            }
        }

        return availableProcedures.sort();
    }

    /**
     * Get compatibility statistics for a tool configuration
     */
    getCompatibilityStats(userConfig: SkillConfig): {
        total: number;
        compatible: number;
        warnings: number;
        errors: number;
        by_scope: { [key in ProcedureScope]: number };
    } {
        if (!this.builtinDatabase) {
            return {
                total: 0,
                compatible: 0,
                warnings: 0,
                errors: 0,
                by_scope: {
                    [ProcedureScope.UNIVERSAL]: 0,
                    [ProcedureScope.VIRTUOSO]: 0,
                    [ProcedureScope.ALLEGRO]: 0,
                    [ProcedureScope.CROSS_TOOL]: 0
                }
            };
        }

        const stats = {
            total: 0,
            compatible: 0,
            warnings: 0,
            errors: 0,
            by_scope: {
                [ProcedureScope.UNIVERSAL]: 0,
                [ProcedureScope.VIRTUOSO]: 0,
                [ProcedureScope.ALLEGRO]: 0,
                [ProcedureScope.CROSS_TOOL]: 0
            }
        };

        for (const [name, procedure] of Object.entries(this.builtinDatabase.procedures)) {
            stats.total++;
            stats.by_scope[procedure.scope]++;

            const compatibility = this.checkProcedureCompatibility(name, userConfig);
            switch (compatibility.status) {
                case 'compatible':
                    stats.compatible++;
                    break;
                case 'warning':
                    stats.warnings++;
                    break;
                case 'error':
                    stats.errors++;
                    break;
            }
        }

        return stats;
    }

    /**
     * Public wrapper for version comparison
     */
    compareVersions(v1: string, v2: string): number {
        return this.versionMatcher.compareVersions(v1, v2);
    }
}