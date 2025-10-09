import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';

// Cache for skill search folder path
let cachedSearchFolder: string | undefined;
let searchFolderLastModified: number = 0;

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

export function activate(context: vscode.ExtensionContext) {
    const fileLinkProvider: vscode.DocumentLinkProvider = {
        async provideDocumentLinks(document, token) {
            try {
                const text = document.getText();
                const links: vscode.DocumentLink[] = [];
                const regex = /([:\w\-\\\/\.]+\.il)/g;
                let match: RegExpExecArray | null;

                // Load search folder path from configuration
                const searchFolderPath = await loadSearchFolderPath();

                while ((match = regex.exec(text)) !== null) {
                    const start = document.positionAt(match.index);
                    const end = document.positionAt(match.index + match[0].length);
                    let fileName = match[1];
                    let resolvedPath: string | undefined;

                    // If fileName is already an absolute path, use it directly
                    if (fileName.startsWith('/') || /^[A-Z]:\\/i.test(fileName)) {
                        resolvedPath = fileName;
                    } else {
                        // Extract just the filename (without any path components)
                        const baseFileName = path.basename(fileName);

                        // Try to find file in searchFolderPath first (if configured)
                        if (searchFolderPath) {
                            console.debug(`[SKILL Link] Searching for ${baseFileName} in ${searchFolderPath}`);
                            resolvedPath = findFileInDirectory(searchFolderPath, baseFileName);

                            if (resolvedPath) {
                                console.debug(`[SKILL Link] Found file in search folder: ${resolvedPath}`);
                            }
                        }

                        // If not found in searchFolderPath, fall back to workspace root
                        if (!resolvedPath) {
                            const workspaceFolders = vscode.workspace.workspaceFolders;
                            if (workspaceFolders && workspaceFolders.length > 0) {
                                const workspaceRoot = workspaceFolders[0].uri.fsPath;
                                resolvedPath = path.join(workspaceRoot, fileName);
                                console.debug(`[SKILL Link] Falling back to workspace root: ${resolvedPath}`);
                            }
                        }
                    }

                    if (resolvedPath) {
                        const fileUri = vscode.Uri.file(resolvedPath);
                        console.debug(`[SKILL Link] Created link: ${match[0]} at ${start.line}:${start.character} -> ${resolvedPath}`);
                        links.push(new vscode.DocumentLink(new vscode.Range(start, end), fileUri));
                    }
                }
                return links;
            } catch (error) {
                console.error(`[SKILL Link] Error providing document links: ${error instanceof Error ? error.message : 'Unknown error'}`);
                return [];
            }
        }
    };

    context.subscriptions.push(
        vscode.languages.registerDocumentLinkProvider({ scheme: 'file', language: 'cadence-skill' }, fileLinkProvider)
    );
}

export function deactivate() {
    // Clear caches to prevent memory leaks
    cachedSearchFolder = undefined;
    searchFolderLastModified = 0;
}