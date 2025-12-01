# Cadence SKILL Extension for Visual Studio Code

[![Version](https://img.shields.io/badge/version-0.0.11-blue.svg)](https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![VSCode](https://img.shields.io/badge/VSCode-^1.88.0-007ACC.svg)](https://code.visualstudio.com/)

A comprehensive Visual Studio Code extension that provides rich language support for Cadence SKILL (`.il` files), the programming language used in Cadence EDA design tools including Virtuoso, Allegro, and other Cadence platforms.

## ✨ Features

### 🎨 Syntax Highlighting
- **Comprehensive Language Support**: Full syntax highlighting for SKILL language constructs
- **Advanced Pattern Recognition**:
  - Regular expressions (PCRE/REX) with enhanced highlighting
  - 4-level nested bracket color cycling for groups and lookaheads
  - Character set highlighting with range underlines (e.g., `[a-z]`)
  - Octal escape sequence support (`\000` to `\377`)
  - HEX color index display
  - Object and variable highlighting
  - Input/output specification syntax
- **Markdown Integration**: SKILL code block syntax highlighting in Markdown files
- **Tool-Specific Keywords**: Support for Virtuoso OCEAN XL and other Cadence tool-specific functions

### 🔍 IntelliSense & Auto-Completion
- **8,136+ Built-in Functions**: Complete function database extracted from 20 official Cadence SKILL manuals
- **Smart Context-Aware Suggestions**: Auto-completion based on your coding context
- **Configurable Completion**: Customize through `.vscode/skill.json` workspace settings
- **Function Categories**: Organized by CAI, MAE, OCEAN, Device, Database, Layout, Language, UI, Verification, and more

### 📋 Code Navigation
- **Procedure Outline View**: Hierarchical display of all procedures in current file
- **Quick Navigation**: Jump to procedure definitions instantly
- **Breadcrumb Support**: Shows current procedure context in the editor breadcrumb
- **Recursive File Search**: Supports searching across subdirectories in configured paths

### 🔗 File Linking
- **Automatic File Detection**: Recognizes and links SKILL file references
- **Path Intelligence**: Prioritizes searching in configured `searchFolderPath`
- **File Hover Information**:
  - Full resolved file path
  - File size
  - Last modified timestamp
- **Missing File Warnings**: Yellow squiggly underlines for non-existent file paths

### 📖 Rich Documentation
- **Enhanced Hover Tooltips**:
  - Function signatures with parameter details
  - Return type information
  - Usage examples and notes
- **Signature Help**: Real-time parameter assistance while typing function calls
- **Custom Documentation Tags**: Support for special documentation tags in block comments:
  - `<@summary>`: Function description
  - `<argumentName>`: Parameter documentation
  - `<@return>`: Return value description
  - `<@note>`: Important warnings
  - `<@example>`: Usage examples

### 🛠️ Advanced Parameter Support
- **Optional Parameters**: Recognizes `@optional` keyword and default values
- **Keyword Arguments**: Supports `@key` parameters
- **Variadic Functions**: Handles variable-length argument lists
- **Nested Optional Parameters**: Complex parameter pattern recognition

## 📦 Installation

### From VSIX Package
1. Download the latest `.vsix` file from the [releases page](https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/releases)
2. Open VS Code
3. Go to Extensions view (`Ctrl+Shift+X` / `Cmd+Shift+X`)
4. Click the `...` menu → `Install from VSIX...`
5. Select the downloaded `.vsix` file

### From Source
```bash
git clone https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL.git
cd VSCodeExtension-SKILL
npm install
npm run compile
```

## ⚙️ Configuration

Create a `.vscode/skill.json` file in your workspace to configure the extension:

```json
{
  "auto_complete": true,
  "search_folder_path": "./skill",
  "environment": {
    "primary_tool": "virtuoso",
    "tools": {
      "virtuoso": {
        "version": "6.1.8",
        "version_range": "6.1.0~6.1.8",
        "subtools": ["layout", "schematic", "analog", "digital"]
      },
      "allegro": {
        "version": "22.1",
        "version_range": ">=22.1",
        "subtools": ["pcb", "package"]
      }
    }
  },
  "compatibility": {
    "mode": "permissive",
    "allow_universal": true,
    "allow_cross_tool": true,
    "show_version_warnings": true,
    "show_scope_warnings": true,
    "minimum_version": "6.0.0"
  }
}
```

### Configuration Options

| Option | Type | Description |
|--------|------|-------------|
| `auto_complete` | boolean | Enable/disable auto-completion feature |
| `search_folder_path` | string | Path to search for SKILL files (supports recursive search) |
| `environment.primary_tool` | string | Primary Cadence tool (e.g., "virtuoso", "allegro") |
| `environment.tools` | object | Tool-specific version and feature configuration |
| `compatibility.mode` | string | Compatibility checking mode ("strict" or "permissive") |
| `compatibility.allow_universal` | boolean | Allow universal SKILL functions across all versions |
| `compatibility.show_version_warnings` | boolean | Display warnings for version-specific functions |

## 📚 Documentation System

### Writing Documented Procedures

```skill
/*
<@summary>
Calculate the area of a rectangle
Supports both integer and floating-point dimensions
</@summary>

<width>
Width of the rectangle (must be positive)
</width>

<height>
Height of the rectangle (must be positive)
</height>

<unit>
Unit of measurement (optional, defaults to "um")
</unit>

<@return>
Returns the calculated area as a float
Returns nil if invalid dimensions provided
</@return>

<@note>
This function performs basic input validation
Negative or zero dimensions will return nil
</@note>

<@example>
area = calculateArea(10.5 20.0 "mm")
println(area)  ; Output: 210.0
</@example>
*/
procedure(calculateArea(width height @optional (unit "um"))
  when(and(greaterp(width 0) greaterp(height 0))
    times(width height)
  )
)
```

### Supported Tag Reference

- `<@summary>...</@summary>`: Main function description (required)
- `<paramName>...</paramName>`: Individual parameter documentation (required for each param)
- `<@return>...</@return>`: Return value description (optional)
- `<@note>...</@note>`: Important warnings and notes (optional)
- `<@example>...</@example>`: Usage examples (optional)

## 🎯 Supported File Types

- `.il` - SKILL source files
- `.cdsinit` - Cadence initialization files

## 🔧 Development

### Build Commands

```bash
# Compile TypeScript
npm run compile

# Watch mode for development
npm run watch

# Run linter
npm run lint

# Run tests
npm run pretest  # Compile and lint
npm run test     # Run test suite

# Create VSIX package
npm run vscode:prepublish  # Prepare for publishing
./makeVSIX.sh              # Linux/macOS
makeVSIX.bat              # Windows
```

### Project Structure

```
VSCodeExtension-SKILL/
├── src/
│   ├── extension.ts                    # Main entry point
│   ├── skill.completion.ts             # IntelliSense provider
│   ├── skill.outline.ts                # Document symbol provider
│   ├── skill.link.ts                   # File linking
│   ├── skill.procedure.ts              # Procedure navigation & signature help
│   └── builtin-procedures/             # Built-in function database
│       ├── databases/                  # Version-specific databases
│       ├── compatibility-engine.ts     # Version compatibility checker
│       ├── version-matcher.ts          # Version matching logic
│       └── prompt-generator.ts         # IntelliSense prompt generation
├── syntax/skill/                       # TextMate grammar definitions
│   ├── basic.tmLanguage.json          # Basic syntax
│   ├── function.tmLanguage.json       # Function highlighting
│   └── markdown-injection.tmLanguage.json  # Markdown integration
├── docs/
│   ├── complete-skill-functions.json   # 8,136+ function database
│   ├── complete-skill-reference.md     # Full reference documentation
│   └── skill-quick-reference.md        # Quick reference guide
└── out/                                # Compiled output
```

## 📖 SKILL Function Reference

This extension includes a comprehensive database of **8,136+ SKILL functions** extracted from 20 official Cadence manuals, organized into categories:

- **CAI** - Cadence Application Interface
- **MAE** - Model Application Environment
- **OCEAN** - Open Command Environment for Analysis
- **Database** - Database access and manipulation
- **Layout** - Layout-specific functions
- **Language** - Core SKILL language functions
- **UI** - User interface functions
- **Verification** - Design verification tools
- And 12+ more categories...

### Advanced Function Search

```bash
# Search for a specific function
python3 scripts/search_skill_advanced.py functionName

# Browse by category
python3 scripts/search_skill_advanced.py --category Database

# View database statistics
python3 scripts/search_skill_advanced.py --stats

# Re-extract from PDF manuals
python3 scripts/extract_skill_functions.py
```

## 🆕 Release Notes

### Version 0.0.11 (Latest)
- 🎨 Enhanced PCRE/REX syntax highlighting with 4-level nested bracket color cycling
- 🌈 Theme-aware bracket colors (Purple → Yellow → Teal → Green)
- 📐 Character set bracket highlighting with range underline decoration
- 🔢 Octal escape sequence support (`\000` to `\377`) for PCRE and REX
- ✨ Improved escape character highlighting with proper scope assignment
- 🐛 Fixed character range regex to correctly handle octal sequences
- ❌ Removed hexadecimal test (SKILL only supports octal)

### Version 0.0.10
- ✨ Enhanced procedure indexing with recursive subdirectory scanning
- 🔍 Improved file path navigation prioritizing configured `searchFolderPath`
- 📂 Recursive file search for procedure navigation and file links
- 🐛 Fixed breadcrumb navigation to display procedure name throughout entire block
- 📋 Added hover support for file paths with metadata (size, modified time)
- ⚠️ Added diagnostic warnings for non-existent file paths with yellow squiggly underlines

### Version 0.0.9
- 🐛 Fixed signature help for embedded procedures
- 📝 Added Markdown SKILL code block syntax highlighting
- 🔧 Migrated to Node.js build tools

### Version 0.0.8
- 📖 Updated signature help to support block comment documentation
- 🎨 Enhanced input/output specification syntax highlighting
- ✨ Added regex expression syntax highlighting
- 🎨 Added HEX color index highlighting
- 📋 Advanced hover and signature help for procedures
- 🔍 Enhanced object and variable highlighting

### Version 0.0.7
- 🔗 Automatic SKILL file detection and linking
- 🧭 Procedure navigation for quick location switching
- 📝 Basic signature help for procedures
- 🔧 Updated techfile variant keywords

[View complete changelog](CHANGELOG.md)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

### Development Setup
1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/VSCodeExtension-SKILL.git`
3. Install dependencies: `npm install`
4. Make your changes
5. Test your changes: `npm run pretest && npm run test`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built on the [Visual Studio Code Extension API](https://code.visualstudio.com/api)
- SKILL function database extracted from official Cadence documentation
- Special thanks to the EDA community for feedback and contributions

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/issues)
- **Documentation**: [Project Wiki](https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL/wiki)
- **Repository**: [GitHub](https://github.com/EHCORE-Open-Source/VSCodeExtension-SKILL)

---

**Made with ❤️ for the Cadence SKILL community**

*Accelerate your SKILL development with intelligent code assistance!*