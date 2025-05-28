import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
    const fileLinkProvider: vscode.DocumentLinkProvider = {
        provideDocumentLinks(document, token) {
            const text = document.getText();
            const links: vscode.DocumentLink[] = [];
            const regex = /([:\w\-\\\/\.]+\.il)/g;
            let match: RegExpExecArray | null;
            while ((match = regex.exec(text)) !== null) {
                const start = document.positionAt(match.index);
                const end = document.positionAt(match.index + match[0].length);
                let fileName = match[1];

                // If fileName is a relative path, convert it to an absolute path.
                // Check if the absolute path starts with '/' or is a Windows absolute path. If not, assume it is relative to the workspace root directory.
                if (!fileName.startsWith('/') && !/^[A-Z]:\\/i.test(fileName)) {
                    const workspaceFolders = vscode.workspace.workspaceFolders;
                    if (workspaceFolders && workspaceFolders.length > 0) {
                        const workspaceRoot = workspaceFolders[0].uri.fsPath;
                        fileName = `${workspaceRoot}/${fileName}`;
                    }
                }

                const fileUri = vscode.Uri.file(fileName);
                console.debug(`Found link: ${match[0]} at ${start.line}:${start.character} to ${fileName}`);
                links.push(new vscode.DocumentLink(new vscode.Range(start, end), fileUri));
            }
            return links;
        }
    };

    context.subscriptions.push(
        vscode.languages.registerDocumentLinkProvider({ scheme: 'file', language: 'cadence-skill' }, fileLinkProvider)
    );
}

export function deactivate() {}