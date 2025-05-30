import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

// Extend procedureIndex to include documentation
let procedureIndex: {
    [name: string]: {
        file: string,
        line: number,
        args: string[],
        doc: {
            summary: string,
            argDocs: { [arg: string]: string }
        }
    }
} = {};

// Parse documentation block for a procedure
function parseProcedureDoc(lines: string[], procLine: number, args: string[]): { summary: string, argDocs: { [arg: string]: string } } {
    // Default summary and argument docs
    const defaultSummary = 'No documentation available.';
    const defaultArgDoc = 'No documentation for this argument.';
    let summary = defaultSummary;
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
            // Extract <argumentName>...</argumentName> for each argument
            for (const arg of args) {
                // Remove any default value or formatting in arg name
                const argName = arg.split(/[ =]/)[0].replace(/[()]/g, '').trim();
                const argMatch = docLines.match(new RegExp(`<${argName}>([\\s\\S]*?)<\\/${argName}>`, 'i'));
                if (argMatch) {
                    argDocs[argName] = argMatch[1].trim();
                } else {
                    argDocs[argName] = defaultArgDoc;
                }
            }
        }
    } else {
        // No valid doc block, use defaults
        for (const arg of args) {
            const argName = arg.split(/[ =]/)[0].replace(/[()]/g, '').trim();
            argDocs[argName] = defaultArgDoc;
        }
    }
    return { summary, argDocs };
}

function loadSkillConfig(): string | undefined {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) { return; }
    const configPath = path.join(workspaceFolders[0].uri.fsPath, '.vscode', 'skill.json');
    console.debug(`Loaded skill configuration from ${configPath}`);

    // Check if the configuration file exists
    if (fs.existsSync(configPath)) {
        const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        let folderPath = config.skill.searchFolderPath;

        // If folderPath is a relative path, convert it to an absolute path.
        // Check if the absolute path starts with '/' or is a Windows absolute path. If not, assume it is relative to the workspace root directory.
        if (!folderPath.startsWith('/') && !/^[A-Z]:\\/i.test(folderPath)) {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (workspaceFolders && workspaceFolders.length > 0) {
                const workspaceRoot = workspaceFolders[0].uri.fsPath;
                folderPath = `${workspaceRoot}/${folderPath}`;
            }
        }

        // Return the absolute path to the skill folder
        console.debug(`Skill folder path: ${folderPath}`);
        return folderPath;
    }
}

function indexProcedures(skillFolder: string) {
    procedureIndex = {};
    const files = fs.readdirSync(skillFolder);
    files.forEach(file => {
        const filePath = path.join(skillFolder, file);
        console.debug(`Processing file: ${filePath}`);
        if (fs.statSync(filePath).isFile() && file.endsWith('.il')) {
            const lines = fs.readFileSync(filePath, 'utf8').split('\n');
            lines.forEach((line, idx) => {
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
            });
        }
    });
}

export function activate(context: vscode.ExtensionContext) {
    const skillFolder = loadSkillConfig();
    if (skillFolder) {
        indexProcedures(skillFolder);
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
        provideHover(document, position, token) {
            const wordRange = document.getWordRangeAtPosition(position);
            if (!wordRange) { return; }
            const word = document.getText(wordRange);
            const proc = procedureIndex[word];
            if (proc) {
                // Only show on invocation (must be followed by a left parenthesis)
                const after = document.getText(new vscode.Range(wordRange.end, wordRange.end.translate(0, 1)));
                if (after !== '(') { return; }
                const { requiredArgs, optionalArgs, keyArgs, restArgs } = splitArgs(proc.args);

                // Build hover text with documentation (markdown supported)
                let hoverText = `**procedure \`${word}\`**\n\n`;
                hoverText += `${proc.doc.summary}\n\n`;
                hoverText += `---\n`;

                // Helper to get argument doc
                const getArgDoc = (arg: string) => {
                    const argName = arg.split(/[ =]/)[0].replace(/[()]/g, '').trim();
                    return proc.doc.argDocs[argName] || 'No documentation for this argument.';
                };

                if (requiredArgs.length > 0) {
                    hoverText += `+ Arguments: ${formatArgList(requiredArgs)}\n`;
                    for (const arg of requiredArgs) {
                        hoverText += `  - \`${arg}\`: ${getArgDoc(arg)}\n`;
                    }
                    hoverText += `\n`;
                }
                if (optionalArgs.length > 0) {
                    hoverText += `+ Optional Arguments: ${formatArgList(optionalArgs)}\n`;
                    for (const arg of optionalArgs) {
                        hoverText += `  - \`${arg}\`: ${getArgDoc(arg)}\n`;
                    }
                    if (keyArgs.length > 0) {
                        hoverText += '\n';
                        hoverText += `> Key Arguments is ignored when optional arguments are provided.\n`;
                    }
                    if (restArgs.length > 0) {
                        hoverText += '\n';
                    }
                } else if (keyArgs.length > 0) {
                    hoverText += `+ Key Arguments: ${formatArgList(keyArgs)}\n`;
                    for (const arg of keyArgs) {
                        hoverText += `  - \`${arg}\`: ${getArgDoc(arg)}\n`;
                    }
                }
                if (restArgs.length > 0) {
                    hoverText += `+ Arbitrary Arguments: ${formatArgList(restArgs)}\n`;
                    for (const arg of restArgs) {
                        hoverText += `  - \`${arg}\`: ${getArgDoc(arg)}\n`;
                    }
                }
                // Use MarkdownString to support markdown in hover
                return new vscode.Hover(new vscode.MarkdownString(hoverText, true));
            }
        }
    };

    const signatureHelpProvider: vscode.SignatureHelpProvider = {
        provideSignatureHelp(document, position, token, context) {
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
            if (!procName || !procedureIndex[procName] || !openParenPos) { return; }

            // Get the text from the opening parenthesis to the cursor position (may be multi-line)
            const range = new vscode.Range(
                openParenPos.translate(0, 1), // after '('
                position
            );
            const textBefore = document.getText(range);

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

            const argList = parseSkillArgs(textBefore.trim());

            // Calculate cursor offset relative to textBefore
            const cursorOffset = textBefore.length;
            // Use getArgIndex to get the correct argument index
            let argIndex = getArgIndex(textBefore, cursorOffset);

            // Only move to next argument if last char is space and not inside any structure
            let inQuote = false;
            let inParen = 0;
            let inSpecialParen = false;
            for (let i = 0; i < textBefore.length; i++) {
                const c = textBefore[i];
                if (c === '"') {
                    inQuote = !inQuote;
                } else if (!inQuote && (c === "'" || c === '`') && textBefore[i + 1] === '(') {
                    inSpecialParen = true;
                    i++; // skip to '('
                    inParen++;
                } else if (!inQuote && c === '(') {
                    inParen++;
                } else if (!inQuote && c === ')') {
                    if (inParen > 0) { inParen--; }
                    if (inParen === 0) { inSpecialParen = false; }
                }
            }
            // Only move to next argument if last char is space and not inside any structure
            if (
                textBefore.endsWith(' ') &&
                !inQuote &&
                inParen === 0 &&
                !inSpecialParen
            ) {
                argIndex = argList.length;
            }

            const { requiredArgs, optionalArgs } = splitArgs(procedureIndex[procName].args);
            const allArgs = [...requiredArgs, ...optionalArgs];

            // Helper to get argument doc
            const getArgDoc = (arg: string) => {
                const argName = arg.split(/[ =]/)[0].replace(/[()]/g, '').trim();
                return new vscode.MarkdownString(procedureIndex[procName].doc.argDocs[argName] || 'No documentation for this argument.');
            };

            // Build signature help documentation (markdown supported)
            let sigDoc = `---\n\n${procedureIndex[procName].doc.summary}`; // Only procedure summary

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

    vscode.workspace.onDidSaveTextDocument(doc => {
        if (doc.fileName.endsWith('.il')) {
            const skillFolder = loadSkillConfig();
            if (skillFolder) {
                indexProcedures(skillFolder);
            }
        }
    });
}

function splitArgs(args: string[]) {
    const requiredArgs: string[] = [];
    const optionalArgs: string[] = [];
    const keyArgs: string[] = [];
    const restArgs: string[] = [];
    let optionalMode = false;
    let keyMode = false;
    let arbitraryMode = false;
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
            // Parse the syntax format: (word1 word2)
            const match = args[i].match(/^\(\s*(\S+)\s+(.+)\s*\)$/);
            if (match) {
                optionalArgs.push(`${match[1]} = ${match[2]}`);
            }
        } else if (keyMode) {
            // Parse the syntax format: (word1 word2)
            const match = args[i].match(/^\(\s*(\S+)\s+(.+)\s*\)$/);
            if (match) {
                keyArgs.push(`${match[1]} = ${match[2]}`);
            }
        } else {
            requiredArgs.push(args[i]);
        }
    }
    return { requiredArgs, optionalArgs, keyArgs, restArgs };
}

function formatArgList(args: string[]): string {
    return args.map(arg => `\`${arg.trim()}\``).join(', ');
}

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