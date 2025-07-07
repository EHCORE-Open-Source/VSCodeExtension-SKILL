// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import {default as skillCompletionConfig} from './config/skill.completion.json';

interface SkillConfig {
    skill: {
        autoComplete: boolean;
    };
}

const languageCompletionSet: Set<string> = new Set<string>();
const languageCompletionDatabase: { [key: string]: vscode.CompletionItem[]; } = {};
let cachedConfig: boolean | null = null;
let configLastModified: number = 0;

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {
    
    // Use the console to output diagnostic information (console.log) and errors (console.error)
    // This line of code will only be executed once when your extension is activated

    const defaultCompletionProvider = vscode.languages.registerCompletionItemProvider('cadence-skill', {provideCompletionItems});
    context.subscriptions.push(defaultCompletionProvider);

    console.log('Congratulations, the extension "VSCodeExtension-SKILL" is now active!');
}

function getFunctionDescription(description: string[][]): vscode.MarkdownString {
    const topicSet = new vscode.MarkdownString();
    description.forEach(topic => {
        topicSet.appendMarkdown(topic.join(' '));
        topicSet.appendText('\n');
        topicSet.isTrusted = true;
    });
    return topicSet;
}

function loadSkillConfig(): boolean {
    const defaultAutoComplete = false;
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) { return defaultAutoComplete; }
    
    const configPath = path.join(workspaceFolders[0].uri.fsPath, '.vscode', 'skill.json');
    
    try {
        // Check if we have cached config and file hasn't changed
        if (cachedConfig !== null && fs.existsSync(configPath)) {
            const stats = fs.statSync(configPath);
            if (stats.mtime.getTime() === configLastModified) {
                return cachedConfig;
            }
        }

        // Check if the configuration file exists
        if (fs.existsSync(configPath)) {
            const stats = fs.statSync(configPath);
            const configContent = fs.readFileSync(configPath, 'utf8');
            const config: SkillConfig = JSON.parse(configContent);
            
            let autoComplete = config.skill?.autoComplete;
            if (autoComplete === undefined || autoComplete === null) {
                autoComplete = defaultAutoComplete;
            }

            // Cache the result
            cachedConfig = autoComplete;
            configLastModified = stats.mtime.getTime();
            
            console.debug(`Auto-complete enabled: ${autoComplete}`);
            return autoComplete;
        }
    } catch (error) {
        console.error(`Failed to load skill configuration: ${error instanceof Error ? error.message : 'Unknown error'}`);
        return defaultAutoComplete;
    }

    // If the configuration file does not exist, return false
    cachedConfig = defaultAutoComplete;
    return defaultAutoComplete;
}

function provideCompletionItems(document: vscode.TextDocument, position: vscode.Position, token: vscode.CancellationToken, context: vscode.CompletionContext): vscode.CompletionItem[] | null {
    // Check if auto-complete is enabled first to avoid unnecessary work
    if (!loadSkillConfig()) {
        return null;
    }

    // If the auto-complete function has been added, it will not be repeated.
    if (!languageCompletionSet.has(document.languageId)) {
        languageCompletionSet.add(document.languageId);

        // Add the auto-completion keyword
        const completionList: vscode.CompletionItem[] = [];
        
        try {
            skillCompletionConfig.functions.forEach(funcReference => {
                Object.values(funcReference.definitions).forEach(funcArray => {
                    funcArray.forEach(funcSet => {
                        funcSet.name_collection.forEach(funcName => {
                            const completionItem = new vscode.CompletionItem(funcName);
                            completionItem.kind = vscode.CompletionItemKind.Function;
                            completionItem.detail = funcReference.comment;
                            completionItem.documentation = getFunctionDescription(funcSet.description);
                            completionList.push(completionItem);
                        });
                    });
                });
            });
            languageCompletionDatabase[document.languageId] = completionList;
        } catch (error) {
            console.error(`Failed to build completion items: ${error instanceof Error ? error.message : 'Unknown error'}`);
            return null;
        }
    }

    // Return the completion items for the current language
    return languageCompletionDatabase[document.languageId] || null;
}

// This method is called when your extension is deactivated
export function deactivate() {
    // Clear caches to prevent memory leaks
    languageCompletionSet.clear();
    Object.keys(languageCompletionDatabase).forEach(key => {
        delete languageCompletionDatabase[key];
    });
    cachedConfig = null;
    configLastModified = 0;
}
