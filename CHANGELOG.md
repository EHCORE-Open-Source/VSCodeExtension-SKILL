# Changelog

All notable changes to the "Cadence SKILL Extension" will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/compare/v0.0.10...HEAD
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
