#!/bin/bash
# Shell script for creating VSIX package on Linux/macOS

# User variable setting
outputFolder="vsix"

# Check that vsce is available; if not, ask the user whether to install it
if ! command -v vsce >/dev/null 2>&1; then
    echo "vsce (@vscode/vsce) is not installed."
    if [ ! -t 0 ]; then
        echo "Non-interactive shell: install it with 'npm install -g @vscode/vsce' and run again"
        exit 1
    fi
    if ! command -v npm >/dev/null 2>&1; then
        echo "npm was not found; install Node.js first, then run 'npm install -g @vscode/vsce'"
        exit 1
    fi
    read -r -p "Install it now with 'npm install -g @vscode/vsce'? [y/N] " answer
    case "$answer" in
        [yY]|[yY][eE][sS])
            npm install -g @vscode/vsce
            if [ $? -ne 0 ] || ! command -v vsce >/dev/null 2>&1; then
                echo "Failed to install vsce"
                exit 1
            fi
            ;;
        *)
            echo "vsce is required to create the VSIX package"
            exit 1
            ;;
    esac
fi

# If the output folder doesn't exist, create the output folder
if [ ! -d "$outputFolder" ]; then
    mkdir -p "$outputFolder"
fi

# Compile and package a VSIX extension file
echo "Creating VSIX package..."
vsce package --out "$outputFolder"

# Check if the command was successful
if [ $? -eq 0 ]; then
    echo "VSIX package created successfully in $outputFolder folder"
else
    echo "Failed to create VSIX package"
    exit 1
fi