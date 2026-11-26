/**
 * SKILL Function JSON Schema Definitions
 *
 * This file defines TypeScript interfaces for SKILL function JSON formats
 * to support automated review and validation.
 */

/**
 * Legacy format (awvAppendList.json style)
 */
export interface LegacyFunctionDefinition {
  function_name: string;
  category: string;
  syntax: string;
  description: string;
  arguments: LegacyArgument[];
  return_value: LegacyReturnValue[];
  examples: any[];
  notes: string | null;
  page_numbers: string;
  document_title: string;
  source_images: string[];
}

export interface LegacyArgument {
  name: string;
  type: string | null;
  description: string;
}

export interface LegacyReturnValue {
  type: string;
  description: string;
}

/**
 * New format (append.json style)
 */
export interface ModernFunctionDefinition {
  function_name: string;
  category: string;
  category_hierarchy: string[];
  primary_syntax: PrimarySyntax;
  overloads: Overload[];
  description: string;
  notes: string | null;
  examples: Example[];
  aliases: string[];
  availability: Availability;
  sources: Sources;
  metadata: Metadata;
}

export interface PrimarySyntax {
  syntax_string: string;
  return_syntax: string;
  description: string;
  arguments: Argument[];
  return_values: ReturnValue[];
}

export interface Argument {
  name: string;
  type_prefix: string;
  type_description: string;
  description: string;
  parameter_type: number; // 0=required, 1=optional, 2=variadic, 3=keyword
  position: number;
  is_keyword: boolean;
  default_value: string | null;
}

export interface ReturnValue {
  type_name: string;
  type_prefix: string;
  type_description: string;
  description: string;
  position: number;
}

export interface Overload {
  syntax_string: string;
  return_syntax: string;
  description: string;
  arguments: Argument[];
  return_values: ReturnValue[];
}

export interface Example {
  code: string;
  description: string;
  position: number;
}

export interface Availability {
  product_code: string;
  product_release_id: string | null;
  status: string;
}

export interface Sources {
  source_file: string;
  source_images: string[];
  start_page: string;
  end_page: string;
}

export interface Metadata {
  verified: boolean;
  extraction_confidence: number;
  needs_review: boolean;
  parser_version: string;
}

/**
 * Unified function definition (supports both formats)
 */
export type FunctionDefinition = LegacyFunctionDefinition | ModernFunctionDefinition;

/**
 * Function review result
 */
export interface FunctionReviewResult {
  function_name: string;
  format: 'legacy' | 'modern';
  validation: ValidationResult;
  quality_score: QualityScore;
  suggestions: Suggestion[];
  ai_analysis?: string;
  timestamp: string;
}

export interface ValidationResult {
  is_valid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface ValidationError {
  field: string;
  message: string;
  severity: 'error' | 'critical';
}

export interface ValidationWarning {
  field: string;
  message: string;
  severity: 'warning' | 'info';
}

export interface QualityScore {
  overall: number; // 0-100
  documentation: number; // 0-100
  completeness: number; // 0-100
  clarity: number; // 0-100
  examples: number; // 0-100
}

export interface Suggestion {
  category: 'documentation' | 'syntax' | 'examples' | 'metadata' | 'structure';
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  current_value?: string;
  suggested_value?: string;
}

/**
 * Review configuration
 */
export interface ReviewConfig {
  enableAI: boolean;
  aiProvider: 'openai' | 'gemini';
  strictMode: boolean;
  checkExamples: boolean;
  checkTypeConsistency: boolean;
  generateSuggestions: boolean;
  outputFormat: 'json' | 'markdown' | 'html';
}

/**
 * Type guards
 */
export function isLegacyFormat(def: FunctionDefinition): def is LegacyFunctionDefinition {
  return 'syntax' in def && !('primary_syntax' in def);
}

export function isModernFormat(def: FunctionDefinition): def is ModernFunctionDefinition {
  return 'primary_syntax' in def;
}
