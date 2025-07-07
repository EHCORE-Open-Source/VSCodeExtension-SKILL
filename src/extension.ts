// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
import * as vscode from 'vscode';
import * as skillCompletion from './skill.completion';
import * as skillOutline from './skill.outline';
import * as skillLink from './skill.link';
import * as skillProcedure from './skill.procedure';

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export async function activate(context: vscode.ExtensionContext) {
    console.log('[SKILL] Main extension activating...');
    skillCompletion.activate(context);
    skillOutline.activate(context);
    skillLink.activate(context);
    await skillProcedure.activate(context);
    console.log('[SKILL] Main extension activation complete');
}

// This method is called when your extension is deactivated
export function deactivate() {}
