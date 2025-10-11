import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { createFunctionReviewer } from '../utils/function-reviewer';
import type { FunctionDefinition, FunctionReviewResult } from '../utils/function-review-types';

/**
 * Test Suite: SKILL Function Review System
 *
 * This test suite validates the automated function review system
 * for SKILL function JSON definitions.
 */

test.describe('Function Reviewer Tests', () => {
  let reviewer;
  const testDataDir = path.join(process.cwd(), 'test-data');
  const testOutputDir = path.join(process.cwd(), 'test-results', 'function-reviews');

  test.beforeAll(async () => {
    // Create test output directory
    if (!fs.existsSync(testOutputDir)) {
      fs.mkdirSync(testOutputDir, { recursive: true });
    }
  });

  test.beforeEach(async () => {
    reviewer = createFunctionReviewer({
      enableAI: false, // Disable AI for faster tests
      strictMode: false,
      checkExamples: true,
      generateSuggestions: true
    });
  });

  test('should review legacy format function (awvAppendList)', async () => {
    const filePath = 'awvAppendList.json';

    if (!fs.existsSync(filePath)) {
      test.skip();
      return;
    }

    const result = await reviewer.reviewFunctionFile(filePath);

    expect(result.function_name).toBe('awvAppendList');
    expect(result.format).toBe('legacy');
    expect(result.validation).toBeDefined();
    expect(result.quality_score).toBeDefined();

    // Validation should pass
    expect(result.validation.is_valid).toBe(true);

    // Should have some quality score
    expect(result.quality_score.overall).toBeGreaterThan(0);
    expect(result.quality_score.overall).toBeLessThanOrEqual(100);

    // Save result
    const outputPath = path.join(testOutputDir, 'awvAppendList-review.json');
    reviewer.saveResult(result, outputPath);

    expect(fs.existsSync(outputPath)).toBe(true);
  });

  test('should review modern format function (append1)', async () => {
    const filePath = 'test_output/append.json';

    if (!fs.existsSync(filePath)) {
      test.skip();
      return;
    }

    const result = await reviewer.reviewFunctionFile(filePath);

    expect(result.function_name).toBe('append1');
    expect(result.format).toBe('modern');
    expect(result.validation.is_valid).toBe(true);

    // Modern format should have good scores
    expect(result.quality_score.overall).toBeGreaterThan(50);

    // Should have primary syntax
    const content = fs.readFileSync(filePath, 'utf-8');
    const definition = JSON.parse(content);
    expect(definition.primary_syntax).toBeDefined();
    expect(definition.primary_syntax.arguments).toBeDefined();

    // Save as markdown
    const outputPath = path.join(testOutputDir, 'append1-review.md');
    reviewer.saveResult(result, outputPath);

    expect(fs.existsSync(outputPath)).toBe(true);

    // Verify markdown content
    const markdown = fs.readFileSync(outputPath, 'utf-8');
    expect(markdown).toContain('# Function Review: `append1`');
    expect(markdown).toContain('Quality Score');
    expect(markdown).toContain('Validation');
  });

  test('should detect validation errors for incomplete function', async () => {
    const incompleteFunction = {
      function_name: '', // Empty name - should error
      category: 'Test',
      description: '', // Empty description - should error
      primary_syntax: null
    };

    const result = await reviewer.reviewFunction(incompleteFunction);

    expect(result.validation.is_valid).toBe(false);
    expect(result.validation.errors.length).toBeGreaterThan(0);

    // Should have critical error for missing function name
    const criticalErrors = result.validation.errors.filter(
      e => e.severity === 'critical'
    );
    expect(criticalErrors.length).toBeGreaterThan(0);
  });

  test('should detect warnings for uncategorized function', async () => {
    const uncategorizedFunction = {
      function_name: 'testFunc',
      category: 'Uncategorized',
      description: 'A test function',
      primary_syntax: {
        syntax_string: 'testFunc()',
        return_syntax: 'nil',
        description: 'Test',
        arguments: [],
        return_values: []
      }
    };

    const result = await reviewer.reviewFunction(uncategorizedFunction);

    expect(result.validation.warnings.length).toBeGreaterThan(0);

    const categoryWarning = result.validation.warnings.find(
      w => w.field === 'category'
    );
    expect(categoryWarning).toBeDefined();
  });

  test('should calculate quality scores correctly', async () => {
    const wellDocumentedFunction = {
      function_name: 'testFunc',
      category: 'Test Functions',
      description: 'This is a well-documented test function with a comprehensive description that explains what it does, how to use it, and what to expect. It provides clear guidance for developers.',
      notes: 'Additional implementation notes',
      primary_syntax: {
        syntax_string: 'testFunc( l_list x_count )',
        return_syntax: 't/nil',
        description: 'Detailed syntax description',
        arguments: [
          {
            name: 'l_list',
            type_prefix: 'l',
            type_description: 'list',
            description: 'Input list parameter with detailed explanation',
            parameter_type: 0,
            position: 0,
            is_keyword: false,
            default_value: null
          }
        ],
        return_values: [
          {
            type_name: 't/nil',
            type_prefix: 't',
            type_description: 'boolean',
            description: 'Returns true on success',
            position: 0
          }
        ]
      },
      examples: [
        {
          code: 'testFunc(list(1 2 3) 5)',
          description: 'Basic usage example',
          position: 0
        }
      ],
      sources: {
        source_file: 'test.pdf',
        source_images: [],
        start_page: '1',
        end_page: '1'
      },
      metadata: {
        verified: true,
        extraction_confidence: 0.95,
        needs_review: false,
        parser_version: '1.0'
      }
    };

    const result = await reviewer.reviewFunction(wellDocumentedFunction);

    // Well-documented function should have high scores
    expect(result.quality_score.overall).toBeGreaterThan(70);
    expect(result.quality_score.documentation).toBeGreaterThan(70);
    expect(result.quality_score.completeness).toBeGreaterThan(80);
    expect(result.quality_score.examples).toBeGreaterThan(0);
  });

  test('should generate relevant suggestions', async () => {
    const needsImprovementFunction = {
      function_name: 'poorFunc',
      category: 'Uncategorized',
      description: 'Short desc', // Too short
      primary_syntax: {
        syntax_string: 'poorFunc()',
        return_syntax: 'nil',
        description: 'Test',
        arguments: [],
        return_values: []
      },
      examples: [] // No examples
    };

    const result = await reviewer.reviewFunction(needsImprovementFunction);

    expect(result.suggestions.length).toBeGreaterThan(0);

    // Should suggest categorization
    const categorySuggestion = result.suggestions.find(
      s => s.category === 'metadata' && s.title.includes('Categorize')
    );
    expect(categorySuggestion).toBeDefined();

    // Should suggest adding examples
    const exampleSuggestion = result.suggestions.find(
      s => s.category === 'examples'
    );
    expect(exampleSuggestion).toBeDefined();

    // Should suggest expanding description
    const descSuggestion = result.suggestions.find(
      s => s.title.includes('description')
    );
    expect(descSuggestion).toBeDefined();
  });

  test('should format review as markdown correctly', async () => {
    const testFunction = {
      function_name: 'markdownTest',
      category: 'Test',
      description: 'Test function for markdown formatting',
      primary_syntax: {
        syntax_string: 'markdownTest()',
        return_syntax: 'nil',
        description: 'Test',
        arguments: [],
        return_values: []
      }
    };

    const result = await reviewer.reviewFunction(testFunction);
    const markdown = reviewer.formatAsMarkdown(result);

    expect(markdown).toContain('# Function Review: `markdownTest`');
    expect(markdown).toContain('## 📊 Quality Score');
    expect(markdown).toContain('## ✓ Validation');
    expect(markdown).toContain('**Status**:');

    // Should have quality score table
    expect(markdown).toMatch(/\| Metric \| Score \|/);
    expect(markdown).toMatch(/Overall.*\/100/);

    // Should have progress bar
    expect(markdown).toMatch(/[🟢🟡🔴]/);
  });

  test('should handle batch review of multiple functions', async () => {
    const functions = [
      {
        function_name: 'func1',
        category: 'Test',
        description: 'First test function',
        syntax: 'func1()'
      },
      {
        function_name: 'func2',
        category: 'Test',
        description: 'Second test function',
        primary_syntax: {
          syntax_string: 'func2()',
          return_syntax: 'nil',
          description: 'Test',
          arguments: [],
          return_values: []
        }
      }
    ];

    const results = [];

    for (const func of functions) {
      const result = await reviewer.reviewFunction(func);
      results.push(result);
    }

    expect(results.length).toBe(2);
    expect(results[0].function_name).toBe('func1');
    expect(results[1].function_name).toBe('func2');
    expect(results[0].format).toBe('legacy');
    expect(results[1].format).toBe('modern');
  });

  test('should validate argument type consistency', async () => {
    const reviewerStrict = createFunctionReviewer({
      enableAI: false,
      checkTypeConsistency: true
    });

    const inconsistentFunction = {
      function_name: 'inconsistentFunc',
      category: 'Test',
      description: 'Function with inconsistent types',
      primary_syntax: {
        syntax_string: 'inconsistentFunc( x_value )',
        return_syntax: 'nil',
        description: 'Test',
        arguments: [
          {
            name: 'x_value',
            type_prefix: 'l', // Wrong! Should be 'x'
            type_description: 'list',
            description: 'A value',
            parameter_type: 0,
            position: 0,
            is_keyword: false,
            default_value: null
          }
        ],
        return_values: []
      }
    };

    const result = await reviewerStrict.reviewFunction(inconsistentFunction);

    // Should have type consistency warning
    const typeWarning = result.validation.warnings.find(
      w => w.field.includes('type_prefix')
    );
    expect(typeWarning).toBeDefined();
  });

  test('should save results in different formats', async () => {
    const testFunction = {
      function_name: 'formatTest',
      category: 'Test',
      description: 'Testing output formats',
      syntax: 'formatTest()'
    };

    const result = await reviewer.reviewFunction(testFunction);

    // Save as JSON
    const jsonPath = path.join(testOutputDir, 'format-test.json');
    reviewer.saveResult(result, jsonPath);
    expect(fs.existsSync(jsonPath)).toBe(true);

    const jsonContent = JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));
    expect(jsonContent.function_name).toBe('formatTest');

    // Save as Markdown
    const mdPath = path.join(testOutputDir, 'format-test.md');
    reviewer.saveResult(result, mdPath);
    expect(fs.existsSync(mdPath)).toBe(true);

    const mdContent = fs.readFileSync(mdPath, 'utf-8');
    expect(mdContent).toContain('# Function Review');
  });
});

/**
 * Integration Tests with Real Files
 */
test.describe('Real Function File Reviews', () => {
  test('should review all JSON files in functions directory', async ({ skip }) => {
    const functionsDir = 'functions';

    if (!fs.existsSync(functionsDir)) {
      skip();
      return;
    }

    const files = fs.readdirSync(functionsDir)
      .filter(f => f.endsWith('.json'))
      .slice(0, 5); // Limit to 5 files for testing

    if (files.length === 0) {
      skip();
      return;
    }

    const reviewer = createFunctionReviewer({
      enableAI: false,
      checkExamples: true
    });

    const results = [];

    for (const file of files) {
      const filePath = path.join(functionsDir, file);
      const result = await reviewer.reviewFunctionFile(filePath);
      results.push(result);

      console.log(`✓ Reviewed: ${result.function_name} (Score: ${result.quality_score.overall}/100)`);
    }

    expect(results.length).toBeGreaterThan(0);

    // Generate summary report
    const avgScore = results.reduce((sum, r) => sum + r.quality_score.overall, 0) / results.length;
    const validCount = results.filter(r => r.validation.is_valid).length;

    console.log(`\n📊 Summary:`);
    console.log(`   Total reviewed: ${results.length}`);
    console.log(`   Valid: ${validCount}/${results.length}`);
    console.log(`   Average score: ${avgScore.toFixed(1)}/100`);

    expect(avgScore).toBeGreaterThan(0);
  });
});
