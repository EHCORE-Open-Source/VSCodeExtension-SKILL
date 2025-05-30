// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import {default as skillCompletionConfig} from './config/completion.skill.json';

var languageCompletionSet: Set<string> = new Set<string>();
var languageCompletionDatabase: { [key: string]: vscode.CompletionItem[]; } = {};

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {
    
    // Use the console to output diagnostic information (console.log) and errors (console.error)
    // This line of code will only be executed once when your extension is activated

    const defaultCompletionProvider = vscode.languages.registerCompletionItemProvider('cadence-skill', {provideCompletionItems});
    context.subscriptions.push(defaultCompletionProvider);

    console.log('Congratulations, the extension "VSCodeExtension-SKILL" is now active!');
}

function getFunctionDescription(description: string[][]) {
    var topicSet = new vscode.MarkdownString();
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
    console.debug(`Loaded skill configuration from ${configPath}`);

    // Check if the configuration file exists
    if (fs.existsSync(configPath)) {
        const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        let autoComplete = config.skill.autoComplete;
        if( autoComplete === undefined || autoComplete === null) {
            autoComplete = defaultAutoComplete; // Default to false if not specified
        }

        // Check if the auto-complete configuration is enabled
        console.debug(`Auto-complete enabled: ${autoComplete}`);
        return autoComplete;
    }

    // If the configuration file does not exist, return false
    return defaultAutoComplete;
}

function provideCompletionItems(document: vscode.TextDocument, position: vscode.Position, token: vscode.CancellationToken, context: vscode.CompletionContext) {
    // If the auto-complete function has been added, it will not be repeated.
    if (!languageCompletionSet.has(document.languageId)) {
        languageCompletionSet.add(document.languageId);

        // Add the auto-completion keyword
        let completionList = new Array();
        skillCompletionConfig.functions.forEach(funcReference => {
            funcReference.definitions.forEach(funcSet => {
                funcSet.name_collection.forEach(funcName => {
                    let completionItem = new vscode.CompletionItem(funcName);
                    completionItem.kind = vscode.CompletionItemKind.Function;
                    completionItem.detail = funcReference.comment;
                    completionItem.documentation = getFunctionDescription(funcSet.description);
                    completionList.push(completionItem);
                });
            });
        });
        languageCompletionDatabase[document.languageId] = completionList;
    }

    // Return the completion items for the current language
    if( loadSkillConfig() ) {
        return languageCompletionDatabase[document.languageId];
    }

    // If auto-complete is not enabled, return null
    return null;
}

// This method is called when your extension is deactivated
export function deactivate() {}
