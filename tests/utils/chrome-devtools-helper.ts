/**
 * Chrome DevTools Protocol Helper
 *
 * Provides advanced Chrome DevTools integration for performance monitoring,
 * network analysis, and console tracking during automated tests.
 */

import { Page, CDPSession } from '@playwright/test';

export interface PerformanceMetrics {
  timestamp: number;
  documents: number;
  frames: number;
  jsEventListeners: number;
  nodes: number;
  layoutCount: number;
  recalcStyleCount: number;
  layoutDuration: number;
  recalcStyleDuration: number;
  scriptDuration: number;
  taskDuration: number;
  jsHeapUsedSize: number;
  jsHeapTotalSize: number;
}

export interface NetworkRequest {
  url: string;
  method: string;
  status?: number;
  type: string;
  size: number;
  time: number;
  timestamp: number;
}

export interface ConsoleMessage {
  type: 'log' | 'info' | 'warn' | 'error' | 'debug';
  text: string;
  timestamp: number;
  stackTrace?: string;
}

export class ChromeDevToolsHelper {
  private client?: CDPSession;
  private networkRequests: NetworkRequest[] = [];
  private consoleMessages: ConsoleMessage[] = [];
  private performanceMetrics: PerformanceMetrics[] = [];

  /**
   * Initialize CDP session and enable monitoring
   */
  async initialize(page: Page): Promise<void> {
    this.client = await page.context().newCDPSession(page);

    // Enable various CDP domains
    await this.client.send('Performance.enable');
    await this.client.send('Network.enable');
    await this.client.send('Runtime.enable');
    await this.client.send('Log.enable');

    // Set up network monitoring
    this.client.on('Network.requestWillBeSent', (params) => {
      this.networkRequests.push({
        url: params.request.url,
        method: params.request.method,
        type: params.type,
        size: 0,
        time: 0,
        timestamp: params.timestamp,
      });
    });

    this.client.on('Network.loadingFinished', (params) => {
      const request = this.networkRequests.find(
        r => r.timestamp === params.timestamp
      );
      if (request) {
        request.size = params.encodedDataLength;
      }
    });

    // Set up console monitoring
    page.on('console', (msg) => {
      this.consoleMessages.push({
        type: msg.type() as any,
        text: msg.text(),
        timestamp: Date.now(),
      });
    });
  }

  /**
   * Collect current performance metrics
   */
  async collectPerformanceMetrics(): Promise<PerformanceMetrics> {
    if (!this.client) {
      throw new Error('CDP session not initialized');
    }

    const { metrics } = await this.client.send('Performance.getMetrics');

    const metricsMap = new Map(
      metrics.map(m => [m.name, m.value])
    );

    const performanceMetrics: PerformanceMetrics = {
      timestamp: Date.now(),
      documents: metricsMap.get('Documents') || 0,
      frames: metricsMap.get('Frames') || 0,
      jsEventListeners: metricsMap.get('JSEventListeners') || 0,
      nodes: metricsMap.get('Nodes') || 0,
      layoutCount: metricsMap.get('LayoutCount') || 0,
      recalcStyleCount: metricsMap.get('RecalcStyleCount') || 0,
      layoutDuration: metricsMap.get('LayoutDuration') || 0,
      recalcStyleDuration: metricsMap.get('RecalcStyleDuration') || 0,
      scriptDuration: metricsMap.get('ScriptDuration') || 0,
      taskDuration: metricsMap.get('TaskDuration') || 0,
      jsHeapUsedSize: metricsMap.get('JSHeapUsedSize') || 0,
      jsHeapTotalSize: metricsMap.get('JSHeapTotalSize') || 0,
    };

    this.performanceMetrics.push(performanceMetrics);
    return performanceMetrics;
  }

  /**
   * Get navigation timing metrics
   */
  async getNavigationTiming(): Promise<any> {
    if (!this.client) {
      throw new Error('CDP session not initialized');
    }

    const result = await this.client.send('Runtime.evaluate', {
      expression: 'JSON.stringify(performance.timing)',
      returnByValue: true,
    });

    return JSON.parse(result.result.value);
  }

  /**
   * Get Core Web Vitals
   */
  async getCoreWebVitals(): Promise<{
    LCP?: number;
    FID?: number;
    CLS?: number;
    FCP?: number;
    TTFB?: number;
  }> {
    if (!this.client) {
      throw new Error('CDP session not initialized');
    }

    const result = await this.client.send('Runtime.evaluate', {
      expression: `
        (function() {
          const vitals = {};

          // Get performance entries
          const entries = performance.getEntriesByType('navigation')[0];
          if (entries) {
            vitals.TTFB = entries.responseStart - entries.requestStart;
          }

          // Get paint timing
          const paintEntries = performance.getEntriesByType('paint');
          const fcp = paintEntries.find(e => e.name === 'first-contentful-paint');
          if (fcp) vitals.FCP = fcp.startTime;

          return vitals;
        })()
      `,
      returnByValue: true,
    });

    return result.result.value;
  }

  /**
   * Monitor network requests
   */
  getNetworkRequests(): NetworkRequest[] {
    return [...this.networkRequests];
  }

  /**
   * Filter network requests by criteria
   */
  filterNetworkRequests(filter: {
    method?: string;
    type?: string;
    minSize?: number;
    minTime?: number;
  }): NetworkRequest[] {
    return this.networkRequests.filter(request => {
      if (filter.method && request.method !== filter.method) return false;
      if (filter.type && request.type !== filter.type) return false;
      if (filter.minSize && request.size < filter.minSize) return false;
      if (filter.minTime && request.time < filter.minTime) return false;
      return true;
    });
  }

  /**
   * Get console messages
   */
  getConsoleMessages(type?: ConsoleMessage['type']): ConsoleMessage[] {
    if (type) {
      return this.consoleMessages.filter(msg => msg.type === type);
    }
    return [...this.consoleMessages];
  }

  /**
   * Check for console errors
   */
  hasConsoleErrors(): boolean {
    return this.consoleMessages.some(msg => msg.type === 'error');
  }

  /**
   * Get performance summary
   */
  getPerformanceSummary(): {
    totalRequests: number;
    totalSize: number;
    slowestRequests: NetworkRequest[];
    largestRequests: NetworkRequest[];
    errorCount: number;
    warningCount: number;
    avgScriptDuration: number;
    avgLayoutDuration: number;
  } {
    const totalRequests = this.networkRequests.length;
    const totalSize = this.networkRequests.reduce(
      (sum, req) => sum + req.size, 0
    );

    const sortedByTime = [...this.networkRequests].sort(
      (a, b) => b.time - a.time
    );
    const sortedBySize = [...this.networkRequests].sort(
      (a, b) => b.size - a.size
    );

    const errorCount = this.consoleMessages.filter(
      msg => msg.type === 'error'
    ).length;
    const warningCount = this.consoleMessages.filter(
      msg => msg.type === 'warn'
    ).length;

    const avgScriptDuration = this.performanceMetrics.length > 0
      ? this.performanceMetrics.reduce(
          (sum, m) => sum + m.scriptDuration, 0
        ) / this.performanceMetrics.length
      : 0;

    const avgLayoutDuration = this.performanceMetrics.length > 0
      ? this.performanceMetrics.reduce(
          (sum, m) => sum + m.layoutDuration, 0
        ) / this.performanceMetrics.length
      : 0;

    return {
      totalRequests,
      totalSize,
      slowestRequests: sortedByTime.slice(0, 5),
      largestRequests: sortedBySize.slice(0, 5),
      errorCount,
      warningCount,
      avgScriptDuration,
      avgLayoutDuration,
    };
  }

  /**
   * Enable code coverage
   */
  async startCoverage(): Promise<void> {
    if (!this.client) {
      throw new Error('CDP session not initialized');
    }

    await this.client.send('Profiler.enable');
    await this.client.send('Profiler.startPreciseCoverage', {
      callCount: true,
      detailed: true,
    });
  }

  /**
   * Stop and collect code coverage
   */
  async stopCoverage(): Promise<any> {
    if (!this.client) {
      throw new Error('CDP session not initialized');
    }

    const result = await this.client.send('Profiler.takePreciseCoverage');
    await this.client.send('Profiler.stopPreciseCoverage');
    await this.client.send('Profiler.disable');

    return result;
  }

  /**
   * Clear all collected data
   */
  clearData(): void {
    this.networkRequests = [];
    this.consoleMessages = [];
    this.performanceMetrics = [];
  }

  /**
   * Cleanup and close CDP session
   */
  async cleanup(): Promise<void> {
    if (this.client) {
      await this.client.detach();
      this.client = undefined;
    }
    this.clearData();
  }
}

/**
 * Factory function for creating Chrome DevTools helper
 */
export async function createCDPHelper(page: Page): Promise<ChromeDevToolsHelper> {
  const helper = new ChromeDevToolsHelper();
  await helper.initialize(page);
  return helper;
}
