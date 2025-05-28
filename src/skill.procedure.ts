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
                const match = line.match(/^\s*procedure\(\s*(\w+)\s*\(([^\)]*)\)/i);
                if (match) {
                    console.debug(`Found procedure: ${match[1]} in ${filePath} at line ${idx + 1}`);
                    procedureIndex[match[1]] = {
                        file: filePath,
                        line: idx,
                        args: match[2].split(',').map(s => s.trim()).filter(Boolean)
                    };
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

    context.subscriptions.push(
        vscode.languages.registerDocumentLinkProvider({ scheme: 'file', language: 'cadence-skill' }, provider)
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
}