import { test, expect } from '@playwright/test';
import { createAITestHelper } from '../utils/ai-test-helper';
import { createCDPHelper } from '../utils/chrome-devtools-helper';

/**
 * Example E2E Test with AI-Powered Features and Chrome DevTools Integration
 *
 * This test demonstrates:
 * - AI-powered element selection
 * - Performance monitoring with Chrome DevTools
 * - Network request analysis
 * - Console error detection
 * - Smart assertions
 */

test.describe('E2E Example: Homepage Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to homepage
    await page.goto('/');
  });

  test('should load homepage with performance monitoring', async ({ page }) => {
    // Initialize Chrome DevTools helper
    const cdp = await createCDPHelper(page);

    // Collect initial performance metrics
    const initialMetrics = await cdp.collectPerformanceMetrics();
    console.log('Initial Performance Metrics:', initialMetrics);

    // Perform actions
    await page.waitForLoadState('networkidle');

    // Collect final metrics
    const finalMetrics = await cdp.collectPerformanceMetrics();
    console.log('Final Performance Metrics:', finalMetrics);

    // Get Core Web Vitals
    const webVitals = await cdp.getCoreWebVitals();
    console.log('Core Web Vitals:', webVitals);

    // Verify no console errors
    expect(cdp.hasConsoleErrors()).toBe(false);

    // Get performance summary
    const summary = cdp.getPerformanceSummary();
    console.log('Performance Summary:', summary);

    // Assertions on performance
    expect(summary.errorCount).toBe(0);
    expect(webVitals.TTFB).toBeLessThan(1000); // TTFB < 1s
    if (webVitals.FCP) {
      expect(webVitals.FCP).toBeLessThan(2000); // FCP < 2s
    }

    // Cleanup
    await cdp.cleanup();
  });

  test('should interact with elements using AI-powered selectors', async ({ page }) => {
    const ai = createAITestHelper('gemini');

    // Use AI to find elements
    const searchButtonSelector = await ai.generateSelector(
      page,
      'main search button in the header'
    );
    console.log('AI Generated Selector:', searchButtonSelector);

    // Click the button
    await page.click(searchButtonSelector);

    // Let AI suggest assertions
    const assertions = await ai.suggestAssertions(
      page,
      'after clicking search button'
    );
    console.log('AI Suggested Assertions:', assertions);

    // Verify search input is visible
    await expect(page.locator('input[type="search"]')).toBeVisible();
  });

  test('should monitor network requests and API calls', async ({ page }) => {
    const cdp = await createCDPHelper(page);

    // Trigger some API calls
    await page.goto('/?load=data');
    await page.waitForLoadState('networkidle');

    // Get all network requests
    const allRequests = cdp.getNetworkRequests();
    console.log(`Total requests: ${allRequests.length}`);

    // Filter API requests
    const apiRequests = cdp.filterNetworkRequests({
      type: 'XHR',
    });
    console.log('API Requests:', apiRequests);

    // Verify API calls
    expect(apiRequests.length).toBeGreaterThan(0);

    // Check for slow requests
    const slowRequests = allRequests.filter(r => r.time > 3000);
    expect(slowRequests.length).toBe(0);

    // Get performance summary
    const summary = cdp.getPerformanceSummary();
    console.log('Slowest Requests:', summary.slowestRequests);
    console.log('Largest Requests:', summary.largestRequests);

    await cdp.cleanup();
  });

  test('should track console messages during interaction', async ({ page }) => {
    const cdp = await createCDPHelper(page);

    // Perform interactions
    await page.click('button#action');
    await page.waitForTimeout(1000);

    // Get console messages
    const allMessages = cdp.getConsoleMessages();
    const errors = cdp.getConsoleMessages('error');
    const warnings = cdp.getConsoleMessages('warn');

    console.log('Total console messages:', allMessages.length);
    console.log('Errors:', errors);
    console.log('Warnings:', warnings);

    // Verify no unexpected errors
    expect(errors.length).toBe(0);

    await cdp.cleanup();
  });

  test('should use AI for test failure analysis', async ({ page }) => {
    const ai = createAITestHelper('gemini');
    const cdp = await createCDPHelper(page);

    try {
      // Intentionally failing action for demo
      await page.click('button#non-existent', { timeout: 5000 });
    } catch (error: unknown) {
      // Use AI to analyze failure
      const errorMessage = error instanceof Error ? error.message : String(error);
      const analysis = await ai.analyzeFailure(
        'Homepage button click test',
        errorMessage
      );

      console.log('AI Failure Analysis:');
      console.log(analysis);

      // Get additional context from DevTools
      const consoleErrors = cdp.getConsoleMessages('error');
      const networkSummary = cdp.getPerformanceSummary();

      console.log('Console Errors:', consoleErrors);
      console.log('Network Summary:', networkSummary);
    }

    await cdp.cleanup();
  });

  test('should measure code coverage', async ({ page }) => {
    const cdp = await createCDPHelper(page);

    // Start coverage
    await cdp.startCoverage();

    // Perform actions
    await page.click('button#feature-a');
    await page.click('button#feature-b');
    await page.fill('input#search', 'test query');

    // Stop and collect coverage
    const coverage = await cdp.stopCoverage();

    console.log('Code Coverage Results:', coverage);

    // Analyze coverage (you can integrate with tools like Istanbul)
    const totalFunctions = coverage.result.length;
    const coveredFunctions = coverage.result.filter(
      (fn: any) => fn.functions?.some((f: any) => f.ranges.some((r: any) => r.count > 0))
    ).length;

    console.log(`Coverage: ${coveredFunctions}/${totalFunctions} functions`);

    await cdp.cleanup();
  });
});

/**
 * AI-Generated Test Cases Example
 */
test.describe('AI-Generated Tests', () => {
  test('generate and run dynamic test cases', async ({ page }) => {
    const ai = createAITestHelper('gemini');

    const userStory = `
      As a user, I want to search for products on the homepage
      so that I can quickly find what I'm looking for.
      The search should support:
      - Autocomplete suggestions
      - Filtering by category
      - Sorting by relevance/price
    `;

    // Generate test cases using AI
    const testCases = await ai.generateTestCases(userStory, 'e2e');

    console.log('AI-Generated Test Cases:');
    testCases.forEach((testCase, index) => {
      console.log(`${index + 1}. ${testCase}`);
    });

    // You can then implement these test cases programmatically
    // or use them as guidance for manual test creation
  });
});

/**
 * Performance Regression Test
 */
test.describe('Performance Regression', () => {
  test('should meet performance benchmarks', async ({ page }) => {
    const cdp = await createCDPHelper(page);
    const ai = createAITestHelper('gemini');

    // Measure page load performance
    await page.goto('/', { waitUntil: 'networkidle' });

    const metrics = await cdp.collectPerformanceMetrics();
    const webVitals = await cdp.getCoreWebVitals();
    const navTiming = await cdp.getNavigationTiming();

    const performanceData = {
      metrics,
      webVitals,
      navTiming,
      summary: cdp.getPerformanceSummary(),
    };

    console.log('Performance Data:', JSON.stringify(performanceData, null, 2));

    // Use AI to analyze performance
    const analysis = await ai.analyzePerformance(performanceData);
    console.log('AI Performance Analysis:');
    console.log(analysis);

    // Performance assertions
    expect(metrics.scriptDuration).toBeLessThan(5000); // < 5s
    expect(metrics.layoutDuration).toBeLessThan(1000); // < 1s
    expect(performanceData.summary.totalSize).toBeLessThan(5 * 1024 * 1024); // < 5MB

    await cdp.cleanup();
  });
});

/**
 * Accessibility Test with AI
 */
test.describe('Accessibility', () => {
  test('should generate and verify accessibility requirements', async ({ page }) => {
    const ai = createAITestHelper('gemini');

    // Generate accessibility test scenarios
    const a11yTests = await ai.generateA11yTests(
      'E-commerce product listing page with filters and sorting'
    );

    console.log('AI-Generated Accessibility Tests:');
    a11yTests.forEach((test, index) => {
      console.log(`${index + 1}. ${test}`);
    });

    // Run basic accessibility checks
    await page.goto('/');

    // Check keyboard navigation
    await page.keyboard.press('Tab');
    const focusedElement = await page.evaluate(() => {
      return document.activeElement?.tagName;
    });
    expect(focusedElement).toBeTruthy();

    // You can integrate with @axe-core/playwright for comprehensive checks
    // const { injectAxe, checkA11y } = require('axe-playwright');
    // await injectAxe(page);
    // await checkA11y(page);
  });
});
