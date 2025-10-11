import { defineConfig, devices } from '@playwright/test';
import * as dotenv from 'dotenv';

dotenv.config();

/**
 * Playwright Configuration for Streamlit App Testing
 *
 * This configuration is specifically designed for testing the
 * running Streamlit application without starting a web server.
 */

export default defineConfig({
  testDir: './tests/e2e',
  testMatch: '**/streamlit-app-test.spec.ts',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  timeout: 60000,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'test-results/streamlit-html' }],
    ['json', { outputFile: 'test-results/streamlit-results.json' }]
  ],

  use: {
    baseURL: process.env.STREAMLIT_URL || 'http://localhost:8501',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    headless: false,
    viewport: { width: 1280, height: 720 },
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage'
          ]
        }
      },
    },
  ],

  // No web server - test against running Streamlit instance
  // Make sure Streamlit is running at http://localhost:8501
});