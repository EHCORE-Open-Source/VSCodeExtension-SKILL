import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

// Cache for skill search folder path
let cachedSearchFolder: string | undefined;
let searchFolderLastModified: number = 0;

// Diagnostic collection for file path warnings
let diagnosticCollection: vscode.DiagnosticCollection;

interface LegacySkillConfig {
    skill: {
        searchFolderPath?: string;
    };
}

interface NewSkillConfig {
    search_folder_path?: string;
}

type SkillConfig = LegacySkillConfig | NewSkillConfig;

function isLegacyConfig(config: SkillConfig): config is LegacySkillConfig {
    return 'skill' in config && typeof config.skill === 'object';
}

async function loadSearchFolderPath(): Promise<string | undefined> {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) { return; }

    const configPath = path.join(workspaceFolders[0].uri.fsPath, '.vscode', 'skill.json');

    try {
        // Check if we have cached path and config file hasn't changed
        if (cachedSearchFolder && fs.existsSync(configPath)) {
            const stats = fs.statSync(configPath);
            if (stats.mtime.getTime() === searchFolderLastModified) {
                return cachedSearchFolder;
            }
        }

        // Check if the configuration file exists
        if (fs.existsSync(configPath)) {
            const stats = fs.statSync(configPath);
            const configContent = fs.readFileSync(configPath, 'utf8');
            const config: SkillConfig = JSON.parse(configContent);

            // Determine search folder path based on config format
            let folderPath: string | undefined;

            if (isLegacyConfig(config)) {
                // Legacy configuration format
                folderPath = config.skill?.searchFolderPath;
            } else {
                // New configuration format
                folderPath = config.search_folder_path;
            }

            if (!folderPath) {
                console.debug('[SKILL Link] searchFolderPath not found in skill configuration');
                return;
            }

            // If folderPath is a relative path, convert it to an absolute path
            if (!folderPath.startsWith('/') && !/^[A-Z]:\\/i.test(folderPath)) {
                const workspaceRoot = workspaceFolders[0].uri.fsPath;
                folderPath = path.join(workspaceRoot, folderPath);
            }

            // Cache the result
            cachedSearchFolder = folderPath;
            searchFolderLastModified = stats.mtime.getTime();

            console.debug(`[SKILL Link] Search folder path: ${folderPath}`);
            return folderPath;
        }
    } catch (error) {
        console.error(`[SKILL Link] Failed to load skill configuration: ${error instanceof Error ? error.message : 'Unknown error'}`);
        return;
    }
}

// Helper function to recursively search for a file in a directory
function findFileInDirectory(dir: string, fileName: string): string | undefined {
    try {
        if (!fs.existsSync(dir)) {
            return undefined;
        }

        const files = fs.readdirSync(dir);

        for (const file of files) {
            const filePath = path.join(dir, file);
            try {
                const stat = fs.statSync(filePath);

                // If exact match found in current directory
                if (stat.isFile() && file === fileName) {
                    return filePath;
                }

                // Recursively search subdirectories
                if (stat.isDirectory()) {
                    const found = findFileInDirectory(filePath, fileName);
                    if (found) {
                        return found;
                    }
                }
            } catch (statError) {
                console.debug(`[SKILL Link] Error accessing ${filePath}: ${statError instanceof Error ? statError.message : 'Unknown error'}`);
            }
        }
    } catch (readdirError) {
        console.debug(`[SKILL Link] Error reading directory ${dir}: ${readdirError instanceof Error ? readdirError.message : 'Unknown error'}`);
    }

    return undefined;
}

// Helper function to parse strcat() calls and extract file path components
interface StrcatResult {
    fullMatch: string;           // The complete strcat(...) expression
    pathLiterals: string[];      // String literals found in strcat
    variables: string[];         // Variable names found in strcat
    combinedPath: string;        // Combined path from literals (ignoring variables for now)
    startIndex: number;          // Start position of the strcat call
    endIndex: number;            // End position of the strcat call
}

function parseStrcatCall(text: string, startPos: number): StrcatResult | null {
    // Match strcat( ... ) starting from startPos
    const strcatRegex = /strcat\s*\(/g;
    strcatRegex.lastIndex = startPos;
    const match = strcatRegex.exec(text);

    if (!match) {
        return null;
    }

    // Find the matching closing parenthesis
    let depth = 1;
    let pos = match.index + match[0].length;
    const startIndex = match.index;

    while (pos < text.length && depth > 0) {
        if (text[pos] === '(') {
            depth++;
        } else if (text[pos] === ')') {
            depth--;
        }
        pos++;
    }

    if (depth !== 0) {
        return null; // Unmatched parentheses
    }

    const endIndex = pos;
    const fullMatch = text.substring(startIndex, endIndex);
    const argsContent = text.substring(match.index + match[0].length, endIndex - 1);

    // Extract string literals and variables
    const pathLiterals: string[] = [];
    const variables: string[] = [];

    // Match string literals (both single and double quotes)
    const stringRegex = /["']([^"']+)["']/g;
    let stringMatch: RegExpExecArray | null;

    while ((stringMatch = stringRegex.exec(argsContent)) !== null) {
        pathLiterals.push(stringMatch[1]);
    }

    // Match variable names (word characters not inside strings)
    // Remove all strings first, then extract variables
    const withoutStrings = argsContent.replace(/["'][^"']*["']/g, '');
    const varRegex = /\b([a-zA-Z_]\w*)\b/g;
    let varMatch: RegExpExecArray | null;

    while ((varMatch = varRegex.exec(withoutStrings)) !== null) {
        const varName = varMatch[1];
        // Exclude SKILL keywords
        if (!['strcat', 'load'].includes(varName)) {
            variables.push(varName);
        }
    }

    // Combine path literals (simple concatenation)
    const combinedPath = pathLiterals.join('');

    return {
        fullMatch,
        pathLiterals,
        variables,
        combinedPath,
        startIndex,
        endIndex
    };
}

// Helper function to analyze variable data flow and find file lists
function analyzeVariableDataFlow(text: string, variableName: string, loadPosition: number): string[] {
    const fileNames: string[] = [];

    // Look backwards from load() position to find variable assignment
    const textBeforeLoad = text.substring(0, loadPosition);

    // Pattern 1: Direct assignment - varName = strcat(..., sourceVar)
    const strcatPattern = new RegExp(`${variableName}\\s*=\\s*strcat\\s*\\([^)]*?\\s+(\\w+)\\s*\\)`, 'g');
    let match: RegExpExecArray | null;

    while ((match = strcatPattern.exec(textBeforeLoad)) !== null) {
        const sourceVar = match[1];

        // Pattern 2: foreach( sourceVar listVar ) - find listVar
        const foreachPattern = new RegExp(`foreach\\s*\\(\\s*${sourceVar}\\s+(\\w+)`, 'g');
        let foreachMatch: RegExpExecArray | null;

        while ((foreachMatch = foreachPattern.exec(textBeforeLoad)) !== null) {
            const listVar = foreachMatch[1];

            // Pattern 3: listVar = list(...) - extract file names
            const listPattern = new RegExp(`${listVar}\\s*=\\s*list\\s*\\([^)]*\\)`, 'g');
            let listMatch: RegExpExecArray | null;

            while ((listMatch = listPattern.exec(textBeforeLoad)) !== null) {
                const listContent = listMatch[0];

                // Extract all .il file names from list
                const filePattern = /["']([:\w\-\\\/\.]+\.il)["']/g;
                let fileMatch: RegExpExecArray | null;

                while ((fileMatch = filePattern.exec(listContent)) !== null) {
                    fileNames.push(fileMatch[1]);
                }
            }
        }
    }

    // Pattern 4: Direct foreach - foreach( varName listVar )
    const directForeachPattern = new RegExp(`foreach\\s*\\(\\s*${variableName}\\s+(\\w+)`, 'g');

    while ((match = directForeachPattern.exec(textBeforeLoad)) !== null) {
        const listVar = match[1];

        // Find listVar = list(...)
        const listPattern = new RegExp(`${listVar}\\s*=\\s*list\\s*\\([^)]*\\)`, 'g');
        let listMatch: RegExpExecArray | null;

        while ((listMatch = listPattern.exec(textBeforeLoad)) !== null) {
            const listContent = listMatch[0];

            // Extract all .il file names from list
            const filePattern = /["']([:\w\-\\\/\.]+\.il)["']/g;
            let fileMatch: RegExpExecArray | null;

            while ((fileMatch = filePattern.exec(listContent)) !== null) {
                fileNames.push(fileMatch[1]);
            }
        }
    }

    return fileNames;
}

// Helper function to resolve and check file path
async function resolveFilePath(fileName: string, searchFolderPath: string | undefined): Promise<{ resolvedPath: string | undefined, fileExists: boolean }> {
    let resolvedPath: string | undefined;
    let fileExists = false;

    // If fileName is already an absolute path, use it directly
    if (fileName.startsWith('/') || /^[A-Z]:\\/i.test(fileName)) {
        resolvedPath = fileName;
        fileExists = fs.existsSync(resolvedPath);
    } else {
        // Extract just the filename (without any path components)
        const baseFileName = path.basename(fileName);

        // Try to find file in searchFolderPath first (if configured)
        if (searchFolderPath) {
            resolvedPath = findFileInDirectory(searchFolderPath, baseFileName);
            if (resolvedPath) {
                fileExists = true;
            }
        }

        // If not found in searchFolderPath, fall back to workspace root
        if (!resolvedPath) {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (workspaceFolders && workspaceFolders.length > 0) {
                const workspaceRoot = workspaceFolders[0].uri.fsPath;
                resolvedPath = path.join(workspaceRoot, fileName);
                fileExists = fs.existsSync(resolvedPath);
            }
        }
    }

    return { resolvedPath, fileExists };
}

// Helper function to check if a position is inside a comment
function isInsideComment(document: vscode.TextDocument, position: vscode.Position): boolean {
    const text = document.getText();
    const offset = document.offsetAt(position);

    // Check for block comments /* ... */
    let blockCommentStart = -1;
    let blockCommentEnd = -1;
    let searchFrom = 0;

    while (searchFrom < offset) {
        const nextBlockStart = text.indexOf('/*', searchFrom);
        const nextBlockEnd = text.indexOf('*/', searchFrom);

        if (nextBlockStart !== -1 && nextBlockStart < offset) {
            blockCommentStart = nextBlockStart;
            // Find corresponding end
            const correspondingEnd = text.indexOf('*/', nextBlockStart + 2);
            if (correspondingEnd !== -1) {
                blockCommentEnd = correspondingEnd + 2;
                if (offset >= blockCommentStart && offset < blockCommentEnd) {
                    return true;
                }
                searchFrom = blockCommentEnd;
            } else {
                // Unclosed block comment - position is inside if after start
                if (offset >= blockCommentStart) {
                    return true;
                }
                break;
            }
        } else {
            break;
        }
    }

    // Check for line comments ;
    const lineText = document.lineAt(position.line).text;
    const linePrefix = lineText.substring(0, position.character);
    const semicolonIndex = linePrefix.indexOf(';');

    if (semicolonIndex !== -1) {
        return true;
    }

    return false;
}

// Function to update diagnostics for file paths
async function updateDiagnostics(document: vscode.TextDocument): Promise<void> {
    if (document.languageId !== 'cadence-skill') {
        return;
    }

    const diagnostics: vscode.Diagnostic[] = [];
    const text = document.getText();

    // Load search folder path from configuration
    const searchFolderPath = await loadSearchFolderPath();

    // Pattern 1: Match load("file.il") or load('file.il') - string literals
    const loadLiteralRegex = /load\s*\(\s*["']([:\w\-\\\/\.]+\.il)["']\s*\)/g;
    let match: RegExpExecArray | null;

    while ((match = loadLiteralRegex.exec(text)) !== null) {
        // match[1] contains the filename
        const fileNameStartIndex = match.index + match[0].indexOf(match[1]);
        const start = document.positionAt(fileNameStartIndex);
        const end = document.positionAt(fileNameStartIndex + match[1].length);
        const range = new vscode.Range(start, end);

        // Skip if inside a comment
        if (isInsideComment(document, start)) {
            continue;
        }

        let fileName = match[1];

        // Skip if the filename contains format placeholders
        if (/%[sdfxiouXcp]/.test(fileName)) {
            continue;
        }

        const { resolvedPath, fileExists } = await resolveFilePath(fileName, searchFolderPath);

        // If file doesn't exist, add a warning diagnostic
        if (resolvedPath && !fileExists) {
            const diagnostic = new vscode.Diagnostic(
                range,
                `File not found: ${resolvedPath}`,
                vscode.DiagnosticSeverity.Warning
            );
            diagnostic.source = 'SKILL';
            diagnostics.push(diagnostic);
        }
    }

    // Pattern 1b: Match load(strcat(...)) - parse strcat and check file paths
    const loadStrcatRegex = /load\s*\(\s*strcat\s*\(/g;

    while ((match = loadStrcatRegex.exec(text)) !== null) {
        const loadStartPos = match.index;
        const strcatStartPos = text.indexOf('strcat', loadStartPos);

        // Parse the strcat call
        const strcatResult = parseStrcatCall(text, strcatStartPos);

        if (!strcatResult) {
            continue;
        }

        // Skip if inside a comment
        const loadPosition = document.positionAt(loadStartPos);
        if (isInsideComment(document, loadPosition)) {
            continue;
        }

        // Skip if the combined path contains format placeholders
        if (/%[sdfxiouXcp]/.test(strcatResult.combinedPath)) {
            continue;
        }

        // Check if the combined path is a valid .il file
        if (!strcatResult.combinedPath.endsWith('.il')) {
            continue;
        }

        // Resolve and check the combined file path
        const { resolvedPath, fileExists } = await resolveFilePath(strcatResult.combinedPath, searchFolderPath);

        // If file doesn't exist, add warning diagnostics for each literal component
        if (resolvedPath && !fileExists) {
            for (const literal of strcatResult.pathLiterals) {
                // Find the position of this literal in the strcat call
                const literalRegex = new RegExp(`["']${literal.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}["']`, 'g');
                literalRegex.lastIndex = strcatResult.startIndex;
                const literalMatch = literalRegex.exec(text);

                if (!literalMatch) {
                    continue;
                }

                const literalStartIndex = literalMatch.index + 1; // Skip opening quote
                const start = document.positionAt(literalStartIndex);
                const end = document.positionAt(literalStartIndex + literal.length);
                const range = new vscode.Range(start, end);

                // Skip if inside a comment
                if (isInsideComment(document, start)) {
                    continue;
                }

                const diagnostic = new vscode.Diagnostic(
                    range,
                    `File not found (strcat combined path): ${resolvedPath}`,
                    vscode.DiagnosticSeverity.Warning
                );
                diagnostic.source = 'SKILL';
                diagnostics.push(diagnostic);
            }
        }
    }

    // Pattern 1c: Match load(variable) - analyze data flow
    const loadVarRegex = /load\s*\(\s*(\w+)\s*\)/g;

    while ((match = loadVarRegex.exec(text)) !== null) {
        const varName = match[1];
        const loadPosition = match.index;

        // Analyze variable data flow to find source file list
        const relatedFiles = analyzeVariableDataFlow(text, varName, loadPosition);

        // For each file found through data flow analysis, check if it exists
        for (const fileName of relatedFiles) {
            // Find the position of this filename in the list definition
            const fileNameRegex = new RegExp(`["']${fileName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}["']`, 'g');
            let fileMatch: RegExpExecArray | null;

            while ((fileMatch = fileNameRegex.exec(text)) !== null) {
                const fileNameStartIndex = fileMatch.index + 1; // Skip opening quote
                const start = document.positionAt(fileNameStartIndex);
                const end = document.positionAt(fileNameStartIndex + fileName.length);
                const range = new vscode.Range(start, end);

                // Skip if inside a comment
                if (isInsideComment(document, start)) {
                    continue;
                }

                // Skip if already processed
                const alreadyProcessed = diagnostics.some(d => d.range.isEqual(range));
                if (alreadyProcessed) {
                    continue;
                }

                // Skip if the filename contains format placeholders
                if (/%[sdfxiouXcp]/.test(fileName)) {
                    continue;
                }

                const { resolvedPath, fileExists } = await resolveFilePath(fileName, searchFolderPath);

                // If file doesn't exist, add a warning diagnostic
                if (resolvedPath && !fileExists) {
                    const diagnostic = new vscode.Diagnostic(
                        range,
                        `File not found (referenced by ${varName}): ${resolvedPath}`,
                        vscode.DiagnosticSeverity.Warning
                    );
                    diagnostic.source = 'SKILL';
                    diagnostics.push(diagnostic);
                }
            }
        }
    }

    diagnosticCollection.set(document.uri, diagnostics);
}

export function activate(context: vscode.ExtensionContext) {
    // Initialize diagnostic collection
    diagnosticCollection = vscode.languages.createDiagnosticCollection('skill-file-paths');
    context.subscriptions.push(diagnosticCollection);

    const fileLinkProvider: vscode.DocumentLinkProvider = {
        async provideDocumentLinks(document, token) {
            try {
                const text = document.getText();
                const links: vscode.DocumentLink[] = [];

                // Load search folder path from configuration
                const searchFolderPath = await loadSearchFolderPath();

                // Pattern 1: Match load("file.il") or load('file.il') - string literals
                const loadLiteralRegex = /load\s*\(\s*["']([:\w\-\\\/\.]+\.il)["']\s*\)/g;
                let match: RegExpExecArray | null;

                while ((match = loadLiteralRegex.exec(text)) !== null) {
                    // match[1] contains the filename
                    const fileNameStartIndex = match.index + match[0].indexOf(match[1]);
                    const start = document.positionAt(fileNameStartIndex);
                    const end = document.positionAt(fileNameStartIndex + match[1].length);

                    // Skip if inside a comment
                    if (isInsideComment(document, start)) {
                        continue;
                    }

                    let fileName = match[1];

                    // Skip if the filename contains format placeholders
                    if (/%[sdfxiouXcp]/.test(fileName)) {
                        continue;
                    }

                    const { resolvedPath } = await resolveFilePath(fileName, searchFolderPath);

                    if (resolvedPath) {
                        const fileUri = vscode.Uri.file(resolvedPath);
                        console.debug(`[SKILL Link] Created link: ${match[0]} at ${start.line}:${start.character} -> ${resolvedPath}`);
                        links.push(new vscode.DocumentLink(new vscode.Range(start, end), fileUri));
                    }
                }

                // Pattern 1b: Match load(strcat(...)) - parse strcat and create links
                const loadStrcatRegex = /load\s*\(\s*strcat\s*\(/g;

                while ((match = loadStrcatRegex.exec(text)) !== null) {
                    const loadStartPos = match.index;
                    const strcatStartPos = text.indexOf('strcat', loadStartPos);

                    // Parse the strcat call
                    const strcatResult = parseStrcatCall(text, strcatStartPos);

                    if (!strcatResult) {
                        continue;
                    }

                    // Skip if inside a comment
                    const loadPosition = document.positionAt(loadStartPos);
                    if (isInsideComment(document, loadPosition)) {
                        continue;
                    }

                    // Skip if the combined path contains format placeholders
                    if (/%[sdfxiouXcp]/.test(strcatResult.combinedPath)) {
                        continue;
                    }

                    // Check if the combined path is a valid .il file
                    if (!strcatResult.combinedPath.endsWith('.il')) {
                        continue;
                    }

                    // For each string literal in the strcat call, create a link
                    for (const literal of strcatResult.pathLiterals) {
                        // Find the position of this literal in the strcat call
                        const literalRegex = new RegExp(`["']${literal.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}["']`, 'g');
                        literalRegex.lastIndex = strcatResult.startIndex;
                        const literalMatch = literalRegex.exec(text);

                        if (!literalMatch) {
                            continue;
                        }

                        const literalStartIndex = literalMatch.index + 1; // Skip opening quote
                        const start = document.positionAt(literalStartIndex);
                        const end = document.positionAt(literalStartIndex + literal.length);
                        const range = new vscode.Range(start, end);

                        // Skip if inside a comment
                        if (isInsideComment(document, start)) {
                            continue;
                        }

                        // Try to resolve the combined path
                        const { resolvedPath } = await resolveFilePath(strcatResult.combinedPath, searchFolderPath);

                        if (resolvedPath) {
                            const fileUri = vscode.Uri.file(resolvedPath);
                            console.debug(`[SKILL Link] Created link via strcat: ${literal} (combined: ${strcatResult.combinedPath}) -> ${resolvedPath}`);
                            links.push(new vscode.DocumentLink(range, fileUri));
                        }
                    }
                }

                // Pattern 1c: Match load(variable) - analyze data flow and create links
                const loadVarRegex = /load\s*\(\s*(\w+)\s*\)/g;

                while ((match = loadVarRegex.exec(text)) !== null) {
                    const varName = match[1];
                    const loadPosition = match.index;

                    // Analyze variable data flow to find source file list
                    const relatedFiles = analyzeVariableDataFlow(text, varName, loadPosition);

                    // For each file found through data flow analysis, create links
                    for (const fileName of relatedFiles) {
                        // Find the position of this filename in the list definition
                        const fileNameRegex = new RegExp(`["']${fileName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}["']`, 'g');
                        let fileMatch: RegExpExecArray | null;

                        while ((fileMatch = fileNameRegex.exec(text)) !== null) {
                            const fileNameStartIndex = fileMatch.index + 1; // Skip opening quote
                            const start = document.positionAt(fileNameStartIndex);
                            const end = document.positionAt(fileNameStartIndex + fileName.length);
                            const range = new vscode.Range(start, end);

                            // Skip if inside a comment
                            if (isInsideComment(document, start)) {
                                continue;
                            }

                            // Skip if already processed
                            const alreadyProcessed = links.some(l => l.range.isEqual(range));
                            if (alreadyProcessed) {
                                continue;
                            }

                            // Skip if the filename contains format placeholders
                            if (/%[sdfxiouXcp]/.test(fileName)) {
                                continue;
                            }

                            const { resolvedPath } = await resolveFilePath(fileName, searchFolderPath);

                            if (resolvedPath) {
                                const fileUri = vscode.Uri.file(resolvedPath);
                                console.debug(`[SKILL Link] Created link via data flow: ${fileName} -> ${resolvedPath}`);
                                links.push(new vscode.DocumentLink(range, fileUri));
                            }
                        }
                    }
                }

                return links;
            } catch (error) {
                console.error(`[SKILL Link] Error providing document links: ${error instanceof Error ? error.message : 'Unknown error'}`);
                return [];
            }
        }
    };

    const filePathHoverProvider: vscode.HoverProvider = {
        async provideHover(document, position, token) {
            try {
                const text = document.getText();

                // Load search folder path from configuration
                const searchFolderPath = await loadSearchFolderPath();

                // Pattern 1: Match load("file.il") or load('file.il') - string literals
                const loadLiteralRegex = /load\s*\(\s*["']([:\w\-\\\/\.]+\.il)["']\s*\)/g;
                let match: RegExpExecArray | null;

                while ((match = loadLiteralRegex.exec(text)) !== null) {
                    // match[1] contains the filename
                    const fileNameStartIndex = match.index + match[0].indexOf(match[1]);
                    const start = document.positionAt(fileNameStartIndex);
                    const end = document.positionAt(fileNameStartIndex + match[1].length);
                    const range = new vscode.Range(start, end);

                    // Check if cursor is within this file path
                    if (!range.contains(position)) {
                        continue;
                    }

                    // Skip if inside a comment
                    if (isInsideComment(document, position)) {
                        continue;
                    }

                    let fileName = match[1];

                    // Skip if the filename contains format placeholders
                    if (/%[sdfxiouXcp]/.test(fileName)) {
                        continue;
                    }

                    const { resolvedPath, fileExists } = await resolveFilePath(fileName, searchFolderPath);

                    if (resolvedPath) {
                        let hoverText = `**📄 SKILL File**\n\n`;

                        if (fileExists) {
                            hoverText += `✅ **File found:**\n\`\`\`\n${resolvedPath}\n\`\`\`\n\n`;

                            // Add file stats if available
                            try {
                                const stats = fs.statSync(resolvedPath);
                                const fileSizeKB = (stats.size / 1024).toFixed(2);
                                const lastModified = stats.mtime.toLocaleString();
                                hoverText += `**Size:** ${fileSizeKB} KB\n\n`;
                                hoverText += `**Last Modified:** ${lastModified}`;
                            } catch (error) {
                                // Ignore stat errors
                            }
                        } else {
                            hoverText += `⚠️ **File not found:**\n\`\`\`\n${resolvedPath}\n\`\`\`\n\n`;
                            hoverText += `*This file may not exist or is inaccessible.*`;
                        }

                        return new vscode.Hover(new vscode.MarkdownString(hoverText, true), range);
                    }
                }

                // Pattern 1b: Check if hovering over a strcat-based load() call
                const loadStrcatRegex = /load\s*\(\s*strcat\s*\(/g;
                let strcatMatch: RegExpExecArray | null;

                while ((strcatMatch = loadStrcatRegex.exec(text)) !== null) {
                    const loadStartPos = strcatMatch.index;
                    const strcatStartPos = text.indexOf('strcat', loadStartPos);

                    // Parse the strcat call
                    const strcatResult = parseStrcatCall(text, strcatStartPos);

                    if (!strcatResult) {
                        continue;
                    }

                    // Skip if inside a comment
                    const loadPosition = document.positionAt(loadStartPos);
                    if (isInsideComment(document, loadPosition)) {
                        continue;
                    }

                    // Check each literal in the strcat call
                    for (const literal of strcatResult.pathLiterals) {
                        // Find the position of this literal in the strcat call
                        const literalRegex = new RegExp(`["']${literal.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}["']`, 'g');
                        literalRegex.lastIndex = strcatResult.startIndex;
                        const literalMatch = literalRegex.exec(text);

                        if (!literalMatch) {
                            continue;
                        }

                        const literalStartIndex = literalMatch.index + 1; // Skip opening quote
                        const start = document.positionAt(literalStartIndex);
                        const end = document.positionAt(literalStartIndex + literal.length);
                        const range = new vscode.Range(start, end);

                        // Check if cursor is within this literal
                        if (!range.contains(position)) {
                            continue;
                        }

                        // Skip if inside a comment
                        if (isInsideComment(document, position)) {
                            continue;
                        }

                        // Skip if the combined path contains format placeholders
                        if (/%[sdfxiouXcp]/.test(strcatResult.combinedPath)) {
                            continue;
                        }

                        // Check if the combined path is a valid .il file
                        if (!strcatResult.combinedPath.endsWith('.il')) {
                            continue;
                        }

                        const { resolvedPath, fileExists } = await resolveFilePath(strcatResult.combinedPath, searchFolderPath);

                        if (resolvedPath) {
                            let hoverText = `**📄 SKILL File (via strcat)**\n\n`;
                            hoverText += `**Combined path:** \`${strcatResult.combinedPath}\`\n\n`;

                            if (fileExists) {
                                hoverText += `✅ **File found:**\n\`\`\`\n${resolvedPath}\n\`\`\`\n\n`;

                                // Add file stats if available
                                try {
                                    const stats = fs.statSync(resolvedPath);
                                    const fileSizeKB = (stats.size / 1024).toFixed(2);
                                    const lastModified = stats.mtime.toLocaleString();
                                    hoverText += `**Size:** ${fileSizeKB} KB\n\n`;
                                    hoverText += `**Last Modified:** ${lastModified}`;
                                } catch (error) {
                                    // Ignore stat errors
                                }
                            } else {
                                hoverText += `⚠️ **File not found:**\n\`\`\`\n${resolvedPath}\n\`\`\`\n\n`;
                                hoverText += `*This file may not exist or is inaccessible.*`;
                            }

                            return new vscode.Hover(new vscode.MarkdownString(hoverText, true), range);
                        }
                    }
                }

                // Pattern 1c: Check if hovering over a file in a list related to load(variable)
                const ilFileRegex = /["']([:\w\-\\\/\.]+\.il)["']/g;

                while ((match = ilFileRegex.exec(text)) !== null) {
                    const fileNameStartIndex = match.index + 1; // Skip opening quote
                    const start = document.positionAt(fileNameStartIndex);
                    const end = document.positionAt(fileNameStartIndex + match[1].length);
                    const range = new vscode.Range(start, end);

                    // Check if cursor is within this file path
                    if (!range.contains(position)) {
                        continue;
                    }

                    // Skip if inside a comment
                    if (isInsideComment(document, position)) {
                        continue;
                    }

                    let fileName = match[1];

                    // Skip if the filename contains format placeholders
                    if (/%[sdfxiouXcp]/.test(fileName)) {
                        continue;
                    }

                    const { resolvedPath, fileExists } = await resolveFilePath(fileName, searchFolderPath);

                    if (resolvedPath) {
                        let hoverText = `**📄 SKILL File**\n\n`;

                        if (fileExists) {
                            hoverText += `✅ **File found:**\n\`\`\`\n${resolvedPath}\n\`\`\`\n\n`;

                            // Add file stats if available
                            try {
                                const stats = fs.statSync(resolvedPath);
                                const fileSizeKB = (stats.size / 1024).toFixed(2);
                                const lastModified = stats.mtime.toLocaleString();
                                hoverText += `**Size:** ${fileSizeKB} KB\n\n`;
                                hoverText += `**Last Modified:** ${lastModified}`;
                            } catch (error) {
                                // Ignore stat errors
                            }
                        } else {
                            hoverText += `⚠️ **File not found:**\n\`\`\`\n${resolvedPath}\n\`\`\`\n\n`;
                            hoverText += `*This file may not exist or is inaccessible.*`;
                        }

                        return new vscode.Hover(new vscode.MarkdownString(hoverText, true), range);
                    }
                }
            } catch (error) {
                console.error(`[SKILL Link] Error providing hover: ${error instanceof Error ? error.message : 'Unknown error'}`);
            }
            return undefined;
        }
    };

    context.subscriptions.push(
        vscode.languages.registerDocumentLinkProvider({ scheme: 'file', language: 'cadence-skill' }, fileLinkProvider),
        vscode.languages.registerHoverProvider({ scheme: 'file', language: 'cadence-skill' }, filePathHoverProvider)
    );

    // Update diagnostics on document open, change, and save
    context.subscriptions.push(
        vscode.workspace.onDidOpenTextDocument(updateDiagnostics),
        vscode.workspace.onDidChangeTextDocument(e => updateDiagnostics(e.document)),
        vscode.workspace.onDidSaveTextDocument(updateDiagnostics)
    );

    // Update diagnostics for all currently open documents
    vscode.workspace.textDocuments.forEach(updateDiagnostics);
}

export function deactivate() {
    // Clear caches to prevent memory leaks
    cachedSearchFolder = undefined;
    searchFolderLastModified = 0;

    // Clear diagnostics
    if (diagnosticCollection) {
        diagnosticCollection.clear();
        diagnosticCollection.dispose();
    }
}