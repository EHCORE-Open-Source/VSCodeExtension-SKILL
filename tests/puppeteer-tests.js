/**
 * Puppeteer Example Tests
 *
 * This file demonstrates Puppeteer-specific features and Chrome DevTools integration.
 * Run with: npm run puppeteer:run
 */

const puppeteer = require('puppeteer');
const fs = require('fs').promises;
const path = require('path');

/**
 * Test: Basic page navigation and screenshots
 */
async function testBasicNavigation() {
  console.log('\n🧪 Test: Basic Navigation with Screenshots');

  const browser = await puppeteer.launch({
    headless: false,
    devtools: true,
    args: ['--auto-open-devtools-for-tabs']
  });

  const page = await browser.newPage();

  // Set viewport
  await page.setViewport({ width: 1920, height: 1080 });

  // Navigate
  await page.goto('https://example.com', { waitUntil: 'networkidle2' });

  // Take screenshot
  await page.screenshot({
    path: 'test-results/screenshots/puppeteer-example.png',
    fullPage: true
  });

  console.log('✓ Screenshot saved');

  // Generate PDF
  await page.pdf({
    path: 'test-results/puppeteer-example.pdf',
    format: 'A4'
  });

  console.log('✓ PDF generated');

  await browser.close();
}

/**
 * Test: Performance monitoring with Chrome DevTools Protocol
 */
async function testPerformanceMonitoring() {
  console.log('\n🧪 Test: Performance Monitoring');

  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  // Enable Performance monitoring
  const client = await page.target().createCDPSession();
  await client.send('Performance.enable');

  // Start tracing
  await page.tracing.start({
    path: 'test-results/traces/puppeteer-trace.json',
    screenshots: true
  });

  // Navigate
  await page.goto('https://example.com', { waitUntil: 'networkidle2' });

  // Get metrics
  const metrics = await page.metrics();
  console.log('Performance Metrics:', metrics);

  // Get DevTools metrics
  const performanceMetrics = await client.send('Performance.getMetrics');
  console.log('DevTools Metrics:', performanceMetrics.metrics);

  // Stop tracing
  await page.tracing.stop();

  // Get performance timing
  const performanceTiming = JSON.parse(
    await page.evaluate(() => JSON.stringify(window.performance.timing))
  );

  console.log('Navigation Timing:', {
    domContentLoaded: performanceTiming.domContentLoadedEventEnd - performanceTiming.navigationStart,
    loadComplete: performanceTiming.loadEventEnd - performanceTiming.navigationStart,
    firstPaint: performanceTiming.responseStart - performanceTiming.navigationStart
  });

  await browser.close();
}

/**
 * Test: Network request interception and modification
 */
async function testNetworkInterception() {
  console.log('\n🧪 Test: Network Request Interception');

  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  // Track all requests
  const requests = [];
  page.on('request', request => {
    requests.push({
      url: request.url(),
      method: request.method(),
      resourceType: request.resourceType()
    });
  });

  // Intercept and block images
  await page.setRequestInterception(true);
  page.on('request', request => {
    if (request.resourceType() === 'image') {
      request.abort();
    } else {
      request.continue();
    }
  });

  await page.goto('https://example.com', { waitUntil: 'networkidle2' });

  console.log(`Total requests: ${requests.length}`);
  console.log('Request breakdown:', {
    documents: requests.filter(r => r.resourceType === 'document').length,
    scripts: requests.filter(r => r.resourceType === 'script').length,
    stylesheets: requests.filter(r => r.resourceType === 'stylesheet').length,
    images: requests.filter(r => r.resourceType === 'image').length,
    xhr: requests.filter(r => r.resourceType === 'xhr').length
  });

  await browser.close();
}

/**
 * Test: Console log monitoring
 */
async function testConsoleMonitoring() {
  console.log('\n🧪 Test: Console Monitoring');

  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  const consoleLogs = [];
  page.on('console', msg => {
    consoleLogs.push({
      type: msg.type(),
      text: msg.text(),
      location: msg.location()
    });
  });

  // Trigger some console output
  await page.goto('https://example.com');
  await page.evaluate(() => {
    console.log('Test log message');
    console.warn('Test warning');
    console.error('Test error');
  });

  console.log('Console Messages:', consoleLogs);

  await browser.close();
}

/**
 * Test: JavaScript coverage analysis
 */
async function testCodeCoverage() {
  console.log('\n🧪 Test: Code Coverage Analysis');

  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  // Start JS coverage
  await page.coverage.startJSCoverage();
  await page.coverage.startCSSCoverage();

  await page.goto('https://example.com', { waitUntil: 'networkidle2' });

  // Stop coverage
  const [jsCoverage, cssCoverage] = await Promise.all([
    page.coverage.stopJSCoverage(),
    page.coverage.stopCSSCoverage()
  ]);

  // Calculate coverage
  let totalBytes = 0;
  let usedBytes = 0;

  for (const entry of [...jsCoverage, ...cssCoverage]) {
    totalBytes += entry.text.length;
    for (const range of entry.ranges) {
      usedBytes += range.end - range.start - 1;
    }
  }

  const coveragePercent = ((usedBytes / totalBytes) * 100).toFixed(2);
  console.log(`Code Coverage: ${coveragePercent}%`);
  console.log(`Used: ${(usedBytes / 1024).toFixed(2)} KB`);
  console.log(`Total: ${(totalBytes / 1024).toFixed(2)} KB`);

  // Save detailed coverage
  await fs.writeFile(
    'test-results/coverage-report.json',
    JSON.stringify({ jsCoverage, cssCoverage }, null, 2)
  );

  await browser.close();
}

/**
 * Test: Device emulation
 */
async function testDeviceEmulation() {
  console.log('\n🧪 Test: Device Emulation');

  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  // Emulate iPhone 12
  await page.emulate(puppeteer.devices['iPhone 12']);

  await page.goto('https://example.com', { waitUntil: 'networkidle2' });

  await page.screenshot({
    path: 'test-results/screenshots/mobile-view.png',
    fullPage: true
  });

  console.log('✓ Mobile screenshot saved');

  // Test different devices
  const devices = ['iPad Pro', 'Pixel 5', 'Galaxy S9+'];

  for (const deviceName of devices) {
    await page.emulate(puppeteer.devices[deviceName]);
    await page.goto('https://example.com', { waitUntil: 'networkidle2' });

    const screenshot = `test-results/screenshots/${deviceName.replace(/\s+/g, '-').toLowerCase()}.png`;
    await page.screenshot({ path: screenshot, fullPage: true });

    console.log(`✓ ${deviceName} screenshot saved`);
  }

  await browser.close();
}

/**
 * Test: Network conditions simulation
 */
async function testNetworkThrottling() {
  console.log('\n🧪 Test: Network Throttling');

  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  // Simulate slow 3G
  const client = await page.target().createCDPSession();
  await client.send('Network.emulateNetworkConditions', {
    offline: false,
    downloadThroughput: (500 * 1024) / 8, // 500kb/s
    uploadThroughput: (500 * 1024) / 8,
    latency: 400 // 400ms
  });

  const startTime = Date.now();
  await page.goto('https://example.com', { waitUntil: 'networkidle2' });
  const loadTime = Date.now() - startTime;

  console.log(`Page load time on slow 3G: ${loadTime}ms`);

  await browser.close();
}

/**
 * Test: Automated form filling and submission
 */
async function testFormAutomation() {
  console.log('\n🧪 Test: Form Automation');

  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto('https://example.com/form', { waitUntil: 'networkidle2' });

  // Fill form
  await page.type('#name', 'John Doe', { delay: 100 });
  await page.type('#email', 'john@example.com', { delay: 100 });
  await page.select('#country', 'US');
  await page.click('#subscribe');

  // Take screenshot before submit
  await page.screenshot({
    path: 'test-results/screenshots/form-filled.png'
  });

  // Submit form
  await page.click('button[type="submit"]');
  await page.waitForNavigation({ waitUntil: 'networkidle2' });

  console.log('✓ Form submitted successfully');

  await browser.close();
}

/**
 * Main test runner
 */
async function runAllTests() {
  console.log('🚀 Starting Puppeteer Tests\n');
  console.log('=================================');

  try {
    await testBasicNavigation();
    await testPerformanceMonitoring();
    await testNetworkInterception();
    await testConsoleMonitoring();
    await testCodeCoverage();
    await testDeviceEmulation();
    await testNetworkThrottling();
    // await testFormAutomation(); // Commented out as it needs a real form

    console.log('\n=================================');
    console.log('✅ All tests completed successfully!');
  } catch (error) {
    console.error('\n❌ Test failed:', error);
    process.exit(1);
  }
}

// Run tests
runAllTests();
