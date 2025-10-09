import * as vscode from 'vscode';

// This method is called when your extension is activated
// Your extension is activated the very first time the command is executed
export function activate(context: vscode.ExtensionContext) {
    context.subscriptions.push(vscode.languages.registerDocumentSymbolProvider({ scheme: "file", language: "cadence-skill" }, new DocumentSymbolProvider()));
}

interface Element {
    Name: string;
    Symbol: vscode.SymbolKind;
    Description: string;
    Line: vscode.Range;
    Elements?: Element[];
}

class DocumentSymbolProvider implements vscode.DocumentSymbolProvider {
    /**
     * Find the end position of a procedure block by matching parentheses
     * @param document The text document
     * @param startLine Line number where procedure declaration starts
     * @param startChar Character position of the opening parenthesis after 'procedure'
     * @returns The end position of the procedure block, or undefined if not found
     */
    private findProcedureEnd(
        document: vscode.TextDocument,
        startLine: number,
        startChar: number
    ): vscode.Position | undefined {
        let depth = 0;
        let inString = false;
        let inLineComment = false;
        let inBlockComment = false;

        // Start from the opening parenthesis
        for (let lineNum = startLine; lineNum < document.lineCount; lineNum++) {
            const line = document.lineAt(lineNum).text;
            const startCharPos = (lineNum === startLine) ? startChar : 0;

            for (let charPos = startCharPos; charPos < line.length; charPos++) {
                const char = line[charPos];
                const nextChar = charPos + 1 < line.length ? line[charPos + 1] : '';

                // Handle string mode
                if (!inLineComment && !inBlockComment && char === '"') {
                    inString = !inString;
                    continue;
                }

                // Handle block comments
                if (!inString && !inLineComment && char === '/' && nextChar === '*') {
                    inBlockComment = true;
                    charPos++; // Skip next character
                    continue;
                }
                if (inBlockComment && char === '*' && nextChar === '/') {
                    inBlockComment = false;
                    charPos++; // Skip next character
                    continue;
                }

                // Handle line comments
                if (!inString && !inBlockComment && char === ';') {
                    inLineComment = true;
                    continue;
                }

                // Skip characters inside comments or strings
                if (inString || inLineComment || inBlockComment) {
                    continue;
                }

                // Count parentheses
                if (char === '(') {
                    depth++;
                } else if (char === ')') {
                    depth--;
                    if (depth === 0) {
                        // Found the matching closing parenthesis
                        return new vscode.Position(lineNum, charPos);
                    }
                }
            }

            // Reset line comment at end of line
            inLineComment = false;
        }

        // If we reach here, no matching parenthesis was found
        return undefined;
    }

    public createSymbol(
        symbol: Element
    ): vscode.DocumentSymbol {
        let result = new vscode.DocumentSymbol(
            symbol.Name,
            symbol.Description,
            symbol.Symbol,
            symbol.Line,
            symbol.Line
        );
        return result;
    }

    public createElementSymbol(
        content: string,
        lineRange: vscode.Range,
        fullRange?: vscode.Range
    ): Element {
        let symbol: vscode.SymbolKind;
        let procedure = '';
        if (content.match(/^\s*procedure\(/i)) {
            symbol = vscode.SymbolKind.Function;
            let match = content.match(/^\s*procedure\(\s*(\w+)/i);
            if (match) {
                procedure = match[1];
            }
        }
        else {
            symbol = vscode.SymbolKind.Null;
        }

        return {
            Name: procedure,
            Description: '',
            Symbol: symbol,
            Line: fullRange || lineRange
        };
    }

    public provideDocumentSymbols(
        document: vscode.TextDocument,
        token: vscode.CancellationToken): Promise<vscode.DocumentSymbol[]> {

            const netlist: Element[] = [];
            for (let i = 0; i < document.lineCount; i++) {
                const line = document.lineAt(i);
                const linePreprocessing = line.text.trim();
                let matchObj: RegExpMatchArray | null;

                // Procedure processing
                matchObj = linePreprocessing.match(/^\s*procedure\(/ig);
                if (matchObj) {
                    // Find the position of 'procedure(' in the original line
                    const procMatch = line.text.match(/procedure\s*\(/i);
                    if (procMatch && procMatch.index !== undefined) {
                        // Find the opening parenthesis position
                        const openParenPos = procMatch.index + procMatch[0].length - 1;

                        // Find the matching closing parenthesis
                        const endPos = this.findProcedureEnd(document, i, openParenPos);

                        // Create full range from procedure start to end
                        let fullRange: vscode.Range;
                        if (endPos) {
                            fullRange = new vscode.Range(
                                line.range.start,
                                endPos.translate(0, 1) // Include the closing parenthesis
                            );
                        } else {
                            // Fallback: use single line if end not found
                            fullRange = line.range;
                        }

                        const newElement = this.createElementSymbol(linePreprocessing, line.range, fullRange);
                        netlist.push(newElement);
                    }
                    continue;
                }
            }

            return new Promise((resolve) => {
                const symbols: vscode.DocumentSymbol[] = [];
                const nodes = [symbols];

                for (let i=0; i<netlist.length; i++) {
                    const newNode = this.createSymbol(netlist[i]);
                    nodes[nodes.length - 1].push(newNode);
                }
                resolve(symbols);
            }
        );
    }
}

// This method is called when your extension is deactivated
export function deactivate() {}