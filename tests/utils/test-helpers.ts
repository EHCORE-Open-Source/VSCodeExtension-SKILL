/**
 * Test Helper Functions
 *
 * Utility functions for creating test data and simplifying test code.
 */

import {
  FunctionDefinition,
  LegacyFunctionDefinition,
  ModernFunctionDefinition,
  Argument,
  PrimarySyntax
} from './function-review-types';

/**
 * Create a minimal modern function definition for testing
 */
export function createModernFunction(
  partial: Partial<ModernFunctionDefinition>
): ModernFunctionDefinition {
  const defaults: ModernFunctionDefinition = {
    function_name: 'testFunction',
    category: 'Test',
    category_hierarchy: ['Test'],
    primary_syntax: {
      syntax_string: 'testFunction()',
      return_syntax: 'nil',
      description: 'Test function',
      arguments: [],
      return_values: []
    },
    overloads: [],
    description: 'Test function description',
    notes: null,
    examples: [],
    aliases: [],
    availability: {
      product_code: 'SKILL',
      product_release_id: null,
      status: 'active'
    },
    sources: {
      source_file: 'test.pdf',
      source_images: [],
      start_page: '1',
      end_page: '1'
    },
    metadata: {
      verified: false,
      extraction_confidence: 1.0,
      needs_review: false,
      parser_version: '1.0'
    }
  };

  return {
    ...defaults,
    ...partial,
    primary_syntax: {
      ...defaults.primary_syntax,
      ...(partial.primary_syntax || {})
    },
    availability: {
      ...defaults.availability,
      ...(partial.availability || {})
    },
    sources: {
      ...defaults.sources,
      ...(partial.sources || {})
    },
    metadata: {
      ...defaults.metadata,
      ...(partial.metadata || {})
    }
  };
}

/**
 * Create a minimal legacy function definition for testing
 */
export function createLegacyFunction(
  partial: Partial<LegacyFunctionDefinition>
): LegacyFunctionDefinition {
  const defaults: LegacyFunctionDefinition = {
    function_name: 'testFunction',
    category: 'Test',
    syntax: 'testFunction()',
    description: 'Test function description',
    arguments: [],
    return_value: [],
    examples: [],
    notes: null,
    page_numbers: '1',
    document_title: 'Test Manual',
    source_images: []
  };

  return {
    ...defaults,
    ...partial
  };
}

/**
 * Create a test argument
 */
export function createArgument(
  partial: Partial<Argument>
): Argument {
  const defaults: Argument = {
    name: 'arg1',
    type_prefix: 'g',
    type_description: 'general',
    description: 'Test argument',
    parameter_type: 0, // required
    position: 0,
    is_keyword: false,
    default_value: null
  };

  return {
    ...defaults,
    ...partial
  };
}
