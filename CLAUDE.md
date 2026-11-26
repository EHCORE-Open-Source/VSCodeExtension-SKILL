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

# Create VSIX package
# Windows:
makeVSIX.bat  # Creates extension package in vsix/ folder

# Linux/macOS:
./makeVSIX.sh  # Creates extension package in vsix/ folder
chmod +x makeVSIX.sh  # Make script executable (if needed)

# Manual command (cross-platform):
vsce package --out vsix  # Direct command alternative
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

## SKILL Function Reference System (8,136+ Functions from 20 PDFs)
- **Cadence manual content is copyrighted and is not stored in this repository** (no `docs/`, no manual extracts, not even in history). The hover feature loads an optional local `docs/complete-skill-functions.json` if a user generates it from their own licensed manuals; it is git-ignored.
- **Advanced search**: `python3 scripts/search_skill_advanced.py <function_name>` - Smart search with fuzzy matching
- **Category search**: `python3 scripts/search_skill_advanced.py --category <category>` - Browse by category
- **Auto-extraction**: `python3 scripts/extract_skill_functions.py` - Re-extract from all PDFs
- **Statistics**: `python3 scripts/search_skill_advanced.py --stats` - Show database stats

**Categories Available**: CAI, MAE, OCEAN, Device, Database, Layout, Language, UI, Verification, and 13 more

## 🚀 Advanced PDF/HTML Parser System

### Overview
A powerful PDF/HTML parser system that processes SKILL documentation with structural awareness, automatic categorization, and comprehensive function extraction capabilities.

### Core Parser: `scripts/skill_pdf_html_parser.py`

#### **Key Features**
1. **Structure-Aware Parsing**: Uses `pdftotext -bbox` to preserve document layout and positioning
2. **Hierarchical Categorization**: Automatic detection of document structure (2-4+ levels deep)
3. **Advanced Parameter Analysis**: Comprehensive SKILL parameter pattern recognition
4. **Special Function Handling**: Intelligent processing of unique SKILL function patterns
5. **Multi-Document Support**: Consistent parsing across all 20 SKILL PDF documents

#### **Function Extraction Capabilities**

##### **1. Standard Function Parsing**
```python
# Basic function signature
functionName( parameters ) => returnType

# Complex parameter patterns
buildString( l_strings [ S_glueCharacters ] ) => t_string
nearlyEqual( n_val1 n_val2 [ f_relTolerance [ f_absTolerance ] ] ) => t/nil
pcreGenCompileOptBits( [ ?caseLess g_setCaseLessp ] [ ?multiLine g_setMultiLinep ] ... ) => x_resultOptBits
```

##### **2. Function Overload Detection**
Automatically identifies and extracts multiple overloads for functions like `append`:
```python
# Three overloads detected:
append( l_list1 l_list2 ) => l_result
append( o_table g_assoc ) => o_table  
append( o_table1 o_table2 ) => o_newTable
```

##### **3. Special Function Patterns**

###### **Similar Function Groups**
- **`vi, vii, vil`**: Detected as 3 separate functions with individual examples
  ```python
  vi( [ S_filename ] ) => t     # Examples: vi("test.il"), vi()
  vii( [ S_filename ] ) => t    # Examples: vii("test.il"), vii()
  vil( [ S_filename ] ) => t    # Examples: vil("test.il"), vil()
  ```

###### **Car/CDR Function Series**
- **Complete 30-function series**: `caar, caaar, caaaar, caaadr, caadar, caaddr, caadr, cadar, cadaar, cadadr, caddar, cadddr, caddr, cadr, car, cdaar, cdaaar, cdaadr, cdadar, cdaddr, cdadr, cdar, cddaar, cddadr, cddar, cdddar, cddddr, cdddr, cddr, cdr`
- **Unified signature**: `functionName( l_list ) => g_result`

###### **Template Functions**
- **`make_<name>`**: Generates `make_myStruct`, `make_abc`, `make_customType`
  ```python
  make_<name>( ... g_args ) => r_defstruct
  ```
- **`copy_<name>`**: Generates `copy_hello123`, `copy_myData`, `copy_testStruct`
  ```python
  copy_<name>( r_source ) => r_defstruct
  ```

###### **setf Helper Functions**
- **Dynamic extraction**: Reads "setf Helper Functions" table from documentation
- **Generated functions**: `setf_car`, `setf_cdr`, `setf_nth`, `setf_get`, `setf_getq`, `setf_arrayref`, `setf_symbol-value`, `setf_symbol-function`
  ```python
  setf_<helper>( g_place g_newValue ) => g_newValue
  ```

#### **SKILL Data Type System**
Based on official SKILL documentation "Identifiers Used to Denote Data Types":

| Prefix | Internal Name | Data Type | Examples |
|--------|---------------|-----------|----------|
| `a_` | array | array | `a_vectorArray` |
| `l_` | list | linked list | `l_list1`, `l_strings` |
| `t_` | string | character string | `t_string`, `t_filename` |
| `n_` | number | integer/float | `n_val1`, `n_modifier` |
| `f_` | flonum | floating-point | `f_relTolerance` |
| `g_` | general | any data type | `g_element`, `g_args` |
| `s_` | symbol | symbol | `s_variable`, `s_name` |
| `S_` | stringSymbol | symbol or string | `S_glueCharacters` |
| `o_` | userType | user-defined type | `o_table`, `o_comPatObj` |
| `r_` | defstruct | defstruct | `r_source`, `r_defstruct` |
| `p_` | port | I/O port | `p_port` |
| `x_` | integer | integer number | `x_size`, `x_options` |
| `u_` | function | function object | `u_function` |

*Plus 15+ additional type prefixes including `d_` (database), `e_` (environment), `b_` (DDPI object), etc.*

#### **Parameter Classification System**
```python
class ParameterType(Enum):
    REQUIRED = "required"     # Standard required parameters
    OPTIONAL = "optional"     # [ ] enclosed parameters  
    VARIADIC = "variadic"     # ... parameters
    KEYWORD = "keyword"       # ?keyword parameters
```

#### **Hierarchical Categorization System**

##### **Category Structure**
```python
@dataclass
class FunctionCategory:
    document_name: str        # "Cadence SKILL Language Reference"
    category_path: List[str]  # ["List", "Functions"] 
    level: int               # 1-4+ depth level
    full_path: str          # "Cadence SKILL Language Reference > List > Functions"
```

##### **Level Detection Algorithm**
- **Level 1**: Font >18pt, x<50px (Main chapters)
- **Level 2**: Font >16pt, x<70px (Major sections) 
- **Level 3**: Font >14pt, x<90px (Subsections)
- **Level 4+**: Font >12pt, x<110px (Detailed categories)

##### **Category Examples**
```
📚 Cadence SKILL Language Reference (164+ functions)
  📁 List Functions (8 functions)
    • append, car, cdr, cons, length, list, reverse, removeListDuplicates
  📁 Arithmetic Functions (5+ functions)  
    • abs, +, -, *, /, nearlyEqual
  📁 String Functions (4+ functions)
    • buildString, parseString, lowerCase, upperCase
  📁 setf Helper Functions (8 functions)
    • setf_car, setf_cdr, setf_nth, setf_get, setf_getq, setf_arrayref

📚 Cadence User Interface SKILL Reference  
  📁 User Entry Functions
    📁 Nesting Enterfunctions
      • applyEnterFun, ...
```

#### **Usage Examples**

##### **Basic Function Extraction**
```bash
# Extract all functions from a single PDF
python3 scripts/skill_pdf_html_parser.py --input docs/pdfs/sklangref.pdf --output /tmp/functions.json

# Extract with category information
python3 scripts/skill_pdf_html_parser.py --input docs/pdfs/sklangref.pdf --categories --output /tmp/categorized_functions.json
```

##### **Batch Processing**
```bash
# Process all 22 SKILL PDFs
python3 scripts/skill_pdf_html_parser.py --batch --input-dir docs/pdfs/ --output-dir docs/extracted/

# Generate category hierarchy report
python3 scripts/skill_pdf_html_parser.py --hierarchy-report --input-dir docs/pdfs/ --output docs/category_hierarchy.md
```

##### **Integration with Main Extractor**
```python
# In extract_skill_functions.py
from skill_pdf_html_parser import SkillPDFHTMLParser

parser = SkillPDFHTMLParser()
functions = parser.extract_functions_from_pdf("sklangref.pdf")
categorized_functions = parser.extract_with_categories("sklangref.pdf")
```

#### **Testing & Validation**

##### **Test Cases Coverage**
1. **Parameter Pattern Tests**
   - ✅ Optional parameters: `[ S_glueCharacters ]`
   - ✅ Nested optional: `[ f_relTolerance [ f_absTolerance ] ]`
   - ✅ Variadic arguments: `[ ... g_arg1 ]`
   - ✅ Keyword arguments: `[ ?caseLess g_setCaseLessp ]`
   - ✅ Mixed patterns: Complex multi-parameter combinations

2. **Special Function Tests**
   - ✅ Car/CDR series: All 30 functions generated correctly
   - ✅ Vi series: 3 separate functions with proper examples
   - ✅ Template functions: `make_<name>`, `copy_<name>` variations
   - ✅ setf helpers: Dynamic table extraction and function generation

3. **Categorization Tests**
   - ✅ Multi-level hierarchy: 2-4+ level deep structures
   - ✅ Function assignment: Correct category for each function
   - ✅ Cross-document consistency: Uniform categorization across PDFs

4. **Overload Detection Tests**
   - ✅ Multiple signatures: `append` function's 3 overloads
   - ✅ Parameter type differences: Different parameter combinations
   - ✅ Return type variations: Different return types per overload

##### **Validation Commands**
```bash
# Run comprehensive test suite
python3 scripts/test_skill_parser.py --comprehensive

# Validate specific test cases
python3 scripts/test_skill_parser.py --test-cases "buildString,nearlyEqual,pcreGenCompileOptBits"

# Performance benchmarking
python3 scripts/test_skill_parser.py --benchmark --input docs/pdfs/sklangref.pdf
```

#### **Performance Metrics**
- **Processing Speed**: ~50-100 functions/second
- **Memory Usage**: <500MB for largest PDF documents
- **Accuracy Rate**: >98% function detection rate
- **Category Coverage**: 40+ categories across 22 documents

#### **Future Enhancements**
1. **Incremental Updates**: Detect and process only changed sections
2. **Cross-Reference Resolution**: Link related functions across documents  
3. **Version Comparison**: Track function changes between SKILL versions
4. **API Documentation**: Generate API docs from extracted function data

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

## Coding Standards

### Language Requirements

#### Communication Language
**COMMUNICATION REQUIREMENT**: When discussing with users via Claude Code, use Traditional Chinese (繁體中文) for all conversations, except for proper nouns and technical terms which should remain in their original language.

#### Code Language Requirement  
**STRICT REQUIREMENT**: All code content, comments, variable names, function names, documentation, and any text within the codebase MUST be written in English only. This is a mandatory standard for:

- All TypeScript/JavaScript code
- All comments and documentation
- Variable and function naming
- JSON configuration files
- Error messages and user-facing text
- Database content and schemas
- API documentation

**Rationale**: Ensures international collaboration, code maintainability, and professional standards.

**Enforcement**: This standard applies to all new code and any modifications to existing code.

## File Structure
- `src/` - TypeScript source files
- `out/` - Compiled JavaScript output
- `syntax/skill/` - Language grammar definitions
- `src/schema/` - JSON schema for completion configuration
- `src/builtin-procedures/` - Built-in SKILL procedures database
- `docs/skill-procedures/` - Version-specific procedure databases
- `vsix/` - Packaged extension files