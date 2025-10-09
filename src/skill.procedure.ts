import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { SkillConfig } from './builtin-procedures/types';
import { CompatibilityEngine } from './builtin-procedures/compatibility-engine';
import { BuiltinProcedureDatabase } from './builtin-procedures/types';
import { skillPromptGenerator } from './builtin-procedures/prompt-generator';

interface ProcedureDoc {
    summary: string;
    argDocs: { [arg: string]: string };
    returnDoc?: string;        // 📤 Optional: Return value description
    notes?: string;           // ⚠️ Optional: Important notes and warnings
    examples?: string[];      // 💡 Optional: Usage examples
}

interface ProcedureInfo {
    file: string;
    line: number;
    args: string[];
    doc: ProcedureDoc;
}

interface LegacySkillProcedureConfig {
    skill: {
        searchFolderPath: string;
    };
}

type SkillProcedureConfig = LegacySkillProcedureConfig | SkillConfig;

// Extend procedureIndex to include documentation
let procedureIndex: { [name: string]: ProcedureInfo } = {};
let procedureIndexLastModified: number = 0;
let cachedSkillFolder: string | undefined;
let compatibilityEngine: CompatibilityEngine | undefined;
let currentSkillConfig: SkillConfig | undefined;
let builtinDatabase: BuiltinProcedureDatabase | undefined;
let completeFunctionsDatabase: any = undefined;

// Remove all block comments from a string, preserving string length for cursor mapping
function removeBlockComments(str: string): string {
    let result = '';
    let i = 0;
    let inBlockComment = false;
    while (i < str.length) {
        if (!inBlockComment && str.slice(i, i + 2) === '/*') {
            inBlockComment = true;
            i += 2;
            continue;
        }
        if (inBlockComment && str.slice(i, i + 2) === '*/') {
            inBlockComment = false;
            i += 2;
            continue;
        }
        if (!inBlockComment) {
            result += str[i];
        }
        i++;
    }
    return result;
}

// Parse arguments, treating quoted strings as a single argument and skipping content in comments (line and block)
function parseSkillArgs(argStr: string): string[] {
    const args: string[] = [];
    let i = 0;
    const len = argStr.length;
    let inLineComment = false;
    let inBlockComment = false;
    let inString = false;
    while (i < len) {
        // Skip leading spaces
        while (i < len && argStr[i] === ' ') { i++; }
        if (i >= len) { break; }

        const c = argStr[i];
        const next2 = argStr.slice(i, i + 2);

        // Enter/exit string mode
        if (!inLineComment && !inBlockComment && c === '"') {
            inString = !inString;
            i++;
            continue;
        }
        // Enter block comment mode
        if (!inString && !inLineComment && next2 === '/*') {
            inBlockComment = true;
            i += 2;
            continue;
        }
        // Exit block comment mode
        if (inBlockComment && next2 === '*/') {
            inBlockComment = false;
            i += 2;
            continue;
        }
        // Enter line comment mode
        if (!inString && !inBlockComment && c === ';') {
            inLineComment = true;
            i++;
            continue;
        }
        // Exit line comment mode at end of line
        if (inLineComment && c === '\n') {
            inLineComment = false;
            i++;
            continue;
        }
        // Skip all characters inside string, line comment, or block comment
        if (inString || inLineComment || inBlockComment) {
            i++;
            continue;
        }

        // Handle quoted string: "..."
        if (c === '"') {
            let arg = '"';
            i++;
            while (i < len) {
                arg += argStr[i];
                if (argStr[i] === '"' && arg[arg.length - 2] !== '\\') {
                    i++;
                    break;
                }
                i++;
            }
            args.push(arg);
            continue;
        }

        // Handle single quote or backtick before parenthesis: '(...) or `(...) 
        if ((c === "'" || c === '`') && argStr[i + 1] === '(') {
            let arg = c;
            i++;
            if (argStr[i] === '(') {
                let depth = 1;
                arg += argStr[i];
                i++;
                while (i < len && depth > 0) {
                    const groupNext2 = argStr.slice(i, i + 2);
                    if (!inString && groupNext2 === '/*') {
                        while (i < len && argStr.slice(i, i + 2) !== '*/') { i++; }
                        i += 2;
                        continue;
                    }
                    if (!inString && argStr[i] === ';') {
                        while (i < len && argStr[i] !== '\n') { i++; }
                        i++;
                        continue;
                    }
                    arg += argStr[i];
                    if (argStr[i] === '(') { depth++; }
                    else if (argStr[i] === ')') { depth--; }
                    i++;
                }
            }
            args.push(arg);
            continue;
        }

        // Handle parenthesis group: (...), including nested
        if (c === '(') {
            let arg = '(';
            i++;
            let depth = 1;
            while (i < len && depth > 0) {
                const groupNext2 = argStr.slice(i, i + 2);
                if (!inString && groupNext2 === '/*') {
                    while (i < len && argStr.slice(i, i + 2) !== '*/') { i++; }
                    i += 2;
                    continue;
                }
                if (!inString && argStr[i] === ';') {
                    while (i < len && argStr[i] !== '\n') { i++; }
                    i++;
                    continue;
                }
                arg += argStr[i];
                if (argStr[i] === '(') { depth++; }
                else if (argStr[i] === ')') { depth--; }
                i++;
            }
            args.push(arg);
            continue;
        }

        // Handle table[...] with chained brackets and nested parentheses/brackets
        const tableMatch = argStr.slice(i).match(/^([a-zA-Z_]\w*)\[/);
        if (tableMatch) {
            let arg = tableMatch[1];
            i += tableMatch[1].length;
            // Consume all chained brackets
            while (i < len && argStr[i] === '[') {
                let depth = 1;
                arg += argStr[i];
                i++;
                while (i < len && depth > 0) {
                    const groupNext2 = argStr.slice(i, i + 2);
                    if (!inString && groupNext2 === '/*') {
                        while (i < len && argStr.slice(i, i + 2) !== '*/') { i++; }
                        i += 2;
                        continue;
                    }
                    if (!inString && argStr[i] === ';') {
                        while (i < len && argStr[i] !== '\n') { i++; }
                        i++;
                        continue;
                    }
                    arg += argStr[i];
                    if (argStr[i] === '[') { depth++; }
                    else if (argStr[i] === ']') { depth--; }
                    // Handle nested parentheses inside brackets
                    if (argStr[i] === '(') {
                        let parenDepth = 1;
                        arg += argStr[i++];
                        while (i < len && parenDepth > 0) {
                            const parenNext2 = argStr.slice(i, i + 2);
                            if (!inString && parenNext2 === '/*') {
                                while (i < len && argStr.slice(i, i + 2) !== '*/') { i++; }
                                i += 2;
                                continue;
                            }
                            if (!inString && argStr[i] === ';') {
                                while (i < len && argStr[i] !== '\n') { i++; }
                                i++;
                                continue;
                            }
                            arg += argStr[i];
                            if (argStr[i] === '(') { parenDepth++; }
                            else if (argStr[i] === ')') { parenDepth--; }
                            i++;
                        }
                        continue;
                    }
                    i++;
                }
            }
            args.push(arg);
            continue;
        }

        // Handle normal word
        let arg = '';
        while (
            i < len &&
            argStr[i] !== ' ' &&
            argStr[i] !== ';' &&
            argStr.slice(i, i + 2) !== '/*'
        ) {
            arg += argStr[i];
            i++;
        }
        if (arg.length > 0) {
            args.push(arg);
        }

        // If we hit a comment after a word, skip the rest of the line or block
        if (i < len && argStr[i] === ';') {
            while (i < len && argStr[i] !== '\n') { i++; }
            i++; // Skip the newline
        }
        if (i < len && argStr.slice(i, i + 2) === '/*') {
            while (i < len && argStr.slice(i, i + 2) !== '*/') { i++; }
            i += 2;
        }
    }
    return args.filter(Boolean);
}

// Calculate argument index by skipping block and line comments and ignoring spaces in block comments
function getArgIndex(argStr: string, cursorOffset: number): number {
    // Remove all block comments for argument index calculation
    let cleanStr = removeBlockComments(argStr.slice(0, cursorOffset));
    let inLineComment = false;
    let inString = false;
    let argCount = 0;
    let i = 0;
    let lastWasSpace = true;
    while (i < cleanStr.length) {
        const c = cleanStr[i];

        // Enter/exit string mode
        if (!inLineComment && c === '"') {
            inString = !inString;
            i++;
            lastWasSpace = false;
            continue;
        }
        // Enter line comment mode
        if (!inString && c === ';') {
            inLineComment = true;
            i++;
            lastWasSpace = false;
            continue;
        }
        // Exit line comment mode at end of line
        if (inLineComment && c === '\n') {
            inLineComment = false;
            i++;
            lastWasSpace = false;
            continue;
        }
        // Skip all characters inside string or line comment
        if (inString || inLineComment) {
            i++;
            continue;
        }
        // Count argument when hitting a space (not consecutive)
        if (c === ' ') {
            if (!lastWasSpace) {
                argCount++;
                lastWasSpace = true;
            }
            i++;
            continue;
        }
        lastWasSpace = false;
        i++;
    }
    // If cursor is not at a space, count the last argument
    if (!lastWasSpace) { argCount++; }
    return Math.max(0, argCount - 1);
}

// Interface for argument boundaries
interface ArgumentBoundary {
    start: number;
    end: number;
    content: string;
}

// Parse argument boundaries with precise position tracking
function parseArgumentBoundaries(text: string): ArgumentBoundary[] {
    const boundaries: ArgumentBoundary[] = [];
    let i = 0;
    let inString = false;
    let inLineComment = false;
    let inBlockComment = false;
    let parenDepth = 0;
    let bracketDepth = 0;
    let argStart = -1;
    
    // Skip leading spaces to find first argument
    while (i < text.length && text[i] === ' ') { i++; }
    
    while (i < text.length) {
        const c = text[i];
        const next2 = text.slice(i, i + 2);
        
        // Handle string mode
        if (!inLineComment && !inBlockComment && c === '"') {
            if (argStart === -1 && !inString) {
                argStart = i;
            }
            inString = !inString;
            i++;
            continue;
        }
        
        // Handle block comments
        if (!inString && !inLineComment && next2 === '/*') {
            inBlockComment = true;
            i += 2;
            continue;
        }
        if (inBlockComment && next2 === '*/') {
            inBlockComment = false;
            i += 2;
            continue;
        }
        
        // Handle line comments
        if (!inString && !inBlockComment && c === ';') {
            inLineComment = true;
            i++;
            continue;
        }
        if (inLineComment && c === '\n') {
            inLineComment = false;
            i++;
            continue;
        }
        
        // Skip content inside comments
        if (inLineComment || inBlockComment) {
            i++;
            continue;
        }
        
        // Handle quoted lists: '(...)
        if (!inString && (c === "'" || c === '`') && i + 1 < text.length && text[i + 1] === '(') {
            if (argStart === -1) {
                argStart = i;
            }
            i++; // skip quote
            parenDepth++;
            i++;
            continue;
        }
        
        // Handle parentheses
        if (!inString && c === '(') {
            if (argStart === -1) {
                argStart = i;
            }
            parenDepth++;
            i++;
            continue;
        }
        if (!inString && c === ')') {
            parenDepth--;
            if (parenDepth === 0 && argStart !== -1) {
                // End of parenthesized argument
                boundaries.push({
                    start: argStart,
                    end: i,
                    content: text.slice(argStart, i + 1)
                });
                argStart = -1;
                // Skip to next non-space character
                i++;
                while (i < text.length && text[i] === ' ') { i++; }
                continue;
            }
            i++;
            continue;
        }
        
        // Handle brackets
        if (!inString && c === '[') {
            if (argStart === -1) {
                argStart = i;
            }
            bracketDepth++;
            i++;
            continue;
        }
        if (!inString && c === ']') {
            bracketDepth--;
            i++;
            continue;
        }
        
        // Handle spaces (argument separators)
        if (!inString && c === ' ' && parenDepth === 0 && bracketDepth === 0) {
            if (argStart !== -1) {
                // End of current argument
                boundaries.push({
                    start: argStart,
                    end: i - 1,
                    content: text.slice(argStart, i)
                });
                argStart = -1;
            }
            // Skip consecutive spaces
            while (i < text.length && text[i] === ' ') { i++; }
            continue;
        }
        
        // Start new argument if not already started
        if (argStart === -1 && c !== ' ') {
            argStart = i;
        }
        
        i++;
    }
    
    // Handle last argument
    if (argStart !== -1) {
        boundaries.push({
            start: argStart,
            end: text.length - 1,
            content: text.slice(argStart)
        });
    }
    
    return boundaries;
}

// Calculate active parameter index with enhanced boundary detection
function calculateActiveParameter(textBefore: string): number {
    const cursorOffset = textBefore.length;
    
    // Parse argument boundaries to get precise positions
    const boundaries = parseArgumentBoundaries(textBefore);
    
    console.debug('[SKILL] calculateActiveParameter:', {
        textBefore: textBefore,
        cursorOffset: cursorOffset,
        boundaries: boundaries
    });
    
    // Check if cursor is within any argument boundary
    for (let i = 0; i < boundaries.length; i++) {
        const boundary = boundaries[i];
        if (cursorOffset >= boundary.start && cursorOffset <= boundary.end + 1) {
            console.debug('[SKILL] Cursor within boundary', i, ':', boundary);
            return i;
        }
    }
    
    // Check if cursor is after the last argument (preparing for new argument)
    if (boundaries.length > 0) {
        const lastBoundary = boundaries[boundaries.length - 1];
        if (cursorOffset > lastBoundary.end + 1) {
            // Check if there's trailing space suggesting a new argument
            const afterLast = textBefore.slice(lastBoundary.end + 1);
            if (afterLast.trim().length === 0 && afterLast.includes(' ')) {
                console.debug('[SKILL] Cursor after last argument, expecting new argument');
                return boundaries.length;
            }
        }
    }
    
    // Fallback: cursor is at the position for the next argument
    console.debug('[SKILL] Cursor at position for argument', boundaries.length);
    return boundaries.length;
}

// Enhanced parameter name extraction function
function extractParameterName(arg: string): string {
    // Handle various parameter formats:
    // 1. "argument2" -> "argument2"
    // 2. "(argument2 default)" -> "argument2"  
    // 3. "argument2 = default" -> "argument2"
    // 4. "@optional", "@key", "@rest" -> skip these keywords
    
    if (arg.startsWith('@')) {
        return ''; // Skip SKILL keywords like @optional, @key, @rest
    }
    
    // Handle parentheses format: (arg default)
    const parenMatch = arg.match(/^\(\s*(\w+)/);
    if (parenMatch) {
        return parenMatch[1];
    }
    
    // Handle assignment format: arg = default
    const assignMatch = arg.match(/^(\w+)\s*=/);
    if (assignMatch) {
        return assignMatch[1];
    }
    
    // Handle space-separated format: arg default
    const spaceMatch = arg.match(/^(\w+)(?:\s|$)/);
    if (spaceMatch) {
        return spaceMatch[1];
    }
    
    // Fallback: clean the argument string
    return arg.replace(/[()]/g, '').split(/[\s=]/)[0].trim();
}

// Parse documentation block for a procedure
function parseProcedureDoc(lines: string[], procLine: number, args: string[]): ProcedureDoc {
    // Default values
    let summary = '';
    let returnDoc: string | undefined;
    let notes: string | undefined;
    const examples: string[] = [];
    const argDocs: { [arg: string]: string } = {};
    
    // Check if previous line ends with */
    if (procLine > 0 && lines[procLine - 1].trim().endsWith('*/')) {
        // Find the start of the block comment
        let startLine = procLine - 1;
        while (startLine >= 0 && !lines[startLine].includes('/*')) {
            startLine--;
        }
        if (startLine >= 0) {
            // Extract block comment content
            const docLines = lines.slice(startLine, procLine).join('\n');
            
            // Extract <@summary>...</@summary>
            const summaryMatch = docLines.match(/<@summary>([\s\S]*?)<\/@summary>/i);
            if (summaryMatch) {
                summary = summaryMatch[1].trim();
            }
            
            // Extract <@return>...</@return>
            const returnMatch = docLines.match(/<@return>([\s\S]*?)<\/@return>/i);
            if (returnMatch) {
                returnDoc = returnMatch[1].trim();
            }
            
            // Extract <@note>...</@note>
            const noteMatch = docLines.match(/<@note>([\s\S]*?)<\/@note>/i);
            if (noteMatch) {
                notes = noteMatch[1].trim();
            }
            
            // Extract <@example>...</@example> (can have multiple)
            const exampleMatches = docLines.matchAll(/<@example>([\s\S]*?)<\/@example>/gi);
            for (const match of exampleMatches) {
                examples.push(match[1].trim());
            }
            
            // Extract <argumentName>...</argumentName> for each argument
            for (const arg of args) {
                // Enhanced parameter name extraction to handle various formats
                const argName = extractParameterName(arg);
                console.debug(`[SKILL] Processing arg: "${arg}" -> extracted name: "${argName}"`);
                
                if (argName) {
                    const argMatch = docLines.match(new RegExp(`<${argName}>([\\s\\S]*?)<\\/${argName}>`, 'i'));
                    if (argMatch) {
                        argDocs[argName] = argMatch[1].trim();
                        console.debug(`[SKILL] Found documentation for "${argName}": "${argDocs[argName]}"`);
                    } else {
                        argDocs[argName] = '';
                        console.debug(`[SKILL] No documentation found for "${argName}"`);
                    }
                }
            }
        }
    } else {
        // No valid doc block, use defaults
        for (const arg of args) {
            const argName = extractParameterName(arg);
            if (argName) {
                argDocs[argName] = '';
            }
        }
    }
    
    return { 
        summary, 
        argDocs, 
        returnDoc: returnDoc || undefined,
        notes: notes || undefined,
        examples: examples.length > 0 ? examples : undefined
    };
}

async function loadSkillConfig(): Promise<string | undefined> {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) { return; }
    
    const configPath = path.join(workspaceFolders[0].uri.fsPath, '.vscode', 'skill.json');
    
    try {
        // Check if we have cached folder path and config file hasn't changed
        if (cachedSkillFolder && fs.existsSync(configPath)) {
            const stats = fs.statSync(configPath);
            if (stats.mtime.getTime() === procedureIndexLastModified) {
                return cachedSkillFolder;
            }
        }

        // Check if the configuration file exists
        if (fs.existsSync(configPath)) {
            const stats = fs.statSync(configPath);
            const configContent = fs.readFileSync(configPath, 'utf8');
            const config: SkillProcedureConfig = JSON.parse(configContent);
            
            // Determine if this is a legacy config or new config
            let folderPath: string | undefined;
            
            console.log('[SKILL] Config loaded, checking format...');
            if (isLegacyConfig(config)) {
                console.log('[SKILL] Detected legacy configuration format');
                // Legacy configuration format
                folderPath = config.skill?.searchFolderPath;
            } else {
                console.log('[SKILL] Detected new configuration format');
                // New configuration format
                folderPath = config.search_folder_path;
                currentSkillConfig = config;
                
                // Initialize compatibility engine with new config
                console.log('[SKILL] Initializing compatibility engine...');
                await initializeCompatibilityEngine(config);
            }

            if (!folderPath) {
                console.error('searchFolderPath not found in skill configuration');
                return;
            }

            // If folderPath is a relative path, convert it to an absolute path.
            if (!folderPath.startsWith('/') && !/^[A-Z]:\\/i.test(folderPath)) {
                if (workspaceFolders && workspaceFolders.length > 0) {
                    const workspaceRoot = workspaceFolders[0].uri.fsPath;
                    folderPath = path.join(workspaceRoot, folderPath);
                }
            }

            // Cache the result
            cachedSkillFolder = folderPath;
            procedureIndexLastModified = stats.mtime.getTime();
            
            console.debug(`Skill folder path: ${folderPath}`);
            return folderPath;
        }
    } catch (error) {
        console.error(`Failed to load skill configuration: ${error instanceof Error ? error.message : 'Unknown error'}`);
        return;
    }
}

function isLegacyConfig(config: SkillProcedureConfig): config is LegacySkillProcedureConfig {
    return 'skill' in config && 'searchFolderPath' in config.skill;
}

async function initializeCompatibilityEngine(config: SkillConfig): Promise<void> {
    try {
        console.log('[SKILL] Initializing compatibility engine...');
        if (!compatibilityEngine) {
            compatibilityEngine = new CompatibilityEngine();
        }
        
        // Load universal procedures database
        let universalDbPath = path.join(__dirname, 'builtin-procedures', 'databases', 'universal-procedures.json');
        // Try alternative path if first doesn't exist (for development vs production)
        if (!fs.existsSync(universalDbPath)) {
            universalDbPath = path.join(__dirname, '..', 'src', 'builtin-procedures', 'databases', 'universal-procedures.json');
        }
        console.log('[SKILL] Looking for universal DB at:', universalDbPath);
        if (fs.existsSync(universalDbPath)) {
            console.log('[SKILL] Universal DB found, loading...');
            const universalDbContent = fs.readFileSync(universalDbPath, 'utf8');
            const universalDb = JSON.parse(universalDbContent);
            console.log('[SKILL] Universal DB loaded with', Object.keys(universalDb.procedures).length, 'procedures');
            
            // Create a builtin database structure
            builtinDatabase = {
                metadata: {
                    version: '1.0.0',
                    total_procedures: Object.keys(universalDb.procedures).length,
                    categories: ['Universal Functions'],
                    supported_tools: {
                        virtuoso: ['*'],
                        allegro: ['*']
                    },
                    last_updated: new Date().toISOString()
                },
                procedures: universalDb.procedures
            };
            
            await compatibilityEngine.loadBuiltinDatabase(builtinDatabase);
            console.log('[SKILL] Successfully loaded universal procedures database');
        } else {
            console.log('[SKILL] Universal DB file not found at path:', universalDbPath);
        }
        
        // Load complete SKILL functions database
        await loadCompleteFunctionsDatabase();
        
    } catch (error) {
        console.error(`[SKILL] Failed to initialize compatibility engine: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
}

async function loadCompleteFunctionsDatabase(): Promise<void> {
    try {
        console.log('[SKILL] Loading complete functions database...');
        
        // Find complete-skill-functions.json
        let completeFunctionsPath = path.join(__dirname, '..', 'docs', 'complete-skill-functions.json');
        // Try alternative paths
        if (!fs.existsSync(completeFunctionsPath)) {
            completeFunctionsPath = path.join(__dirname, '..', '..', 'docs', 'complete-skill-functions.json');
        }
        
        console.log('[SKILL] Looking for complete functions DB at:', completeFunctionsPath);
        if (fs.existsSync(completeFunctionsPath)) {
            console.log('[SKILL] Complete functions DB found, loading...');
            const completeFunctionsContent = fs.readFileSync(completeFunctionsPath, 'utf8');
            completeFunctionsDatabase = JSON.parse(completeFunctionsContent);
            console.log('[SKILL] Complete functions DB loaded with', completeFunctionsDatabase.metadata.total_functions, 'functions');
        } else {
            console.log('[SKILL] Complete functions DB file not found at path:', completeFunctionsPath);
        }
    } catch (error) {
        console.error(`[SKILL] Failed to load complete functions database: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
}

function generateCompleteFunctionHover(func: any): string {
    let hoverText = `**🔧 function** \`${func.name}\`\n\n`;
    
    // Summary section
    if (func.purpose || func.description) {
        const summary = func.purpose || func.description;
        hoverText += `📋 ${summary}\n\n`;
    } else {
        hoverText += `📋 *No documentation available for this function.*\n\n`;
    }
    
    hoverText += `---\n\n`;
    
    // Syntax section
    if (func.syntax) {
        hoverText += `**💻 Syntax:** \`${func.syntax}\`\n\n`;
    }
    
    // Arguments section
    if (func.arguments && Object.keys(func.arguments).length > 0) {
        hoverText += `**📥 Arguments:**\n`;
        Object.entries(func.arguments).forEach(([argName, argDesc]) => {
            const description = (argDesc as string || '*No description*').trim();
            hoverText += `  **\`${argName}\`**  \n    ${description}\n\n`;
        });
    }
    
    // Return value section
    if (func.returns && typeof func.returns === 'object' && Object.keys(func.returns).length > 0) {
        hoverText += `**📤 Returns:** ${Object.values(func.returns).join(', ')}\n\n`;
    }
    
    // Examples section
    if (func.examples && func.examples.length > 0) {
        hoverText += `**💡 Examples:**\n`;
        func.examples.forEach((example: string, index: number) => {
            if (func.examples.length > 1) {
                hoverText += `Example ${index + 1}:\n`;
            }
            hoverText += `\`\`\`skill\n${example}\n\`\`\`\n\n`;
        });
    }
    
    // Category section
    if (func.category) {
        hoverText += `**🏷️ Category:** ${func.category}\n\n`;
    }
    
    // Source file section
    if (func.source_file) {
        hoverText += `---\n*📚 Source: ${func.source_file}*`;
    }
    
    return hoverText;
}

function checkProcedureCompatibility(procedureName: string): string | undefined {
    if (!compatibilityEngine || !currentSkillConfig) {
        return undefined;
    }
    
    const result = compatibilityEngine.checkProcedureCompatibility(procedureName, currentSkillConfig);
    
    if (result.status === 'warning' || result.status === 'error') {
        return result.message;
    }
    
    return undefined;
}

// Helper function to recursively scan directories for .il files
function scanSkillFiles(dir: string, fileList: string[] = []): string[] {
    try {
        const files = fs.readdirSync(dir);

        files.forEach(file => {
            const filePath = path.join(dir, file);
            try {
                const stat = fs.statSync(filePath);
                if (stat.isDirectory()) {
                    // Recursively scan subdirectories
                    scanSkillFiles(filePath, fileList);
                } else if (stat.isFile() && file.endsWith('.il')) {
                    // Add .il file to the list
                    fileList.push(filePath);
                }
            } catch (statError) {
                console.error(`Error accessing ${filePath}: ${statError instanceof Error ? statError.message : 'Unknown error'}`);
            }
        });
    } catch (readdirError) {
        console.error(`Error reading directory ${dir}: ${readdirError instanceof Error ? readdirError.message : 'Unknown error'}`);
    }

    return fileList;
}

function indexProcedures(skillFolder: string): void {
    try {
        if (!fs.existsSync(skillFolder)) {
            console.error(`Skill folder does not exist: ${skillFolder}`);
            return;
        }

        procedureIndex = {};

        // Recursively scan for all .il files in skillFolder and its subdirectories
        const skillFiles = scanSkillFiles(skillFolder);
        console.debug(`Found ${skillFiles.length} SKILL files in ${skillFolder}`);

        skillFiles.forEach(filePath => {
            console.debug(`Processing file: ${filePath}`);

            try {
                const lines = fs.readFileSync(filePath, 'utf8').split('\n');
                lines.forEach((line, idx) => {
                    try {
                        // First, extract the procedure name
                        const nameMatch = line.match(/^\s*procedure\(\s*(\w+)/i);
                        if (nameMatch) {
                            // Start searching for parameters after the procedure name
                            const paramsStart = line.indexOf(nameMatch[1]) + nameMatch[1].length;
                            const paramsStr = line.slice(paramsStart);
                            // Find the first left parenthesis
                            const firstParen = paramsStr.indexOf('(');
                            if (firstParen !== -1) {
                                let depth = 0;
                                let endIdx = -1;
                                for (let i = firstParen; i < paramsStr.length; i++) {
                                    if (paramsStr[i] === '(') { depth++; }
                                    if (paramsStr[i] === ')') { depth--; }
                                    if (depth === 0) {
                                        endIdx = i;
                                        break;
                                    }
                                }
                                let argsRaw = paramsStr.slice(firstParen, endIdx + 1);
                                // Remove the outermost parentheses
                                if (argsRaw.startsWith('(') && argsRaw.endsWith(')')) {
                                    argsRaw = argsRaw.slice(1, -1).trim();
                                }
                                // Split arguments by whitespace (adjust as needed)
                                const args = argsRaw
                                    .match(/\([^\(\)]*\)|[^\s]+/g)
                                    ?.map(s => s.trim())
                                    .filter(Boolean) || [];
                                // Parse documentation for this procedure
                                const doc = parseProcedureDoc(lines, idx, args);
                                procedureIndex[nameMatch[1]] = {
                                    file: filePath,
                                    line: idx,
                                    args,
                                    doc
                                };
                            }
                        }
                    } catch (lineError) {
                        console.error(`Error processing line ${idx + 1} in ${filePath}: ${lineError instanceof Error ? lineError.message : 'Unknown error'}`);
                    }
                });
            } catch (fileError) {
                console.error(`Error processing file ${filePath}: ${fileError instanceof Error ? fileError.message : 'Unknown error'}`);
            }
        });

        console.debug(`Indexed ${Object.keys(procedureIndex).length} procedures from ${skillFiles.length} files`);
    } catch (error) {
        console.error(`Error indexing procedures in ${skillFolder}: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
}

export async function activate(context: vscode.ExtensionContext) {
    console.log('[SKILL] Extension activating...');
    const skillFolder = await loadSkillConfig();
    if (skillFolder) {
        indexProcedures(skillFolder);
    }
    
    // Initialize compatibility engine with default config if not already done
    if (!compatibilityEngine) {
        console.log('[SKILL] Initializing compatibility engine with default config...');
        const defaultConfig: SkillConfig = {
            auto_complete: true,
            search_folder_path: skillFolder || './skill',
            environment: {
                primary_tool: 'virtuoso' as any,
                tools: {
                    virtuoso: { version: '6.1.8' }
                }
            },
            compatibility: {
                mode: 'permissive' as any,
                allow_universal: true,
                allow_cross_tool: true,
                show_version_warnings: true,
                show_scope_warnings: true
            }
        };
        await initializeCompatibilityEngine(defaultConfig);
    }

    const provider: vscode.DocumentLinkProvider = {
        provideDocumentLinks(document) {
            const links: vscode.DocumentLink[] = [];
            const text = document.getText();
            Object.keys(procedureIndex).forEach(proc => {
                // Only match procedureName(, and underline only the name
                // Ensure it is NOT preceded by 'procedure(' (with optional whitespace)
                let regex = new RegExp(`\\b(${proc})\\(`, 'g');
                let match: RegExpExecArray | null;
                while ((match = regex.exec(text)) !== null) {
                    // Check if the match is preceded by 'procedure(', if so, skip
                    const before = text.substring(Math.max(0, match.index - 24), match.index).toLowerCase();
                    if (/\bprocedure\(/.test(before)) {
                        continue;
                    }
                    const start = document.positionAt(match.index);
                    const end = document.positionAt(match.index + match[1].length);
                    const targetUri = vscode.Uri.file(procedureIndex[proc].file).with({ fragment: String(procedureIndex[proc].line + 1) });
                    links.push(new vscode.DocumentLink(new vscode.Range(start, end), targetUri));
                }
            });
            return links;
        }
    };

    const hoverProvider: vscode.HoverProvider = {
        provideHover(document, position) {
            console.log('[SKILL] Hover provider called at position:', position.line, position.character);
            const wordRange = document.getWordRangeAtPosition(position);
            if (!wordRange) { 
                console.log('[SKILL] No word range found at position');
                return; 
            }
            const word = document.getText(wordRange);
            console.log('[SKILL] Hover request for word:', word);
            
            // Check if this is a universal procedure first
            console.log('[SKILL] Compatibility engine available:', compatibilityEngine ? 'YES' : 'NO');
            const universalProc = compatibilityEngine?.getProcedureInfo(word);
            console.log('[SKILL] Universal procedure found for', word, ':', universalProc ? 'YES' : 'NO');
            if (universalProc) {
                console.log('[SKILL] Universal procedure details:', {
                    name: universalProc.name,
                    scope: universalProc.scope,
                    category: universalProc.category
                });
            }
            if (universalProc) {
                // Only show on invocation (must be followed by a left parenthesis)
                const after = document.getText(new vscode.Range(wordRange.end, wordRange.end.translate(0, 1)));
                console.log('[SKILL] Character after word:', after);
                if (after !== '(') { return; }
                
                console.log('[SKILL] Generating hover for universal procedure:', word);
                // Generate enhanced prompt for universal procedure
                let hoverText = skillPromptGenerator.generateHoverPrompt(universalProc);
                
                // Add compatibility warning if needed
                const compatibilityMessage = checkProcedureCompatibility(word);
                if (compatibilityMessage) {
                    hoverText = `⚠️ **Compatibility Warning:** ${compatibilityMessage}\n\n${hoverText}`;
                }
                
                console.log('[SKILL] Returning hover text for:', word);
                return new vscode.Hover(new vscode.MarkdownString(hoverText, true));
            }
            
            // Check complete functions database
            console.log('[SKILL] Complete functions database available:', completeFunctionsDatabase ? 'YES' : 'NO');
            const completeFunc = completeFunctionsDatabase?.functions?.[word];
            console.log('[SKILL] Complete function found for', word, ':', completeFunc ? 'YES' : 'NO');
            if (completeFunc) {
                // Only show on invocation (must be followed by a left parenthesis)
                const after = document.getText(new vscode.Range(wordRange.end, wordRange.end.translate(0, 1)));
                console.log('[SKILL] Character after word:', after);
                if (after !== '(') { return; }
                
                console.log('[SKILL] Generating hover for complete function:', word);
                // Generate hover text for complete function
                let hoverText = generateCompleteFunctionHover(completeFunc);
                
                // Add compatibility warning if needed
                const compatibilityMessage = checkProcedureCompatibility(word);
                if (compatibilityMessage) {
                    hoverText = `⚠️ **Compatibility Warning:** ${compatibilityMessage}\n\n${hoverText}`;
                }
                
                console.log('[SKILL] Returning hover text for complete function:', word);
                return new vscode.Hover(new vscode.MarkdownString(hoverText, true));
            }
            
            // Fall back to user-defined procedures
            const proc = procedureIndex[word];
            if (proc) {
                // Only show on invocation (must be followed by a left parenthesis)
                const after = document.getText(new vscode.Range(wordRange.end, wordRange.end.translate(0, 1)));
                if (after !== '(') { return; }
                
                // Check compatibility for this procedure
                const compatibilityMessage = checkProcedureCompatibility(word);
                
                const { requiredArgs, optionalArgs, keyArgs, restArgs } = splitArgs(proc.args);

                // Build enhanced hover text with comfortable font sizes
                let hoverText = `**🔧 procedure** \`${word}\`\n\n`;
                
                // Add compatibility warning if needed
                if (compatibilityMessage) {
                    hoverText += `⚠️ **Compatibility Warning:** ${compatibilityMessage}\n\n`;
                }
                
                // Summary section
                if (proc.doc.summary) {
                    hoverText += `📋 ${proc.doc.summary}\n\n`;
                } else {
                    hoverText += `📋 *No documentation available for this procedure.*\n\n`;
                }
                
                hoverText += `---\n\n`;

                // Helper to get formatted argument documentation
                const getFormattedArgDoc = (arg: string, isOptional: boolean = false) => {
                    const argName = extractParameterName(arg);
                    const argDoc = proc.doc.argDocs[argName] || '*No documentation*';
                    
                    // Clean multi-line content and normalize to single line with proper spacing
                    const cleanArgDoc = argDoc
                        .replace(/\n/g, ' ')           // Replace newlines with spaces
                        .replace(/\s+/g, ' ')          // Normalize multiple spaces to single space
                        .trim();                       // Remove leading/trailing whitespace
                    
                    const optionalLabel = isOptional ? ' *(optional)*' : '';
                    const defaultValue = arg.includes('=') ? ` = ${arg.split('=')[1].trim()}` : '';
                    
                    return `  **\`${argName}${defaultValue}\`**${optionalLabel}  \n    ${cleanArgDoc}`;
                };

                // Arguments section
                if (requiredArgs.length > 0) {
                    hoverText += `**📥 Arguments:**\n`;
                    for (const arg of requiredArgs) {
                        hoverText += `${getFormattedArgDoc(arg)}\n\n`;
                    }
                }
                
                // Optional arguments section
                if (optionalArgs.length > 0) {
                    hoverText += `**📥 Optional Arguments:**\n`;
                    for (const arg of optionalArgs) {
                        hoverText += `${getFormattedArgDoc(arg, true)}\n\n`;
                    }
                    if (keyArgs.length > 0) {
                        hoverText += '> ℹ️ Key Arguments are ignored when optional arguments are provided.\n\n';
                    }
                } else if (keyArgs.length > 0) {
                    hoverText += `**📥 Key Arguments:**\n`;
                    for (const arg of keyArgs) {
                        hoverText += `${getFormattedArgDoc(arg, true)}\n\n`;
                    }
                }
                
                // Rest arguments section
                if (restArgs.length > 0) {
                    hoverText += `**📥 Arbitrary Arguments:**\n`;
                    for (const arg of restArgs) {
                        hoverText += `${getFormattedArgDoc(arg, true)}\n\n`;
                    }
                }
                
                // Return value section
                if (proc.doc.returnDoc) {
                    hoverText += `**📤 Returns:** ${proc.doc.returnDoc}\n\n`;
                }
                
                // Important notes section
                if (proc.doc.notes) {
                    hoverText += `**⚠️ Important Notes:** ${proc.doc.notes}\n\n`;
                }
                
                // Examples section
                if (proc.doc.examples && proc.doc.examples.length > 0) {
                    hoverText += `**💡 Example:**\n`;
                    proc.doc.examples.forEach((example, index) => {
                        if (proc.doc.examples!.length > 1) {
                            hoverText += `Example ${index + 1}:\n`;
                        }
                        hoverText += `\`\`\`skill\n${example}\n\`\`\`\n\n`;
                    });
                }
                
                // File location
                const fileName = path.basename(proc.file);
                hoverText += `---\n*💾 File: ${fileName}:${proc.line + 1}*`;
                // Use MarkdownString to support markdown in hover
                return new vscode.Hover(new vscode.MarkdownString(hoverText, true));
            }
        }
    };

    const signatureHelpProvider: vscode.SignatureHelpProvider = {
        provideSignatureHelp(document, position) {
            // Search upwards for the procedureName(
            let startLine = position.line;
            let startChar = -1;
            let procName: string | undefined;
            let openParenPos: vscode.Position | undefined;

            for (let lineNum = position.line; lineNum >= 0; lineNum--) {
                const lineText = document.lineAt(lineNum).text;
                const regex = /(\w+)\s*\(/g;
                let match: RegExpExecArray | null;
                while ((match = regex.exec(lineText)) !== null) {
                    if (
                        (lineNum < position.line) ||
                        (lineNum === position.line && match.index < position.character)
                    ) {
                        procName = match[1];
                        startLine = lineNum;
                        startChar = match.index + match[1].length + (match[0].length - match[1].length) - 1;
                        openParenPos = new vscode.Position(startLine, startChar);
                    }
                }
                if (procName) { break; }
            }
            if (!procName || !openParenPos) { return; }
            
            // Get the text from the opening parenthesis to the cursor position (may be multi-line)
            const range = new vscode.Range(
                openParenPos.translate(0, 1), // after '('
                position
            );
            const textBefore = document.getText(range);
            
            // Check if this is a universal procedure first
            const universalProc = compatibilityEngine?.getProcedureInfo(procName);
            if (universalProc) {
                // Handle universal procedure signature help
                return createUniversalSignatureHelp(universalProc, procName, textBefore);
            }
            
            // Check complete functions database
            const completeFunc = completeFunctionsDatabase?.functions?.[procName];
            if (completeFunc) {
                // Handle complete function signature help
                return createCompleteFunctionSignatureHelp(completeFunc, procName, textBefore);
            }
            
            // Fall back to user-defined procedures
            if (!procedureIndex[procName]) { return; }

            // Count parenthesis depth from the procedureName(
            // Parentheses inside line comments (;) and quoted strings (") and block comments (/* ... */) are ignored for depth calculation.
            let depth = 1;
            let inString = false;
            let inLineComment = false;
            let inBlockComment = false;
            for (let i = 0; i < textBefore.length; i++) {
                const c = textBefore[i];
                const next2 = textBefore.slice(i, i + 2);

                // Enter/exit string mode
                if (!inLineComment && !inBlockComment && c === '"') {
                    inString = !inString;
                    continue;
                }
                // Enter block comment mode
                if (!inString && !inLineComment && next2 === '/*') {
                    inBlockComment = true;
                    i++; // Skip '*'
                    continue;
                }
                // Exit block comment mode
                if (inBlockComment && next2 === '*/') {
                    inBlockComment = false;
                    i++; // Skip '/'
                    continue;
                }
                // Enter line comment mode
                if (!inString && !inBlockComment && c === ';') {
                    inLineComment = true;
                    continue;
                }
                // Exit line comment mode at end of line
                if (inLineComment && c === '\n') {
                    inLineComment = false;
                    continue;
                }
                // Only count parentheses if not in string or comment
                if (!inString && !inLineComment && !inBlockComment) {
                    if (c === '(') { depth++; }
                    else if (c === ')') { depth--; }
                    if (depth === 0) {
                        // If depth is 0, the procedure call is complete, do not show signature help
                        return;
                    }
                }
            }

            // Use shared parameter calculation logic
            const argIndex = calculateActiveParameter(textBefore);

            const { requiredArgs, optionalArgs } = splitArgs(procedureIndex[procName].args);
            const allArgs = [...requiredArgs, ...optionalArgs];

            // Helper to get argument doc with enhanced formatting
            const getArgDoc = (arg: string) => {
                const argName = extractParameterName(arg);
                const proc = procedureIndex[procName!];
                const doc = proc?.doc?.argDocs?.[argName];
                return new vscode.MarkdownString(
                    `📥 **\`${argName}\`**: ${doc || '*No documentation for this argument.*'}`
                );
            };

            // Build simplified signature help documentation
            const proc = procedureIndex[procName];
            let sigDoc = '';
            
            // Check compatibility for this procedure
            const compatibilityMessage = checkProcedureCompatibility(procName);
            
            // Add compatibility warning if needed
            if (compatibilityMessage) {
                sigDoc += `⚠️ **Compatibility:** ${compatibilityMessage}\n\n`;
            }
            
            // Add separator line above summary if summary exists
            if (proc.doc.summary) {
                sigDoc += `---\n\n📋 ${proc.doc.summary}`;
            }

            const signature = new vscode.SignatureInformation(
                `${procName}(${allArgs.join(' ')})`,
                new vscode.MarkdownString(sigDoc, true) // Use MarkdownString for better formatting
            );
            // Only set parameter documentation, not the main doc
            signature.parameters = allArgs.map(arg => new vscode.ParameterInformation(arg, getArgDoc(arg)));

            const sigHelp = new vscode.SignatureHelp();
            sigHelp.signatures = [signature];
            sigHelp.activeSignature = 0;
            sigHelp.activeParameter = (argIndex >= allArgs.length) ? -1 : argIndex;

            return sigHelp;
        }
    };

    // Helper function for complete function signature help
    function createCompleteFunctionSignatureHelp(completeFunc: any, procName: string, textBefore: string): vscode.SignatureHelp {
        // Generate signature help prompt
        let sigDoc = '';
        
        // Add compatibility warning if needed
        const compatibilityMessage = checkProcedureCompatibility(procName);
        if (compatibilityMessage) {
            sigDoc += `⚠️ **Compatibility:** ${compatibilityMessage}\n\n`;
        }
        
        // Add separator line above summary if summary exists
        if (completeFunc.purpose || completeFunc.description) {
            const summary = completeFunc.purpose || completeFunc.description;
            sigDoc += `---\n\n📋 ${summary}`;
        }
        
        // Create parameter information from complete function documentation
        const parameters: vscode.ParameterInformation[] = [];
        if (completeFunc.arguments && Object.keys(completeFunc.arguments).length > 0) {
            Object.entries(completeFunc.arguments).forEach(([argName, argDesc]) => {
                const description = (argDesc as string || '*No description*').trim();
                const paramInfo = new vscode.ParameterInformation(
                    argName,
                    new vscode.MarkdownString(`📥 **\`${argName}\`**: ${description}`)
                );
                parameters.push(paramInfo);
            });
        }
        
        // Create signature with complete function syntax
        const signature = new vscode.SignatureInformation(
            completeFunc.syntax || `${procName}(...)`,
            new vscode.MarkdownString(sigDoc, true)
        );
        signature.parameters = parameters;
        
        // Use shared parameter calculation logic for accurate parameter position
        const activeParameter = Math.min(calculateActiveParameter(textBefore), parameters.length - 1);
        
        const sigHelp = new vscode.SignatureHelp();
        sigHelp.signatures = [signature];
        sigHelp.activeSignature = 0;
        sigHelp.activeParameter = activeParameter >= 0 ? activeParameter : -1;
        
        return sigHelp;
    }

    // Helper function for universal procedure signature help
    function createUniversalSignatureHelp(universalProc: any, procName: string, textBefore: string): vscode.SignatureHelp {
        const doc = universalProc.documentation;
        
        // Generate signature help prompt
        let sigDoc = skillPromptGenerator.generateSignaturePrompt(universalProc);
        
        // Add compatibility warning if needed
        const compatibilityMessage = checkProcedureCompatibility(procName);
        if (compatibilityMessage) {
            sigDoc = `⚠️ **Compatibility:** ${compatibilityMessage}\n\n${sigDoc}`;
        }
        
        // Create parameter information from universal procedure documentation
        const parameters: vscode.ParameterInformation[] = [];
        if (doc.parameters) {
            doc.parameters.forEach((param: any, index: number) => {
                const paramInfo = new vscode.ParameterInformation(
                    param.name,
                    new vscode.MarkdownString(skillPromptGenerator.generateParameterPrompt(universalProc, index))
                );
                parameters.push(paramInfo);
            });
        }
        
        // Create signature with universal procedure syntax
        const signature = new vscode.SignatureInformation(
            doc.syntax || `${procName}(...)`,
            new vscode.MarkdownString(sigDoc, true)
        );
        signature.parameters = parameters;
        
        // Use shared parameter calculation logic for accurate parameter position
        const activeParameter = Math.min(calculateActiveParameter(textBefore), parameters.length - 1);
        
        const sigHelp = new vscode.SignatureHelp();
        sigHelp.signatures = [signature];
        sigHelp.activeSignature = 0;
        sigHelp.activeParameter = activeParameter >= 0 ? activeParameter : -1;
        
        return sigHelp;
    }

    context.subscriptions.push(
        vscode.languages.registerDocumentLinkProvider({ scheme: 'file', language: 'cadence-skill' }, provider),
        vscode.languages.registerHoverProvider({ scheme: 'file', language: 'cadence-skill' }, hoverProvider),
        vscode.languages.registerSignatureHelpProvider(
            { scheme: 'file', language: 'cadence-skill' },
            signatureHelpProvider,
            "(", " " // Trigger characters
        )
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('extension.showProcedureInfo', (uri: vscode.Uri) => {
            const proc = Object.entries(procedureIndex).find(([_, v]) => v.file === uri.fsPath);
            if (proc) {
                vscode.window.showInformationMessage(
                    `Procedure: ${proc[0]}\nArgs: ${procedureIndex[proc[0]].args.join(', ')}`
                );
            }
        })
    );

    vscode.workspace.onDidSaveTextDocument(async doc => {
        if (doc.fileName.endsWith('.il')) {
            const skillFolder = await loadSkillConfig();
            if (skillFolder) {
                indexProcedures(skillFolder);
            }
        }
    });
}

export function deactivate() {
    // Clear caches to prevent memory leaks
    procedureIndex = {};
    procedureIndexLastModified = 0;
    cachedSkillFolder = undefined;
    compatibilityEngine = undefined;
    currentSkillConfig = undefined;
    builtinDatabase = undefined;
    completeFunctionsDatabase = undefined;
}

function splitArgs(args: string[]) {
    const requiredArgs: string[] = [];
    const optionalArgs: string[] = [];
    const keyArgs: string[] = [];
    const restArgs: string[] = [];
    let optionalMode = false;
    let keyMode = false;
    let arbitraryMode = false;
    
    console.debug(`[SKILL] splitArgs input:`, args);
    
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '@optional') {
            optionalMode = true;
            keyMode = false; // Optional arguments are not key arguments
            continue;
        } else if (args[i] === '@key') {
            keyMode = true;
            optionalMode = false; // Key arguments are not optional
            continue;
        } else if (args[i] === '@rest') {
            arbitraryMode = true;
            
            // Arbitrary arguments are not optional or key arguments
            optionalMode = false;
            keyMode = false;
            continue;
        }
        if (arbitraryMode) {
            // If in arbitrary mode, treat everything as optional
            restArgs.push(args[i]);
            continue;
        } else if (optionalMode) {
            // Handle different @optional syntax formats:
            // 1. Simple optional: @optional arg2
            // 2. With default: @optional (arg2 default)
            const parenMatch = args[i].match(/^\(\s*(\S+)\s+(.+)\s*\)$/);
            if (parenMatch) {
                // Format: (arg2 default)
                optionalArgs.push(`${parenMatch[1]} = ${parenMatch[2]}`);
            } else {
                // Format: arg2 (simple optional parameter)
                optionalArgs.push(args[i]);
            }
        } else if (keyMode) {
            // Handle different @key syntax formats:
            // 1. Simple key: @key arg2
            // 2. With default: @key (arg2 default)
            const parenMatch = args[i].match(/^\(\s*(\S+)\s+(.+)\s*\)$/);
            if (parenMatch) {
                // Format: (arg2 default)
                keyArgs.push(`${parenMatch[1]} = ${parenMatch[2]}`);
            } else {
                // Format: arg2 (simple key parameter)
                keyArgs.push(args[i]);
            }
        } else {
            requiredArgs.push(args[i]);
        }
    }
    
    const result = { requiredArgs, optionalArgs, keyArgs, restArgs };
    console.debug(`[SKILL] splitArgs result:`, result);
    return result;
}