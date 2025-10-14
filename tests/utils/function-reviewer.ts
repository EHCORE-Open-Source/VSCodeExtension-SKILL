/**
 * SKILL Function Reviewer
 *
 * Automated review system for SKILL function JSON definitions.
 * Supports both legacy and modern formats with AI-powered analysis.
 */

import * as fs from 'fs';
import * as path from 'path';
import {
  FunctionDefinition,
  LegacyFunctionDefinition,
  ModernFunctionDefinition,
  FunctionReviewResult,
  ValidationResult,
  ValidationError,
  ValidationWarning,
  QualityScore,
  Suggestion,
  ReviewConfig,
  isLegacyFormat,
  isModernFormat
} from './function-review-types';
import { AITestHelper, createAITestHelper } from './ai-test-helper';

export class FunctionReviewer {
  private ai?: AITestHelper;
  private config: ReviewConfig;

  constructor(config: Partial<ReviewConfig> = {}) {
    this.config = {
      enableAI: true,
      aiProvider: 'gemini',
      strictMode: false,
      checkExamples: true,
      checkTypeConsistency: true,
      generateSuggestions: true,
      outputFormat: 'json',
      ...config
    };

    if (this.config.enableAI) {
      this.ai = createAITestHelper(this.config.aiProvider);
    }
  }

  /**
   * Review a single function from JSON file
   */
  async reviewFunctionFile(filePath: string): Promise<FunctionReviewResult> {
    const content = fs.readFileSync(filePath, 'utf-8');
    const definition: FunctionDefinition = JSON.parse(content);

    return await this.reviewFunction(definition);
  }

  /**
   * Review a function definition object
   */
  async reviewFunction(definition: FunctionDefinition): Promise<FunctionReviewResult> {
    const format = isLegacyFormat(definition) ? 'legacy' : 'modern';

    console.log(`\n🔍 Reviewing function: ${definition.function_name}`);
    console.log(`📋 Format: ${format}`);

    // Perform validation
    const validation = this.validateFunction(definition);

    // Calculate quality scores
    const quality_score = this.calculateQualityScore(definition);

    // Generate suggestions
    const suggestions = this.generateSuggestions(definition, validation);

    // AI analysis (if enabled)
    let ai_analysis: string | undefined;
    if (this.ai && this.config.enableAI) {
      ai_analysis = await this.performAIAnalysis(definition);
    }

    const result: FunctionReviewResult = {
      function_name: definition.function_name,
      format,
      validation,
      quality_score,
      suggestions,
      ai_analysis,
      timestamp: new Date().toISOString()
    };

    return result;
  }

  /**
   * Validate function definition
   */
  private validateFunction(definition: FunctionDefinition): ValidationResult {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    // Basic required fields
    if (!definition.function_name || definition.function_name.trim() === '') {
      errors.push({
        field: 'function_name',
        message: 'Function name is required',
        severity: 'critical'
      });
    }

    if (!definition.description || definition.description.trim() === '') {
      errors.push({
        field: 'description',
        message: 'Description is required',
        severity: 'error'
      });
    }

    if (!definition.category || definition.category === 'Uncategorized') {
      warnings.push({
        field: 'category',
        message: 'Function should be categorized',
        severity: 'warning'
      });
    }

    // Format-specific validation
    if (isModernFormat(definition)) {
      this.validateModernFormat(definition, errors, warnings);
    } else if (isLegacyFormat(definition)) {
      this.validateLegacyFormat(definition, errors, warnings);
    }

    return {
      is_valid: errors.filter(e => e.severity === 'critical').length === 0,
      errors,
      warnings
    };
  }

  /**
   * Validate modern format
   */
  private validateModernFormat(
    definition: ModernFunctionDefinition,
    errors: ValidationError[],
    warnings: ValidationWarning[]
  ): void {
    // Check primary syntax
    if (!definition.primary_syntax) {
      errors.push({
        field: 'primary_syntax',
        message: 'Primary syntax definition is required',
        severity: 'critical'
      });
      return;
    }

    // Check syntax string format
    if (!definition.primary_syntax.syntax_string.includes(definition.function_name)) {
      warnings.push({
        field: 'primary_syntax.syntax_string',
        message: 'Syntax string should contain function name',
        severity: 'warning'
      });
    }

    // Check arguments
    if (!definition.primary_syntax.arguments || definition.primary_syntax.arguments.length === 0) {
      warnings.push({
        field: 'primary_syntax.arguments',
        message: 'No arguments defined (use empty array if function has no parameters)',
        severity: 'info'
      });
    } else {
      this.validateArguments(definition.primary_syntax.arguments, errors, warnings);
    }

    // Check return values
    if (!definition.primary_syntax.return_values || definition.primary_syntax.return_values.length === 0) {
      warnings.push({
        field: 'primary_syntax.return_values',
        message: 'No return values defined',
        severity: 'warning'
      });
    }

    // Check examples
    if (this.config.checkExamples) {
      if (!definition.examples || definition.examples.length === 0) {
        warnings.push({
          field: 'examples',
          message: 'No examples provided',
          severity: 'warning'
        });
      } else {
        this.validateExamples(definition.examples, definition.function_name, warnings);
      }
    }

    // Check metadata
    if (!definition.metadata) {
      warnings.push({
        field: 'metadata',
        message: 'Metadata is missing',
        severity: 'info'
      });
    } else if (definition.metadata.needs_review) {
      warnings.push({
        field: 'metadata.needs_review',
        message: 'This function is flagged for review',
        severity: 'warning'
      });
    }

    // Check sources
    if (!definition.sources || !definition.sources.source_file) {
      warnings.push({
        field: 'sources',
        message: 'Source documentation is missing',
        severity: 'info'
      });
    }
  }

  /**
   * Validate legacy format
   */
  private validateLegacyFormat(
    definition: LegacyFunctionDefinition,
    errors: ValidationError[],
    warnings: ValidationWarning[]
  ): void {
    // Check syntax
    if (!definition.syntax) {
      errors.push({
        field: 'syntax',
        message: 'Syntax definition is required',
        severity: 'error'
      });
    }

    // Check arguments
    if (!definition.arguments || definition.arguments.length === 0) {
      warnings.push({
        field: 'arguments',
        message: 'No arguments defined',
        severity: 'info'
      });
    } else {
      // Check for null types
      const nullTypes = definition.arguments.filter(arg => arg.type === null);
      if (nullTypes.length > 0) {
        warnings.push({
          field: 'arguments',
          message: `${nullTypes.length} arguments have null type`,
          severity: 'warning'
        });
      }
    }

    // Check return values
    if (!definition.return_value || definition.return_value.length === 0) {
      warnings.push({
        field: 'return_value',
        message: 'No return value defined',
        severity: 'warning'
      });
    }

    // Check examples
    if (this.config.checkExamples && (!definition.examples || definition.examples.length === 0)) {
      warnings.push({
        field: 'examples',
        message: 'No examples provided',
        severity: 'warning'
      });
    }

    // Check documentation source
    if (!definition.page_numbers || !definition.document_title) {
      warnings.push({
        field: 'documentation',
        message: 'Documentation source is incomplete',
        severity: 'info'
      });
    }
  }

  /**
   * Validate arguments
   */
  private validateArguments(
    args: any[],
    errors: ValidationError[],
    warnings: ValidationWarning[]
  ): void {
    args.forEach((arg, index) => {
      if (!arg.name) {
        errors.push({
          field: `arguments[${index}].name`,
          message: 'Argument name is required',
          severity: 'error'
        });
      }

      if (!arg.description || arg.description.trim() === '') {
        warnings.push({
          field: `arguments[${index}].description`,
          message: `Argument '${arg.name}' lacks description`,
          severity: 'warning'
        });
      }

      // Check type consistency
      if (this.config.checkTypeConsistency && arg.type_prefix && arg.name) {
        const namePrefix = arg.name.split('_')[0];
        if (namePrefix !== arg.type_prefix && !arg.is_keyword) {
          warnings.push({
            field: `arguments[${index}].type_prefix`,
            message: `Type prefix '${arg.type_prefix}' doesn't match name prefix '${namePrefix}'`,
            severity: 'info'
          });
        }
      }
    });
  }

  /**
   * Validate examples
   */
  private validateExamples(
    examples: any[],
    functionName: string,
    warnings: ValidationWarning[]
  ): void {
    examples.forEach((example, index) => {
      if (!example.code) {
        warnings.push({
          field: `examples[${index}].code`,
          message: 'Example code is missing',
          severity: 'warning'
        });
      } else if (!example.code.includes(functionName)) {
        warnings.push({
          field: `examples[${index}].code`,
          message: 'Example code does not use the function',
          severity: 'info'
        });
      }

      if (!example.description) {
        warnings.push({
          field: `examples[${index}].description`,
          message: 'Example description is missing',
          severity: 'info'
        });
      }
    });
  }

  /**
   * Calculate quality scores
   */
  private calculateQualityScore(definition: FunctionDefinition): QualityScore {
    let documentation = 0;
    let completeness = 0;
    let clarity = 0;
    let examples = 0;

    // Documentation score
    if (definition.description && definition.description.length > 50) documentation += 50;
    if (definition.description && definition.description.length > 200) documentation += 30;
    if (definition.notes) documentation += 20;

    // Completeness score
    if (definition.function_name) completeness += 20;
    if (definition.description) completeness += 20;
    if (definition.category && definition.category !== 'Uncategorized') completeness += 15;

    if (isModernFormat(definition)) {
      if (definition.primary_syntax?.arguments?.length > 0) completeness += 15;
      if (definition.primary_syntax?.return_values?.length > 0) completeness += 15;
      if (definition.sources?.source_file) completeness += 10;
      if (definition.metadata) completeness += 5;
    } else if (isLegacyFormat(definition)) {
      if (definition.arguments?.length > 0) completeness += 15;
      if (definition.return_value?.length > 0) completeness += 15;
      if (definition.document_title) completeness += 10;
      if (definition.page_numbers) completeness += 5;
    }

    // Clarity score
    const descLength = definition.description?.length || 0;
    if (descLength > 100 && descLength < 1000) clarity += 40;
    if (descLength >= 1000) clarity += 30;

    if (isModernFormat(definition)) {
      const hasGoodArgs = definition.primary_syntax?.arguments?.every(
        arg => arg.description && arg.description.length > 10
      );
      if (hasGoodArgs) clarity += 30;
      if (definition.primary_syntax?.syntax_string) clarity += 30;
    }

    // Examples score
    if (isModernFormat(definition)) {
      const exCount = definition.examples?.length || 0;
      examples = Math.min(exCount * 35, 70);
      if (exCount > 0 && definition.examples?.every(ex => ex.description)) {
        examples += 30;
      }
    } else if (isLegacyFormat(definition)) {
      const exCount = definition.examples?.length || 0;
      examples = Math.min(exCount * 50, 100);
    }

    const overall = Math.round((documentation + completeness + clarity + examples) / 4);

    return {
      overall,
      documentation,
      completeness,
      clarity,
      examples
    };
  }

  /**
   * Generate improvement suggestions
   */
  private generateSuggestions(
    definition: FunctionDefinition,
    validation: ValidationResult
  ): Suggestion[] {
    const suggestions: Suggestion[] = [];

    if (!this.config.generateSuggestions) {
      return suggestions;
    }

    // Suggestions based on validation results
    validation.warnings.forEach(warning => {
      suggestions.push({
        category: 'documentation',
        priority: warning.severity === 'warning' ? 'medium' : 'low',
        title: `Fix warning: ${warning.field}`,
        description: warning.message
      });
    });

    // Category suggestions
    if (definition.category === 'Uncategorized') {
      suggestions.push({
        category: 'metadata',
        priority: 'high',
        title: 'Categorize function',
        description: 'Assign this function to an appropriate category',
        current_value: 'Uncategorized',
        suggested_value: 'Review documentation and assign proper category'
      });
    }

    // Example suggestions
    if (isModernFormat(definition) && (!definition.examples || definition.examples.length === 0)) {
      suggestions.push({
        category: 'examples',
        priority: 'high',
        title: 'Add usage examples',
        description: 'Provide at least one practical example showing how to use this function',
        current_value: 'No examples',
        suggested_value: `${definition.function_name}( ... )`
      });
    }

    // Description quality
    if (definition.description && definition.description.length < 50) {
      suggestions.push({
        category: 'documentation',
        priority: 'medium',
        title: 'Expand description',
        description: 'The description is too brief. Add more details about functionality and use cases.',
        current_value: `${definition.description.length} characters`,
        suggested_value: 'At least 100 characters recommended'
      });
    }

    // Metadata suggestions (modern format)
    if (isModernFormat(definition)) {
      if (!definition.metadata?.verified) {
        suggestions.push({
          category: 'metadata',
          priority: 'low',
          title: 'Verify function definition',
          description: 'Mark this function as verified after manual review',
          current_value: 'false',
          suggested_value: 'true'
        });
      }

      if (!definition.sources?.source_file) {
        suggestions.push({
          category: 'metadata',
          priority: 'medium',
          title: 'Add source documentation',
          description: 'Reference the original documentation file',
          current_value: 'Missing',
          suggested_value: 'docs/path/to/manual.pdf'
        });
      }
    }

    return suggestions;
  }

  /**
   * Perform AI-powered analysis
   */
  private async performAIAnalysis(definition: FunctionDefinition): Promise<string> {
    if (!this.ai) return '';

    try {
      // Create a prompt for AI analysis
      const analysisPrompt = `Analyze this SKILL function definition and provide insights:

Function: ${definition.function_name}
Category: ${definition.category}
Description: ${definition.description}

${isModernFormat(definition) ? `
Arguments: ${definition.primary_syntax.arguments.map((a: any) => `${a.name} (${a.type_description})`).join(', ')}
Return: ${definition.primary_syntax.return_syntax}
` : `
Syntax: ${(definition as LegacyFunctionDefinition).syntax}
`}

Please provide:
1. Quality assessment of the documentation
2. Potential issues or ambiguities
3. Suggestions for improvement
4. Missing information that should be added

Keep the response concise and actionable.`;

      // Use a public method instead of private queryAI
      const analysis = await this.ai.analyzeFailure(
        `Function: ${definition.function_name}`,
        analysisPrompt
      );
      return analysis;
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      return `AI analysis failed: ${errorMessage}`;
    }
  }

  /**
   * Format review result as markdown
   */
  formatAsMarkdown(result: FunctionReviewResult): string {
    const { function_name, format, validation, quality_score, suggestions, ai_analysis } = result;

    let md = `# Function Review: \`${function_name}\`\n\n`;
    md += `**Format**: ${format}\n`;
    md += `**Timestamp**: ${result.timestamp}\n\n`;

    // Quality Score
    md += `## 📊 Quality Score\n\n`;
    md += `- **Overall**: ${quality_score.overall}/100\n`;
    md += `- **Documentation**: ${quality_score.documentation}/100\n`;
    md += `- **Completeness**: ${quality_score.completeness}/100\n`;
    md += `- **Clarity**: ${quality_score.clarity}/100\n`;
    md += `- **Examples**: ${quality_score.examples}/100\n\n`;

    // Validation
    md += `## ✓ Validation\n\n`;
    md += `**Status**: ${validation.is_valid ? '✅ Valid' : '❌ Invalid'}\n\n`;

    if (validation.errors.length > 0) {
      md += `### Errors (${validation.errors.length})\n\n`;
      validation.errors.forEach(err => {
        md += `- **[${err.severity}]** ${err.field}: ${err.message}\n`;
      });
      md += `\n`;
    }

    if (validation.warnings.length > 0) {
      md += `### Warnings (${validation.warnings.length})\n\n`;
      validation.warnings.forEach(warn => {
        md += `- **[${warn.severity}]** ${warn.field}: ${warn.message}\n`;
      });
      md += `\n`;
    }

    // Suggestions
    if (suggestions.length > 0) {
      md += `## 💡 Suggestions (${suggestions.length})\n\n`;

      const highPriority = suggestions.filter(s => s.priority === 'high');
      const mediumPriority = suggestions.filter(s => s.priority === 'medium');
      const lowPriority = suggestions.filter(s => s.priority === 'low');

      if (highPriority.length > 0) {
        md += `### High Priority\n\n`;
        highPriority.forEach(s => {
          md += `#### ${s.title}\n`;
          md += `${s.description}\n\n`;
          if (s.current_value) md += `- Current: ${s.current_value}\n`;
          if (s.suggested_value) md += `- Suggested: ${s.suggested_value}\n`;
          md += `\n`;
        });
      }

      if (mediumPriority.length > 0) {
        md += `### Medium Priority\n\n`;
        mediumPriority.forEach(s => {
          md += `- **${s.title}**: ${s.description}\n`;
        });
        md += `\n`;
      }

      if (lowPriority.length > 0) {
        md += `### Low Priority\n\n`;
        lowPriority.forEach(s => {
          md += `- ${s.title}: ${s.description}\n`;
        });
        md += `\n`;
      }
    }

    // AI Analysis
    if (ai_analysis) {
      md += `## 🤖 AI Analysis\n\n`;
      md += `${ai_analysis}\n\n`;
    }

    return md;
  }

  /**
   * Save review result to file
   */
  saveResult(result: FunctionReviewResult, outputPath: string): void {
    const ext = path.extname(outputPath);

    if (ext === '.md') {
      const markdown = this.formatAsMarkdown(result);
      fs.writeFileSync(outputPath, markdown, 'utf-8');
    } else {
      fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), 'utf-8');
    }

    console.log(`✅ Review saved to: ${outputPath}`);
  }
}

/**
 * Factory function
 */
export function createFunctionReviewer(config?: Partial<ReviewConfig>): FunctionReviewer {
  return new FunctionReviewer(config);
}
