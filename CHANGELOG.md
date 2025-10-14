# Changelog

All notable changes to the "Cadence SKILL Extension" will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.11] - 2025-01-15

### Added
- **Embedded Language Syntax Highlighting**: Support for YAML, Markdown, and JSON syntax highlighting within SKILL block comments (`/* */`)
  - Use triple backticks with language identifier (e.g., ` ```yaml `, ` ```markdown `, ` ```json `)
  - Automatic syntax highlighting for embedded code blocks
  - See [docs/EMBEDDED_LANGUAGE_SYNTAX.md](docs/EMBEDDED_LANGUAGE_SYNTAX.md) for usage guide
- **Test Helper Utilities**: New test helper functions in `tests/utils/test-helpers.ts`
  - `createModernFunction()` - Create complete modern format test function definitions
  - `createLegacyFunction()` - Create complete legacy format test function definitions
  - `createArgument()` - Create test argument objects with defaults
- **Comprehensive Documentation**:
  - [TYPESCRIPT_CONFIG.md](docs/TYPESCRIPT_CONFIG.md) - TypeScript configuration guide
  - [VSCODE_TYPESCRIPT_SETUP.md](docs/VSCODE_TYPESCRIPT_SETUP.md) - VSCode setup instructions
  - [EMBEDDED_LANGUAGE_SYNTAX.md](docs/EMBEDDED_LANGUAGE_SYNTAX.md) - Embedded syntax feature guide
  - [TYPESCRIPT_FIX_SUMMARY.md](TYPESCRIPT_FIX_SUMMARY.md) - Complete fix summary
  - [VSCODE_ERRORS_FIX.md](VSCODE_ERRORS_FIX.md) - Quick troubleshooting guide

### Changed
- **TypeScript Configuration Restructure**: Split configuration for better IDE support
  - `tsconfig.json` - Main extension source code (`src/` directory)
  - `tsconfig.tests.json` - Test files (`tests/` directory) with DOM types
- **ESLint Configuration**: Excluded `tests/` directory from ESLint checking to reduce noise

### Fixed
- **29 TypeScript Compilation Errors**: All type errors in test files resolved
  - Fixed implicit `any` type errors in test files
  - Fixed `error` type handling in catch blocks
  - Fixed `document` API availability in browser tests
  - Fixed private method access in `function-reviewer.ts`
  - Fixed `string | undefined` type safety in `chrome-devtools-helper.ts`
- **VSCode F5 Debug Mode**: Now works correctly with proper TypeScript project configuration
- **Function Description Type Error**: Fixed `getFunctionDescription()` signature in `skill.completion.ts`

### Developer Experience
- ✅ VSCode F5 debug mode fully functional
- ✅ TypeScript IntelliSense working correctly for both `src/` and `tests/`
- ✅ Zero compilation errors in both command line and VSCode
- ✅ Improved test writing experience with helper utilities

## [0.0.10] - 2024-10-09

### Added
- Recursive subdirectory scanning support in `searchFolderPath` for procedure indexing
- File path hover information displaying full resolved path, file size, and last modified time
- Recursive file search functionality for both procedure navigation and file link features
- File path diagnostic warnings with yellow squiggly underlines for non-existent files

### Changed
- Improved file path navigation to prioritize searching in configured `searchFolderPath` from `.vscode/skill.json`

### Fixed
- Breadcrumb navigation now displays procedure name throughout entire procedure block instead of only on definition line

## [0.0.9] - 2024-07-09

### Added
- Markdown SKILL code block syntax highlighting feature
- Node.js tools support for compiling and testing

### Fixed
- Signature help function now works correctly for embedded procedures

## [0.0.8] - 2024-06-15

### Added
- Regular expression syntax highlighting
- HEX color index highlighting support
- Advanced hover and signature help for procedure descriptions
- Block comment support for procedure signature help

### Changed
- Enhanced input and output specification syntax highlighting
- Improved object and variable highlighting for better readability

### Removed
- Table object key item syntax highlighting (removed for consistency)

## [0.0.7] - 2024-05-20

### Added
- Automatic detection and linking of SKILL files
- Procedure navigation feature for quickly switching to corresponding procedure locations
- Signature help for procedures (limited to line comments)

### Changed
- Updated techfile variant keywords

### Known Issues
- Signature help cannot support block comments (fixed in 0.0.8)

## [0.0.6] - 2024-04-10

### Added
- Simple procedure outline feature for document symbol navigation

## [0.0.5] - 2024-03-15

### Fixed
- Syntax highlighting for `axlGetJobPolicy` function
- Syntax highlighting for `ddDelete` function

## [0.0.4] - 2024-02-20

### Added
- Window function syntax highlighting (previously missing)
- Unknown function support:
  - `selectResults`
  - `sevModelItemChanged`
  - `sevSetTableItem`
  - `sevSetVariablesFromForm`
  - `sevSetOutputsFromForm`
  - `apaStartCB`

## [0.0.3] - 2024-01-25

### Added
- Virtuoso OCEAN XL functional color marking support

## [0.0.2] - 2024-01-10

### Changed
- Expanded Virtuoso built-in function color marking coverage

## [0.0.1] - 2024-01-01

### Added
- Initial release
- Basic SKILL language syntax highlighting
- Support for `.il` and `.cdsinit` file extensions
- Basic language configuration

---

## Legend

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security vulnerability fixes

## Links

- [Repository](https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL)
- [Issues](https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/issues)
- [Releases](https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/releases)

[Unreleased]: https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/compare/v0.0.11...HEAD
[0.0.11]: https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/compare/v0.0.10...v0.0.11
[0.0.10]: https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/compare/v0.0.9...v0.0.10
[0.0.9]: https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/compare/v0.0.8...v0.0.9
[0.0.8]: https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/compare/v0.0.7...v0.0.8
[0.0.7]: https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/compare/v0.0.6...v0.0.7
[0.0.6]: https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/compare/v0.0.5...v0.0.6
[0.0.5]: https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/releases/tag/v0.0.1
