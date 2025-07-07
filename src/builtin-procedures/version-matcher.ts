/**
 * Version pattern matching system for SKILL procedures.
 * Supports various version patterns like *, 6.*, 6.0.0~6.1.8, >=22.1, etc.
 * 
 * STRICT REQUIREMENT: All code, comments, and documentation must be in English only.
 */

import { VersionRange } from './types';

export class VersionMatcher {
    /**
     * Parse a version pattern string into a structured VersionRange object.
     * Supported patterns:
     * - "*" -> All versions
     * - "6.*" -> All 6.x versions  
     * - "6.0.*" -> All 6.0.x versions
     * - "6.0.0~6.1.8" -> Range from 6.0.0 to 6.1.8
     * - ">=22.1" -> Minimum version 22.1
     * - "<=23.1" -> Maximum version 23.1
     * - "22.1,23.1" -> Specific version list
     */
    parseVersionPattern(pattern: string): VersionRange {
        const trimmedPattern = pattern.trim();
        
        // Universal pattern: *
        if (trimmedPattern === '*') {
            return {
                pattern: trimmedPattern,
                description: 'All versions supported'
            };
        }
        
        // Wildcard patterns: 6.*, 6.0.*, etc.
        if (trimmedPattern.includes('*')) {
            return this.parseWildcardPattern(trimmedPattern);
        }
        
        // Range patterns: 6.0.0~6.1.8
        if (trimmedPattern.includes('~')) {
            return this.parseRangePattern(trimmedPattern);
        }
        
        // Comparison patterns: >=22.1, <=23.1, >22.1, <23.1
        if (/^[><]=?/.test(trimmedPattern)) {
            return this.parseComparisonPattern(trimmedPattern);
        }
        
        // List patterns: 22.1,23.1,24.0
        if (trimmedPattern.includes(',')) {
            return this.parseListPattern(trimmedPattern);
        }
        
        // Single version: 22.1
        return this.parseSingleVersion(trimmedPattern);
    }

    /**
     * Check if a given version matches the version range.
     */
    isVersionInRange(version: string, range: VersionRange): boolean {
        const normalizedVersion = this.normalizeVersion(version);
        
        // Universal pattern always matches
        if (range.pattern === '*') {
            return true;
        }
        
        // Wildcard pattern matching
        if (range.pattern.includes('*')) {
            return this.matchWildcardPattern(normalizedVersion, range);
        }
        
        // Range pattern matching
        if (range.min_version || range.max_version) {
            return this.matchRangePattern(normalizedVersion, range);
        }
        
        // Exact version matching
        return normalizedVersion === this.normalizeVersion(range.pattern);
    }

    /**
     * Parse wildcard patterns like 6.*, 6.0.*, etc.
     */
    private parseWildcardPattern(pattern: string): VersionRange {
        const parts = pattern.split('.');
        const nonWildcardParts = parts.filter(part => part !== '*');
        
        return {
            pattern,
            description: `All ${nonWildcardParts.join('.')}.x versions`
        };
    }

    /**
     * Parse range patterns like 6.0.0~6.1.8
     */
    private parseRangePattern(pattern: string): VersionRange {
        const [minVersion, maxVersion] = pattern.split('~').map(v => v.trim());
        
        return {
            pattern,
            min_version: minVersion,
            max_version: maxVersion,
            inclusive_min: true,
            inclusive_max: true,
            description: `Versions from ${minVersion} to ${maxVersion}`
        };
    }

    /**
     * Parse comparison patterns like >=22.1, <=23.1
     */
    private parseComparisonPattern(pattern: string): VersionRange {
        const match = pattern.match(/^([><]=?)(.+)$/);
        if (!match) {
            throw new Error(`Invalid comparison pattern: ${pattern}`);
        }
        
        const [, operator, version] = match;
        const result: VersionRange = { pattern };
        
        switch (operator) {
            case '>=':
                result.min_version = version;
                result.inclusive_min = true;
                result.description = `Version ${version} or later`;
                break;
            case '>':
                result.min_version = version;
                result.inclusive_min = false;
                result.description = `Version later than ${version}`;
                break;
            case '<=':
                result.max_version = version;
                result.inclusive_max = true;
                result.description = `Version ${version} or earlier`;
                break;
            case '<':
                result.max_version = version;
                result.inclusive_max = false;
                result.description = `Version earlier than ${version}`;
                break;
        }
        
        return result;
    }

    /**
     * Parse list patterns like 22.1,23.1,24.0
     */
    private parseListPattern(pattern: string): VersionRange {
        const versions = pattern.split(',').map(v => v.trim());
        
        return {
            pattern,
            description: `Specific versions: ${versions.join(', ')}`
        };
    }

    /**
     * Parse single version patterns like 22.1
     */
    private parseSingleVersion(pattern: string): VersionRange {
        return {
            pattern,
            description: `Version ${pattern} only`
        };
    }

    /**
     * Match version against wildcard pattern
     */
    private matchWildcardPattern(version: string, range: VersionRange): boolean {
        const patternParts = range.pattern.split('.');
        const versionParts = version.split('.');
        
        for (let i = 0; i < patternParts.length; i++) {
            if (patternParts[i] === '*') {
                return true; // Wildcard matches everything from this point
            }
            
            if (i >= versionParts.length || patternParts[i] !== versionParts[i]) {
                return false;
            }
        }
        
        return true;
    }

    /**
     * Match version against range pattern
     */
    private matchRangePattern(version: string, range: VersionRange): boolean {
        if (range.min_version) {
            const comparison = this.compareVersions(version, range.min_version);
            if (range.inclusive_min ? comparison < 0 : comparison <= 0) {
                return false;
            }
        }
        
        if (range.max_version) {
            const comparison = this.compareVersions(version, range.max_version);
            if (range.inclusive_max ? comparison > 0 : comparison >= 0) {
                return false;
            }
        }
        
        // Handle list patterns
        if (range.pattern.includes(',')) {
            const allowedVersions = range.pattern.split(',').map(v => v.trim());
            return allowedVersions.some(allowed => 
                this.normalizeVersion(version) === this.normalizeVersion(allowed)
            );
        }
        
        return true;
    }

    /**
     * Compare two version strings.
     * Returns: -1 if v1 < v2, 0 if v1 == v2, 1 if v1 > v2
     */
    compareVersions(v1: string, v2: string): number {
        const parts1 = this.normalizeVersion(v1).split('.').map(Number);
        const parts2 = this.normalizeVersion(v2).split('.').map(Number);
        
        const maxLength = Math.max(parts1.length, parts2.length);
        
        for (let i = 0; i < maxLength; i++) {
            const part1 = parts1[i] || 0;
            const part2 = parts2[i] || 0;
            
            if (part1 < part2) return -1;
            if (part1 > part2) return 1;
        }
        
        return 0;
    }

    /**
     * Normalize version string for consistent comparison
     */
    private normalizeVersion(version: string): string {
        // Remove common prefixes like 'v'
        const cleaned = version.replace(/^v/, '');
        
        // Split by dots and ensure we have at least 3 parts
        const parts = cleaned.split('.');
        while (parts.length < 3) {
            parts.push('0');
        }
        
        return parts.join('.');
    }

    /**
     * Get human-readable description of version compatibility
     */
    getCompatibilityDescription(version: string, range: VersionRange): string {
        if (this.isVersionInRange(version, range)) {
            return `✅ Compatible (${range.description || range.pattern})`;
        } else {
            return `❌ Not compatible (requires ${range.description || range.pattern})`;
        }
    }

    /**
     * Find the best matching version range for a given version
     */
    findBestMatch(version: string, ranges: VersionRange[]): VersionRange | null {
        const compatibleRanges = ranges.filter(range => 
            this.isVersionInRange(version, range)
        );
        
        if (compatibleRanges.length === 0) {
            return null;
        }
        
        // Prefer more specific patterns over wildcards
        return compatibleRanges.sort((a, b) => {
            if (a.pattern === '*') return 1;
            if (b.pattern === '*') return -1;
            return a.pattern.length - b.pattern.length;
        })[0];
    }
}