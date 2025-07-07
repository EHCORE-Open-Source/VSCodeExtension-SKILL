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
4. **Rich Documentation**: Enhanced procedure documentation with visual hierarchy
5. **Syntax Highlighting**: Comprehensive highlighting including HEX colors and regex
6. **Outline View**: Shows procedure structure in the outline panel

## Configuration
The extension can be configured via `.vscode/skill.json` in the workspace:
```json
{
  "skill": {
    "autoComplete": true/false,
    "searchFolderPath": "path/to/skill/files"
  }
}
```

## SKILL Function Reference System (8,136 Functions from 22 PDFs)
- **Complete database**: `docs/complete-skill-functions.json` - All 8,136 functions from 22 manuals
- **Complete reference**: `docs/complete-skill-reference.md` - Full documentation (22 categories)
- **Quick reference**: `docs/skill-quick-reference.md` - Common functions only
- **Advanced search**: `python3 scripts/search_skill_advanced.py <function_name>` - Smart search with fuzzy matching
- **Category search**: `python3 scripts/search_skill_advanced.py --category <category>` - Browse by category
- **Auto-extraction**: `python3 scripts/extract_skill_functions.py` - Re-extract from all PDFs
- **Statistics**: `python3 scripts/search_skill_advanced.py --stats` - Show database stats

**Categories Available**: CAI, MAE, OCEAN, Device, Database, Layout, Language, UI, Verification, and 13 more

## 📖 Procedure Documentation System

### Documentation Tags
The extension supports rich documentation for SKILL procedures using special tags in block comments:

```skill
/*
<@summary>
🎯 Main function description
Can be multi-line text explaining the procedure's purpose
</@summary>

<arg1>
📥 Description of the first argument
</arg1>

<arg2>
📥 Description of the second argument (required)
</arg2>

<optArg>
📥 Description of the optional argument
</optArg>

<@return>
📤 Description of the return value
- Success case: what is returned
- Failure case: what is returned
- Special cases and their handling
</@return>

<@note>
⚠️ Important warnings and usage notes
- Usage limitations or conditions
- Performance considerations
- Safety warnings
</@note>

<@example>
💡 Usage example
result = myProcedure(value1 value2 optionalValue)
if(result
    println("Success")
    println("Failed")
)
</@example>
*/
procedure(myProcedure(arg1 arg2 @optional optArg)
    ; procedure body
)
```

### Supported SKILL Syntax Formats
The extension now properly handles various SKILL parameter syntax:

```skill
// 1. Simple optional parameters
procedure(foo(arg1 @optional arg2)
    ; arg2 is optional without default value
)

// 2. Optional parameters with default values
procedure(bar(arg1 @optional (arg2 "default"))
    ; arg2 is optional with default value "default"
)

// 3. Multiple optional parameters
procedure(baz(arg1 @optional arg2 arg3)
    ; Both arg2 and arg3 are optional
)

// 4. Mixed parameter types
procedure(complex(required1 @optional opt1 opt2 @key (key1 keyDefault))
    ; required1: required
    ; opt1, opt2: optional
    ; key1: key argument with default
)
```

### Tag Reference

| Tag | Required | Purpose |
|-----|----------|---------|
| `<@summary>` | ✅ Required | Main function description |
| `<argumentName>` | ✅ Required | Individual argument descriptions |
| `<@return>` | 🔸 Optional | Return value documentation |
| `<@note>` | 🔸 Optional | Important warnings and notes |
| `<@example>` | 🔸 Optional | Usage examples |

### Visual Features
- **🎨 Rich Hover**: Enhanced tooltips with emoji icons and clear sections
- **🎯 Smart Signature Help**: Context-aware parameter assistance
- **📋 Hierarchical Display**: Well-organized information layout
- **⚡ Performance Optimized**: Cached parsing for fast response

### Hover Display Format
```markdown
**🔧 procedure** `functionName`

📋 [Function summary]

---

**📥 Arguments:**
  **`arg1`**  
    [Single-line description with normalized whitespace]

**📥 Optional Arguments:**
  **`arg2 = defaultValue`** *(optional)*  
    [Single-line description for optional parameter]

**📤 Returns:** [Return value description]

**⚠️ Important Notes:** [Warnings and notes]

**💡 Example:**
```skill
[Usage example]
```

---
*💾 File: filename.il:123*
```

### Signature Help Format
```markdown
---

📋 [Function summary]
```

## File Structure
- `src/` - TypeScript source files
- `out/` - Compiled JavaScript output
- `syntax/skill/` - Language grammar definitions
- `src/schema/` - JSON schema for completion configuration
- `vsix/` - Packaged extension files