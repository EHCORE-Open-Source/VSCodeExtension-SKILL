import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

let procedureIndex: { [name: string]: { file: string, line: number, args: string[] } } = {};

function loadSkillConfig(): string | undefined {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) { return; }
    const configPath = path.join(workspaceFolders[0].uri.fsPath, '.vscode', 'skill.json');
    console.debug(`Loaded skill configuration from ${configPath}`);

    // Check if the configuration file exists
    if (fs.existsSync(configPath)) {
        const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        let folderPath = config.skillFolderPath;

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
                        procedureIndex[nameMatch[1]] = {
                            file: filePath,
                            line: idx,
                            args
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

                let hoverText = `**procedure \`${word}\`**\n\n`;
                if (requiredArgs.length > 0) {
                    hoverText += `+ Arguments: ${formatArgList(requiredArgs)}\n\n`;
                }
                if (optionalArgs.length > 0) {
                    hoverText += `+ Optional Arguments: ${formatArgList(optionalArgs)}`;
                    if( keyArgs.length > 0) {
                        hoverText += '\n\n';
                        hoverText += `> Key Arguments is ignored when optional arguments are provided.`;
                    }
                    if( restArgs.length > 0) {
                        hoverText += '\n\n';
                    }
                } else if (keyArgs.length > 0) {
                    hoverText += `+ Key Arguments: ${formatArgList(keyArgs)}`;
                }
                if (restArgs.length > 0) {
                    hoverText += `+ Arbitrary Arguments: ${formatArgList(restArgs)}`;
                }
                return new vscode.Hover(hoverText);
            }
        }
    };

    const signatureHelpProvider: vscode.SignatureHelpProvider = {
        provideSignatureHelp(document, position, token, context) {
            const line = document.lineAt(position.line).text;
            // Find the procedureName( before the current cursor position
            const regex = /(\w+)\s*\(/g;
            let match: RegExpExecArray | null;
            let procName: string | undefined;
            let lastParenIdx = -1;
            while ((match = regex.exec(line)) !== null) {
                if (position.character > match.index) {
                    procName = match[1];
                    lastParenIdx = match.index + match[0].length;
                }
            }
            if (!procName || !procedureIndex[procName]) { return; }

            const textBefore = line.slice(lastParenIdx, position.character);

            // Parse arguments, treating quoted strings as a single argument
            function parseSkillArgs(argStr: string): string[] {
                const args: string[] = [];
                let i = 0;
                const len = argStr.length;
                while (i < len) {
                    // Skip leading spaces
                    while (i < len && argStr[i] === ' ') { i++; }
                    if (i >= len) { break; }

                    let c = argStr[i];
                    let arg = '';

                    // Handle quoted string: "..."
                    if (c === '"') {
                        arg += c;
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
                        arg += c;
                        i++;
                        // Now handle the parenthesis group with nesting
                        if (argStr[i] === '(') {
                            let depth = 1;
                            arg += argStr[i];
                            i++;
                            while (i < len && depth > 0) {
                                if (argStr[i] === '(') { depth++; }
                                else if (argStr[i] === ')') { depth--; }
                                arg += argStr[i];
                                i++;
                            }
                        }
                        args.push(arg);
                        continue;
                    }

                    // Handle parenthesis group: (...), including nested
                    if (c === '(') {
                        let depth = 1;
                        arg += c;
                        i++;
                        while (i < len && depth > 0) {
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
                        arg += tableMatch[1];
                        i += tableMatch[1].length;
                        // Consume all chained brackets
                        while (i < len && argStr[i] === '[') {
                            let depth = 1;
                            arg += argStr[i];
                            i++;
                            while (i < len && depth > 0) {
                                if (argStr[i] === '[') { depth++; }
                                else if (argStr[i] === ']') { depth--; }
                                // Handle nested parentheses inside brackets
                                if (argStr[i] === '(') {
                                    let parenDepth = 1;
                                    arg += argStr[i++];
                                    while (i < len && parenDepth > 0) {
                                        if (argStr[i] === '(') { parenDepth++; }
                                        else if (argStr[i] === ')') { parenDepth--; }
                                        arg += argStr[i];
                                        i++;
                                    }
                                    continue;
                                }
                                arg += argStr[i];
                                i++;
                            }
                        }
                        args.push(arg);
                        continue;
                    }

                    // Handle normal word
                    while (i < len && argStr[i] !== ' ') {
                        arg += argStr[i];
                        i++;
                    }
                    if (arg.length > 0) {
                        args.push(arg);
                    }
                }
                return args.filter(Boolean);
            }

            const argList = parseSkillArgs(textBefore.trim());

            // Determine if the last character is a space outside of any structure
            let argIndex = Math.max(0, argList.length - 1);

            // Check if the cursor is after a complete argument and a space
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

            const signature = new vscode.SignatureInformation(
                `${procName}(${allArgs.join(' ')})`,
                `Arguments for procedure \`${procName}\``
            );
            signature.parameters = allArgs.map(arg => new vscode.ParameterInformation(arg));

            const sigHelp = new vscode.SignatureHelp();
            sigHelp.signatures = [signature];
            sigHelp.activeSignature = 0;

            // If the argument index is out of range, do not highlight any parameter
            if (argIndex >= allArgs.length) {
                sigHelp.activeParameter = -1;
            } else {
                sigHelp.activeParameter = argIndex;
            }

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