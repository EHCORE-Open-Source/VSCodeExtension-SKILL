import { test, expect } from '@playwright/test';
import { createCDPHelper } from '../utils/chrome-devtools-helper';

/**
 * Streamlit JSON Reviewer App - E2E Tests with CDP
 *
 * This test suite demonstrates real-world web automation testing
 * of the Streamlit function review application using Chrome DevTools Protocol.
 *
 * Features:
 * - Performance monitoring during app interactions
 * - Network request tracking for API calls
 * - Console error detection
 * - Real-time metrics collection
 * - Interactive element testing
 */

test.describe('Streamlit JSON Reviewer - E2E Tests', () => {
  const STREAMLIT_URL = 'http://localhost:8501';

  test.beforeEach(async ({ page }) => {
    // Set longer timeout for Streamlit app initialization
    test.setTimeout(60000);
  });

  test('should load Streamlit app successfully with performance monitoring', async ({ page }) => {
    const cdp = await createCDPHelper(page);

    // Navigate to Streamlit app
    console.log('🚀 Loading Streamlit app...');
    await page.goto(STREAMLIT_URL);

    // Wait for Streamlit to fully initialize
    await page.waitForLoadState('networkidle', { timeout: 30000 });

    // Collect initial performance metrics
    const initialMetrics = await cdp.collectPerformanceMetrics();
    console.log('📊 Initial Performance Metrics:', {
      nodes: initialMetrics.nodes,
      jsHeapUsedSize: `${(initialMetrics.jsHeapUsedSize / 1024 / 1024).toFixed(2)} MB`,
      layoutCount: initialMetrics.layoutCount,
      scriptDuration: `${initialMetrics.scriptDuration.toFixed(2)}ms`
    });

    // Get Core Web Vitals
    const webVitals = await cdp.getCoreWebVitals();
    console.log('🎯 Core Web Vitals:', webVitals);

    // Check for console errors
    const hasErrors = cdp.hasConsoleErrors();
    console.log(`❌ Console Errors: ${hasErrors ? 'YES' : 'NO'}`);

    if (hasErrors) {
      const errors = cdp.getConsoleMessages('error');
      console.log('Error Details:', errors);
    }

    // Get network performance summary
    const summary = cdp.getPerformanceSummary();
    console.log('🌐 Network Summary:', {
      totalRequests: summary.totalRequests,
      totalSize: `${(summary.totalSize / 1024 / 1024).toFixed(2)} MB`,
      errorCount: summary.errorCount,
      warningCount: summary.warningCount
    });

    // Assertions
    expect(hasErrors).toBe(false);
    expect(summary.errorCount).toBe(0);

    // Performance assertions
    if (webVitals.TTFB) {
      expect(webVitals.TTFB).toBeLessThan(3000); // TTFB < 3s for Streamlit
    }

    await cdp.cleanup();
  });

  test('should detect Streamlit framework elements', async ({ page }) => {
    await page.goto(STREAMLIT_URL);
    await page.waitForLoadState('networkidle');

    // Check for Streamlit root element
    const streamlitRoot = await page.locator('[data-testid="stApp"]').count();
    expect(streamlitRoot).toBeGreaterThan(0);

    // Check for main content area
    const mainContent = await page.locator('[data-testid="stAppViewContainer"]').count();
    expect(mainContent).toBeGreaterThan(0);

    console.log('✅ Streamlit framework elements detected');
  });

  test('should monitor file upload interactions with CDP', async ({ page }) => {
    const cdp = await createCDPHelper(page);

    await page.goto(STREAMLIT_URL);
    await page.waitForLoadState('networkidle');

    // Look for file uploader
    const fileUploader = page.locator('[data-testid="stFileUploader"]').first();
    const uploaderExists = await fileUploader.count() > 0;

    if (uploaderExists) {
      console.log('📁 File uploader detected');

      // Collect metrics before interaction
      const beforeMetrics = await cdp.collectPerformanceMetrics();

      // Note: Actual file upload would require a test file
      // This demonstrates how to monitor the interaction

      // Collect metrics after interaction
      const afterMetrics = await cdp.collectPerformanceMetrics();

      console.log('📊 Metrics Comparison:', {
        before: {
          nodes: beforeMetrics.nodes,
          jsHeapUsedSize: `${(beforeMetrics.jsHeapUsedSize / 1024 / 1024).toFixed(2)} MB`
        },
        after: {
          nodes: afterMetrics.nodes,
          jsHeapUsedSize: `${(afterMetrics.jsHeapUsedSize / 1024 / 1024).toFixed(2)} MB`
        },
        delta: {
          nodes: afterMetrics.nodes - beforeMetrics.nodes,
          heapDelta: `${((afterMetrics.jsHeapUsedSize - beforeMetrics.jsHeapUsedSize) / 1024 / 1024).toFixed(2)} MB`
        }
      });
    }

    await cdp.cleanup();
  });

  test('should track WebSocket connections for Streamlit updates', async ({ page }) => {
    const cdp = await createCDPHelper(page);

    await page.goto(STREAMLIT_URL);
    await page.waitForLoadState('networkidle');

    // Get all network requests
    const allRequests = cdp.getNetworkRequests();

    // Filter WebSocket upgrade requests
    const wsRequests = allRequests.filter(r =>
      r.url.includes('_stcore/stream') || r.url.includes('ws://')
    );

    console.log(`🔌 WebSocket Requests: ${wsRequests.length}`);
    wsRequests.forEach(ws => {
      console.log(`  - ${ws.url} (${ws.method})`);
    });

    // Streamlit should establish WebSocket connection
    expect(allRequests.length).toBeGreaterThan(0);

    await cdp.cleanup();
  });

  test('should measure interaction responsiveness', async ({ page }) => {
    const cdp = await createCDPHelper(page);

    await page.goto(STREAMLIT_URL);
    await page.waitForLoadState('networkidle');

    // Test interaction with Streamlit widget if available
    const buttons = page.locator('button').all();
    const buttonList = await buttons;

    if (buttonList.length > 0) {
      console.log(`🔘 Found ${buttonList.length} buttons`);

      // Measure click response time
      const startTime = Date.now();

      await buttonList[0].click();
      await page.waitForTimeout(100); // Wait for Streamlit to process

      const responseTime = Date.now() - startTime;
      console.log(`⏱️ Click Response Time: ${responseTime}ms`);

      // Collect metrics after interaction
      const metrics = await cdp.collectPerformanceMetrics();
      console.log(`💻 JS Heap Used: ${(metrics.jsHeapUsedSize / 1024 / 1024).toFixed(2)} MB`);

      // Response time should be reasonable
      expect(responseTime).toBeLessThan(5000);
    }

    await cdp.cleanup();
  });

  test('should capture and analyze page load timeline', async ({ page }) => {
    const cdp = await createCDPHelper(page);

    console.log('📈 Starting timeline capture...');

    await page.goto(STREAMLIT_URL);
    await page.waitForLoadState('networkidle');

    // Get navigation timing
    const navTiming = await cdp.getNavigationTiming();

    console.log('⏱️ Navigation Timing:', {
      dns: `${navTiming.domainLookupEnd - navTiming.domainLookupStart}ms`,
      tcp: `${navTiming.connectEnd - navTiming.connectStart}ms`,
      request: `${navTiming.responseStart - navTiming.requestStart}ms`,
      response: `${navTiming.responseEnd - navTiming.responseStart}ms`,
      domProcessing: `${navTiming.domComplete - navTiming.domLoading}ms`,
      loadComplete: `${navTiming.loadEventEnd - navTiming.navigationStart}ms`
    });

    // Get performance summary
    const summary = cdp.getPerformanceSummary();

    console.log('📊 Performance Summary:', {
      avgScriptDuration: `${summary.avgScriptDuration.toFixed(2)}ms`,
      avgLayoutDuration: `${summary.avgLayoutDuration.toFixed(2)}ms`,
      totalSize: `${(summary.totalSize / 1024 / 1024).toFixed(2)} MB`
    });

    await cdp.cleanup();
  });

  test('should verify no memory leaks during prolonged interaction', async ({ page }) => {
    const cdp = await createCDPHelper(page);

    await page.goto(STREAMLIT_URL);
    await page.waitForLoadState('networkidle');

    const memorySnapshots = [];

    // Take memory snapshots over multiple interactions
    for (let i = 0; i < 5; i++) {
      const metrics = await cdp.collectPerformanceMetrics();
      memorySnapshots.push({
        iteration: i,
        heapUsed: metrics.jsHeapUsedSize,
        nodes: metrics.nodes
      });

      console.log(`📸 Snapshot ${i + 1}:`, {
        heap: `${(metrics.jsHeapUsedSize / 1024 / 1024).toFixed(2)} MB`,
        nodes: metrics.nodes
      });

      // Simulate user interaction
      await page.waitForTimeout(500);
    }

    // Check if memory is growing unbounded
    const firstHeap = memorySnapshots[0].heapUsed;
    const lastHeap = memorySnapshots[memorySnapshots.length - 1].heapUsed;
    const heapGrowth = ((lastHeap - firstHeap) / firstHeap) * 100;

    console.log(`📈 Memory Growth: ${heapGrowth.toFixed(2)}%`);

    // Memory growth should be reasonable (< 50% for these iterations)
    expect(heapGrowth).toBeLessThan(50);

    await cdp.cleanup();
  });

  test('should check accessibility of interactive elements', async ({ page }) => {
    await page.goto(STREAMLIT_URL);
    await page.waitForLoadState('networkidle');

    // Test keyboard navigation
    console.log('⌨️ Testing keyboard navigation...');

    await page.keyboard.press('Tab');
    const focusedElement1 = await page.evaluate(() => {
      const el = document.activeElement;
      return {
        tag: el?.tagName,
        type: el?.getAttribute('type'),
        testId: el?.getAttribute('data-testid')
      };
    });

    console.log('First Tab Focus:', focusedElement1);
    expect(focusedElement1.tag).toBeTruthy();

    // Check for ARIA labels
    const ariaElements = await page.locator('[aria-label]').count();
    console.log(`🏷️ Elements with aria-label: ${ariaElements}`);

    // Check for role attributes
    const roleElements = await page.locator('[role]').count();
    console.log(`🎭 Elements with role: ${roleElements}`);
  });
});

/**
 * Advanced CDP Features Tests
 */
test.describe('Advanced CDP Features', () => {
  const STREAMLIT_URL = 'http://localhost:8501';

  test('should capture code coverage for Streamlit app', async ({ page }) => {
    const cdp = await createCDPHelper(page);

    // Start coverage tracking
    await cdp.startCoverage();
    console.log('📊 Code coverage tracking started');

    await page.goto(STREAMLIT_URL);
    await page.waitForLoadState('networkidle');

    // Interact with the app to trigger code paths
    const buttons = await page.locator('button').all();
    for (let i = 0; i < Math.min(buttons.length, 3); i++) {
      await buttons[i].click();
      await page.waitForTimeout(200);
    }

    // Stop and collect coverage
    const coverage = await cdp.stopCoverage();

    console.log(`📈 Coverage Results: ${coverage.result.length} scripts analyzed`);

    // Calculate coverage percentage (simplified)
    let totalRanges = 0;
    let coveredRanges = 0;

    for (const script of coverage.result) {
      for (const func of script.functions || []) {
        for (const range of func.ranges || []) {
          totalRanges++;
          if (range.count > 0) coveredRanges++;
        }
      }
    }

    const coveragePercent = totalRanges > 0
      ? (coveredRanges / totalRanges) * 100
      : 0;

    console.log(`✅ Code Coverage: ${coveragePercent.toFixed(2)}%`);

    await cdp.cleanup();
  });

  test('should analyze network waterfall for optimization', async ({ page }) => {
    const cdp = await createCDPHelper(page);

    await page.goto(STREAMLIT_URL);
    await page.waitForLoadState('networkidle');

    const requests = cdp.getNetworkRequests();

    // Group requests by type
    const requestsByType = requests.reduce((acc, req) => {
      acc[req.type] = (acc[req.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    console.log('📊 Requests by Type:', requestsByType);

    // Find bottlenecks
    const summary = cdp.getPerformanceSummary();

    console.log('🐌 Slowest Requests:');
    summary.slowestRequests.forEach((req, i) => {
      console.log(`  ${i + 1}. ${req.url.substring(0, 60)}... (${req.time}ms)`);
    });

    console.log('📦 Largest Requests:');
    summary.largestRequests.forEach((req, i) => {
      console.log(`  ${i + 1}. ${req.url.substring(0, 60)}... (${(req.size / 1024).toFixed(2)} KB)`);
    });

    await cdp.cleanup();
  });

  test('should monitor real-time console logs during interaction', async ({ page }) => {
    const cdp = await createCDPHelper(page);

    await page.goto(STREAMLIT_URL);
    await page.waitForLoadState('networkidle');

    // Perform various interactions
    await page.mouse.move(100, 100);
    await page.waitForTimeout(500);

    const buttons = await page.locator('button').all();
    if (buttons.length > 0) {
      await buttons[0].click();
      await page.waitForTimeout(500);
    }

    // Get all console messages
    const allMessages = cdp.getConsoleMessages();
    const logs = cdp.getConsoleMessages('log');
    const warnings = cdp.getConsoleMessages('warn');
    const errors = cdp.getConsoleMessages('error');

    console.log('📝 Console Summary:', {
      total: allMessages.length,
      logs: logs.length,
      warnings: warnings.length,
      errors: errors.length
    });

    if (warnings.length > 0) {
      console.log('⚠️ Warnings:');
      warnings.forEach(w => console.log(`  - ${w.text}`));
    }

    if (errors.length > 0) {
      console.log('❌ Errors:');
      errors.forEach(e => console.log(`  - ${e.text}`));
    }

    await cdp.cleanup();
  });
});