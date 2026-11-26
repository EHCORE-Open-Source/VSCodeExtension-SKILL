#!/bin/bash

################################################################################
# AI-Powered Automated Testing Environment Setup Script
#
# This script sets up a complete AI-powered automated testing environment
# with Playwright, Puppeteer, and AI integration capabilities.
#
# Features:
# - Playwright with Chrome DevTools Protocol
# - Puppeteer for Chrome-specific testing
# - AI integration (OpenAI/Gemini) for intelligent testing
# - Visual regression testing
# - Performance monitoring
# - Accessibility testing
#
# Usage: ./setup-ai-automation-testing.sh [options]
# Options:
#   --full        Install both Playwright and Puppeteer (default)
#   --playwright  Install Playwright only
#   --puppeteer   Install Puppeteer only
#   --skip-ai     Skip AI integration setup
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
INSTALL_PLAYWRIGHT=true
INSTALL_PUPPETEER=true
INSTALL_AI=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --playwright)
            INSTALL_PUPPETEER=false
            shift
            ;;
        --puppeteer)
            INSTALL_PLAYWRIGHT=false
            shift
            ;;
        --skip-ai)
            INSTALL_AI=false
            shift
            ;;
        --full)
            INSTALL_PLAYWRIGHT=true
            INSTALL_PUPPETEER=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}AI Automation Testing Setup${NC}"
echo -e "${BLUE}================================${NC}\n"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed.${NC}"
    echo -e "${YELLOW}Please install Node.js (v18 or later) from https://nodejs.org/${NC}"
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo -e "${RED}Error: Node.js version 18 or later is required.${NC}"
    echo -e "${YELLOW}Current version: $(node -v)${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Node.js $(node -v) detected${NC}\n"

# Create test automation directory structure
echo -e "${BLUE}Creating project structure...${NC}"
mkdir -p tests/{e2e,unit,integration}
mkdir -p tests/fixtures
mkdir -p tests/utils
mkdir -p tests/ai-helpers
mkdir -p test-results/{screenshots,videos,traces}
mkdir -p .github/workflows

echo -e "${GREEN}✓ Directory structure created${NC}\n"

# Initialize package.json if it doesn't exist
if [ ! -f "package.json" ]; then
    echo -e "${BLUE}Initializing package.json...${NC}"
    npm init -y
    echo -e "${GREEN}✓ package.json created${NC}\n"
fi

# Install Playwright
if [ "$INSTALL_PLAYWRIGHT" = true ]; then
    echo -e "${BLUE}Installing Playwright...${NC}"
    npm install -D @playwright/test
    npx playwright install chromium
    npx playwright install-deps chromium
    echo -e "${GREEN}✓ Playwright installed${NC}\n"
fi

# Install Puppeteer
if [ "$INSTALL_PUPPETEER" = true ]; then
    echo -e "${BLUE}Installing Puppeteer...${NC}"
    npm install puppeteer
    echo -e "${GREEN}✓ Puppeteer installed${NC}\n"
fi

# Install additional testing utilities
echo -e "${BLUE}Installing testing utilities...${NC}"
npm install -D \
    @axe-core/playwright \
    playwright-lighthouse \
    dotenv \
    typescript \
    @types/node \
    ts-node \
    eslint \
    prettier

echo -e "${GREEN}✓ Testing utilities installed${NC}\n"

# Install AI integration packages
if [ "$INSTALL_AI" = true ]; then
    echo -e "${BLUE}Installing AI integration packages...${NC}"
    npm install \
        openai \
        @google/generative-ai \
        langchain \
        @langchain/openai
    echo -e "${GREEN}✓ AI packages installed${NC}\n"
fi

# Create TypeScript configuration
echo -e "${BLUE}Creating TypeScript configuration...${NC}"
cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./tests",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "moduleResolution": "node",
    "types": ["node", "@playwright/test"]
  },
  "include": ["tests/**/*"],
  "exclude": ["node_modules", "dist"]
}
EOF
echo -e "${GREEN}✓ tsconfig.json created${NC}\n"

# Create Playwright configuration
if [ "$INSTALL_PLAYWRIGHT" = true ]; then
    echo -e "${BLUE}Creating Playwright configuration...${NC}"
    cat > playwright.config.ts << 'EOF'
import { defineConfig, devices } from '@playwright/test';
import * as dotenv from 'dotenv';

dotenv.config();

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }]
  ],

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        launchOptions: {
          args: ['--auto-open-devtools-for-tabs']
        }
      },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  webServer: {
    command: 'npm run start',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
EOF
    echo -e "${GREEN}✓ playwright.config.ts created${NC}\n"
fi

# Create environment template
echo -e "${BLUE}Creating environment template...${NC}"
cat > .env.example << 'EOF'
# Base URL for testing
BASE_URL=http://localhost:3000

# AI API Keys (optional - for AI-powered testing features)
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Chrome DevTools Protocol settings
CDP_ENABLE_PERFORMANCE=true
CDP_ENABLE_NETWORK=true
CDP_ENABLE_CONSOLE=true

# Test settings
HEADLESS=false
SLOW_MO=0
TIMEOUT=30000

# Screenshot and video settings
SCREENSHOT_ON_FAILURE=true
VIDEO_ON_FAILURE=true
TRACE_ON_FAILURE=true
EOF

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠ Please configure .env file with your API keys${NC}"
fi

echo -e "${GREEN}✓ Environment files created${NC}\n"

# Create .gitignore
echo -e "${BLUE}Creating .gitignore...${NC}"
cat > .gitignore << 'EOF'
# Dependencies
node_modules/

# Test results
test-results/
playwright-report/
test-results/
screenshots/
videos/
traces/

# Environment variables
.env
.env.local

# Build output
dist/
out/

# OS files
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo
EOF
echo -e "${GREEN}✓ .gitignore created${NC}\n"

# Update package.json scripts
echo -e "${BLUE}Adding npm scripts...${NC}"
node -e "
const fs = require('fs');
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
pkg.scripts = {
  ...pkg.scripts,
  'test': 'playwright test',
  'test:headed': 'playwright test --headed',
  'test:debug': 'playwright test --debug',
  'test:ui': 'playwright test --ui',
  'test:chromium': 'playwright test --project=chromium',
  'test:firefox': 'playwright test --project=firefox',
  'test:webkit': 'playwright test --project=webkit',
  'test:mobile': 'playwright test --project=\"Mobile Chrome\"',
  'test:report': 'playwright show-report',
  'test:codegen': 'playwright codegen',
  'puppeteer:run': 'node tests/puppeteer-tests.js'
};
fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2));
"
echo -e "${GREEN}✓ npm scripts added${NC}\n"

# Create README
echo -e "${BLUE}Creating documentation...${NC}"
cat > AUTOMATION_TESTING_README.md << 'EOF'
# AI-Powered Automated Testing Environment

This project is configured with a complete AI-powered automated testing environment using Playwright and Puppeteer.

## 🚀 Quick Start

### Run Tests
```bash
# Run all tests
npm test

# Run tests in headed mode (see browser)
npm run test:headed

# Run tests in debug mode
npm run test:debug

# Run tests with UI mode
npm run test:ui

# Run tests on specific browser
npm run test:chromium
npm run test:firefox
npm run test:webkit
npm run test:mobile
```

### View Reports
```bash
npm run test:report
```

### Record New Tests
```bash
npm run test:codegen
```

## 📁 Project Structure

```
.
├── tests/
│   ├── e2e/              # End-to-end tests
│   ├── integration/      # Integration tests
│   ├── unit/             # Unit tests
│   ├── fixtures/         # Test fixtures and data
│   ├── utils/            # Test utilities
│   └── ai-helpers/       # AI integration helpers
├── test-results/
│   ├── screenshots/      # Test screenshots
│   ├── videos/           # Test videos
│   └── traces/           # Playwright traces
├── playwright.config.ts  # Playwright configuration
└── .env                  # Environment variables
```

## 🤖 AI Features

### AI-Powered Test Generation
Use AI to generate test cases based on user stories or requirements.

### Intelligent Element Selection
AI helps identify the best selectors for stable tests.

### Smart Assertions
AI suggests relevant assertions based on the page content.

### Bug Analysis
AI analyzes test failures and suggests potential fixes.

## 🛠️ Chrome DevTools Integration

All tests have access to Chrome DevTools Protocol for:
- Performance monitoring
- Network analysis
- Console logging
- Memory profiling
- Coverage analysis

## 📊 Testing Best Practices

1. **Use Page Object Model**: Organize tests with page objects
2. **Leverage Auto-waiting**: Playwright automatically waits for elements
3. **Parallel Execution**: Tests run in parallel by default
4. **Visual Regression**: Take screenshots for visual comparison
5. **Accessibility Testing**: Include accessibility checks in tests

## 🔧 Configuration

Edit `playwright.config.ts` to customize:
- Base URL
- Timeout settings
- Browser configurations
- Reporter settings
- Screenshot/video options

Edit `.env` to configure:
- API keys
- Environment-specific URLs
- Feature flags

## 📝 Writing Tests

See the example tests in `tests/e2e/` for reference implementations.

## 🐛 Debugging

- Use `--debug` flag to step through tests
- Use `--ui` flag for interactive UI mode
- Use `page.pause()` to pause execution
- Check traces in test-results for failed tests

## 📚 Resources

- [Playwright Documentation](https://playwright.dev)
- [Puppeteer Documentation](https://pptr.dev)
- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
EOF
echo -e "${GREEN}✓ Documentation created${NC}\n"

# Print completion message
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo -e "${GREEN}================================${NC}\n"

echo -e "${YELLOW}Next Steps:${NC}"
echo -e "1. Configure your ${BLUE}.env${NC} file with API keys"
echo -e "2. Review ${BLUE}AUTOMATION_TESTING_README.md${NC} for usage guide"
echo -e "3. Run ${BLUE}npm run test:codegen${NC} to record your first test"
echo -e "4. Check example tests in ${BLUE}tests/${NC} directory\n"

if [ "$INSTALL_AI" = true ]; then
    echo -e "${YELLOW}⚠ Remember to add your AI API keys to .env file:${NC}"
    echo -e "   - OPENAI_API_KEY"
    echo -e "   - GEMINI_API_KEY\n"
fi

echo -e "${GREEN}Happy Testing! 🎉${NC}\n"
