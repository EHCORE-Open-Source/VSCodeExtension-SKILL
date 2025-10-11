#!/usr/bin/env node

/**
 * Simple CDP Demo Script
 *
 * This script demonstrates Chrome DevTools Protocol usage
 * with Playwright to automate and monitor web applications.
 *
 * Usage: node tests/simple-cdp-demo.js
 */

const { chromium } = require('playwright');

async function main() {
  console.log('🚀 Starting CDP Automation Demo...\n');

  // Launch browser with DevTools
  const browser = await chromium.launch({
    headless: false,
    args: ['--auto-open-devtools-for-tabs']
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  // Create CDP session
  const client = await context.newCDPSession(page);

  // Enable CDP domains
  await client.send('Performance.enable');
  await client.send('Network.enable');
  await client.send('Runtime.enable');

  console.log('✅ CDP Session initialized\n');

  // Network request tracking
  const requests = [];
  client.on('Network.requestWillBeSent', (params) => {
    requests.push({
      url: params.request.url,
      method: params.request.method,
      timestamp: new Date().toISOString()
    });
  });

  // Console message tracking
  page.on('console', (msg) => {
    console.log(`[Browser Console ${msg.type()}]:`, msg.text());
  });

  // Navigate to Streamlit app
  console.log('🌐 Navigating to http://localhost:8501...\n');

  try {
    await page.goto('http://localhost:8501', {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    console.log('✅ Page loaded successfully\n');

    // Collect performance metrics
    const { metrics } = await client.send('Performance.getMetrics');

    console.log('📊 Performance Metrics:');
    console.log('─────────────────────────────');

    const metricsMap = new Map(metrics.map(m => [m.name, m.value]));

    console.log(`  DOM Nodes: ${metricsMap.get('Nodes') || 0}`);
    console.log(`  JS Heap Size: ${((metricsMap.get('JSHeapUsedSize') || 0) / 1024 / 1024).toFixed(2)} MB`);
    console.log(`  Layout Count: ${metricsMap.get('LayoutCount') || 0}`);
    console.log(`  Script Duration: ${(metricsMap.get('ScriptDuration') || 0).toFixed(2)} ms`);
    console.log('');

    // Get navigation timing
    const navTiming = await client.send('Runtime.evaluate', {
      expression: 'JSON.stringify(performance.timing)',
      returnByValue: true
    });

    const timing = JSON.parse(navTiming.result.value);

    console.log('⏱️  Navigation Timing:');
    console.log('─────────────────────────────');
    console.log(`  DNS Lookup: ${timing.domainLookupEnd - timing.domainLookupStart} ms`);
    console.log(`  TCP Connect: ${timing.connectEnd - timing.connectStart} ms`);
    console.log(`  Request Time: ${timing.responseStart - timing.requestStart} ms`);
    console.log(`  Response Time: ${timing.responseEnd - timing.responseStart} ms`);
    console.log(`  DOM Processing: ${timing.domComplete - timing.domLoading} ms`);
    console.log(`  Total Load Time: ${timing.loadEventEnd - timing.navigationStart} ms`);
    console.log('');

    // Network summary
    console.log('🌐 Network Requests:');
    console.log('─────────────────────────────');
    console.log(`  Total Requests: ${requests.length}`);
    console.log(`  First 5 Requests:`);
    requests.slice(0, 5).forEach((req, i) => {
      const url = req.url.length > 60 ? req.url.substring(0, 60) + '...' : req.url;
      console.log(`    ${i + 1}. ${req.method} ${url}`);
    });
    console.log('');

    // Check for Streamlit elements
    const streamlitApp = await page.locator('[data-testid="stApp"]').count();
    const hasStreamlit = streamlitApp > 0;

    console.log('🎯 Element Detection:');
    console.log('─────────────────────────────');
    console.log(`  Streamlit App Detected: ${hasStreamlit ? '✅ YES' : '❌ NO'}`);

    if (hasStreamlit) {
      const mainContent = await page.locator('[data-testid="stAppViewContainer"]').count();
      console.log(`  Main Content Area: ${mainContent > 0 ? '✅ YES' : '❌ NO'}`);

      const buttons = await page.locator('button').count();
      console.log(`  Buttons Found: ${buttons}`);

      const fileUploader = await page.locator('[data-testid="stFileUploader"]').count();
      console.log(`  File Uploader: ${fileUploader > 0 ? '✅ YES' : '❌ NO'}`);
    }
    console.log('');

    // Take screenshot
    await page.screenshot({
      path: 'test-results/streamlit-screenshot.png',
      fullPage: true
    });
    console.log('📸 Screenshot saved: test-results/streamlit-screenshot.png\n');

    // Test interaction if button exists
    const buttonCount = await page.locator('button').count();
    if (buttonCount > 0) {
      console.log('🖱️  Testing Button Interaction:');
      console.log('─────────────────────────────');

      const startTime = Date.now();
      await page.locator('button').first().click();
      await page.waitForTimeout(500);
      const responseTime = Date.now() - startTime;

      console.log(`  Click Response Time: ${responseTime} ms`);
      console.log('');
    }

    // Wait a bit to observe
    console.log('⏳ Keeping browser open for 5 seconds...\n');
    await page.waitForTimeout(5000);

  } catch (error) {
    console.error('❌ Error:', error.message);
  }

  // Cleanup
  await client.detach();
  await browser.close();

  console.log('✅ Demo completed!\n');
  console.log('📝 Summary:');
  console.log('─────────────────────────────');
  console.log('  This demo showed:');
  console.log('  • CDP session creation');
  console.log('  • Performance metrics collection');
  console.log('  • Network request tracking');
  console.log('  • Navigation timing analysis');
  console.log('  • Element detection');
  console.log('  • Interactive testing');
  console.log('');
}

main().catch(console.error);
