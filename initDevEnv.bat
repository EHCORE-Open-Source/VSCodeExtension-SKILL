@echo off
npm install -g typescript ts-node yo generator-code eslint
npm install -g vscode
npm install @types/node
npm install @types/vscode@1.88.0
npm audit fix --force
npm uninstall @types/mocha
rd /s /q node_modules\@types\mocha
