# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This is a Visual Studio Code extension that provides language support for Cadence SKILL (.il files). The extension includes syntax highlighting, code completion, outline view, procedure navigation, and signature help for the SKILL programming language used in Cadence design tools.

## Development Commands
```bash
# Build the extension
npm run compile

# Watch mode for development
npm run watch

# Run linting
npm run lint

# Run tests (requires compilation first)
npm run pretest  # Compiles and lints
npm run test     # Runs vscode-test

# Package for distribution
npm run vscode:prepublish  # Prepares for publishing
```

## Architecture
- **Main entry point**: `src/extension.ts` - activates all feature modules
- **Core modules**:
  - `skill.completion.ts` - Provides IntelliSense and auto-completion
  - `skill.outline.ts` - Document symbol provider for outline view
  - `skill.link.ts` - File linking functionality
  - `skill.procedure.ts` - Procedure navigation and signature help
- **Configuration**: `src/config/skill.completion.json` - Language completion database
- **Syntax definitions**: `syntax/skill/` - TextMate grammar files for syntax highlighting

## Key Features
1. **Language Support**: Recognizes `.il` and `.cdsinit` files as Cadence SKILL
2. **Auto-completion**: Configurable via `.vscode/skill.json` in workspace
3. **Procedure Navigation**: Jump to procedure definitions and get signature help
4. **Syntax Highlighting**: Comprehensive highlighting including HEX colors and regex
5. **Outline View**: Shows procedure structure in the outline panel

## Configuration
The extension can be configured via `.vscode/skill.json` in the workspace:
```json
{
  "skill": {
    "autoComplete": true/false
  }
}
```

## File Structure
- `src/` - TypeScript source files
- `out/` - Compiled JavaScript output
- `syntax/skill/` - Language grammar definitions
- `src/schema/` - JSON schema for completion configuration
- `vsix/` - Packaged extension files