import vscode from 'vscode';

export function exec(context: vscode.ExtensionContext) {
    context.subscriptions.push(vscode.languages.registerDocumentSymbolProvider({ scheme: "file", language: "cadence-skill" }, new DocumentSymbolProvider()));
}

interface element {
    "Name": string,
    "Symbol": vscode.SymbolKind,
    "Description": string,
    "Line": vscode.Range,
    "Elements"?: element[]
};

class DocumentSymbolProvider implements vscode.DocumentSymbolProvider {
    public createSymbol(
        symbol: element
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
        lineRange: vscode.Range
    ): element {
        let symbol: vscode.SymbolKind;
        let procedure: string = '';
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
            "Name": procedure, 
            "Description": '',
            "Symbol": symbol, 
            "Line": lineRange
        };
    }

    public provideDocumentSymbols(
        document: vscode.TextDocument,
        token: vscode.CancellationToken): Promise<vscode.DocumentSymbol[]> {

            let netlist: element[] = new Array;
            for (let i = 1; i < document.lineCount; i++) {
                let line = document.lineAt(i);
                let linePreprocessing = line.text.trim();
                let matchObj: RegExpMatchArray | null;
                
                // Procedure processing
                matchObj = linePreprocessing.match(/^\s*procedure\(/ig);
                if (matchObj) {
                    const newElement = this.createElementSymbol(linePreprocessing, line.range);
                    netlist.push(newElement);
                    continue;
                }
            }
            
            return new Promise((resolve) => {
                let symbols: vscode.DocumentSymbol[] = [];
                let nodes = [symbols];

                for (let i=0; i<netlist.length; i++) {
                    let newNode = this.createSymbol(netlist[i]);
                    nodes[nodes.length - 1].push(newNode);
                }
                resolve(symbols);
            }
        );
    }
}