/**
 * AI-Powered Test Helper Utilities
 *
 * This module provides AI integration for intelligent test automation,
 * including smart element selection, test generation, and failure analysis.
 */

import OpenAI from 'openai';
import { GoogleGenerativeAI } from '@google/generative-ai';
import { Page } from '@playwright/test';

export interface AIConfig {
  provider: 'openai' | 'gemini';
  apiKey?: string;
  model?: string;
}

export class AITestHelper {
  private openai?: OpenAI;
  private gemini?: GoogleGenerativeAI;
  private provider: 'openai' | 'gemini';

  constructor(config: AIConfig) {
    this.provider = config.provider;

    if (config.provider === 'openai') {
      this.openai = new OpenAI({
        apiKey: config.apiKey || process.env.OPENAI_API_KEY,
      });
    } else if (config.provider === 'gemini') {
      this.gemini = new GoogleGenerativeAI(
        config.apiKey || process.env.GEMINI_API_KEY || ''
      );
    }
  }

  /**
   * Generate intelligent selectors for elements based on description
   */
  async generateSelector(
    page: Page,
    description: string
  ): Promise<string> {
    const pageContent = await page.content();
    const prompt = `Given this HTML content, generate the most stable CSS selector for: "${description}"

HTML Content (truncated):
${pageContent.substring(0, 2000)}

Requirements:
- Prefer data-testid, id, or semantic attributes
- Avoid fragile selectors like nth-child or dynamic classes
- Return only the selector string, no explanation

Selector:`;

    const selector = await this.queryAI(prompt);
    return selector.trim();
  }

  /**
   * Analyze test failure and suggest fixes
   */
  async analyzeFailure(
    testName: string,
    errorMessage: string,
    screenshot?: string
  ): Promise<string> {
    const prompt = `Analyze this test failure and suggest solutions:

Test Name: ${testName}
Error Message: ${errorMessage}

Provide:
1. Root cause analysis
2. Suggested fixes (2-3 options)
3. Prevention strategies

Analysis:`;

    return await this.queryAI(prompt);
  }

  /**
   * Generate test cases from user story or requirement
   */
  async generateTestCases(
    userStory: string,
    testType: 'e2e' | 'integration' | 'unit' = 'e2e'
  ): Promise<string[]> {
    const prompt = `Generate ${testType} test cases for this user story:

${userStory}

Generate 5-7 comprehensive test cases covering:
- Happy path
- Edge cases
- Error scenarios
- Accessibility
- Performance (if relevant)

Format: Return as JSON array of test case descriptions.

Test Cases:`;

    const response = await this.queryAI(prompt);
    try {
      return JSON.parse(response);
    } catch {
      return response.split('\n').filter(line => line.trim());
    }
  }

  /**
   * Suggest assertions based on page state
   */
  async suggestAssertions(
    page: Page,
    context: string
  ): Promise<string[]> {
    const pageContent = await page.content();
    const url = page.url();

    const prompt = `Given this page state, suggest relevant assertions for: "${context}"

URL: ${url}
Page Content (truncated):
${pageContent.substring(0, 2000)}

Suggest 3-5 meaningful assertions that would verify the expected behavior.
Format: Return as JSON array of assertion descriptions.

Assertions:`;

    const response = await this.queryAI(prompt);
    try {
      return JSON.parse(response);
    } catch {
      return response.split('\n').filter(line => line.trim());
    }
  }

  /**
   * Generate test data based on schema or requirements
   */
  async generateTestData(
    schema: string,
    count: number = 1
  ): Promise<any[]> {
    const prompt = `Generate ${count} test data objects matching this schema:

${schema}

Requirements:
- Realistic, diverse data
- Edge cases included
- Valid according to schema
- Return as JSON array

Test Data:`;

    const response = await this.queryAI(prompt);
    try {
      return JSON.parse(response);
    } catch {
      return [];
    }
  }

  /**
   * Analyze page performance and suggest optimizations
   */
  async analyzePerformance(
    performanceMetrics: any
  ): Promise<string> {
    const prompt = `Analyze these performance metrics and suggest optimizations:

${JSON.stringify(performanceMetrics, null, 2)}

Provide:
1. Performance bottlenecks
2. Optimization recommendations
3. Priority level (High/Medium/Low)

Analysis:`;

    return await this.queryAI(prompt);
  }

  /**
   * Generate accessibility test scenarios
   */
  async generateA11yTests(
    pageDescription: string
  ): Promise<string[]> {
    const prompt = `Generate accessibility test scenarios for: "${pageDescription}"

Focus on:
- WCAG 2.1 AA compliance
- Keyboard navigation
- Screen reader support
- Color contrast
- Focus management

Return as JSON array of test scenarios.

Scenarios:`;

    const response = await this.queryAI(prompt);
    try {
      return JSON.parse(response);
    } catch {
      return response.split('\n').filter(line => line.trim());
    }
  }

  /**
   * Core AI query method
   */
  private async queryAI(prompt: string): Promise<string> {
    if (this.provider === 'openai' && this.openai) {
      const completion = await this.openai.chat.completions.create({
        model: 'gpt-4-turbo-preview',
        messages: [
          {
            role: 'system',
            content: 'You are an expert QA engineer and test automation specialist. Provide concise, actionable responses.'
          },
          { role: 'user', content: prompt }
        ],
        temperature: 0.3,
        max_tokens: 1000,
      });

      return completion.choices[0]?.message?.content || '';
    } else if (this.provider === 'gemini' && this.gemini) {
      const model = this.gemini.getGenerativeModel({
        model: 'gemini-pro'
      });

      const result = await model.generateContent(prompt);
      const response = await result.response;
      return response.text();
    }

    throw new Error('AI provider not configured');
  }
}

/**
 * Factory function for creating AI test helper
 */
export function createAITestHelper(
  provider: 'openai' | 'gemini' = 'gemini'
): AITestHelper {
  return new AITestHelper({ provider });
}
