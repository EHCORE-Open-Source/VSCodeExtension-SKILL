/**
 * Quick test script to verify the multi-tool compatibility system
 */

const fs = require('fs');
const path = require('path');

// Load the universal procedures database
const universalDbPath = path.join(__dirname, 'src', 'builtin-procedures', 'databases', 'universal-procedures.json');
const configPath = path.join(__dirname, '.vscode', 'skill.json');

console.log('🔧 Testing SKILL Multi-Tool Compatibility System');
console.log('='.repeat(50));

// Test 1: Check if files exist
console.log('\n📁 File Existence Check:');
console.log(`Universal DB: ${fs.existsSync(universalDbPath) ? '✅ EXISTS' : '❌ MISSING'}`);
console.log(`Config File: ${fs.existsSync(configPath) ? '✅ EXISTS' : '❌ MISSING'}`);

if (fs.existsSync(universalDbPath)) {
    try {
        const universalDb = JSON.parse(fs.readFileSync(universalDbPath, 'utf8'));
        console.log(`\n📊 Universal Procedures Database:`);
        console.log(`   Total procedures: ${Object.keys(universalDb.procedures).length}`);
        console.log(`   Sample procedures: ${Object.keys(universalDb.procedures).slice(0, 5).join(', ')}`);
    } catch (error) {
        console.log(`❌ Error reading universal DB: ${error.message}`);
    }
}

if (fs.existsSync(configPath)) {
    try {
        const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        console.log(`\n⚙️  Configuration:`);
        console.log(`   Primary tool: ${config.environment?.primary_tool || 'NOT SET'}`);
        console.log(`   Compatibility mode: ${config.compatibility?.mode || 'NOT SET'}`);
        console.log(`   Search path: ${config.search_folder_path || 'NOT SET'}`);
        
        const tools = config.environment?.tools || {};
        console.log(`   Configured tools:`);
        Object.entries(tools).forEach(([tool, info]) => {
            console.log(`     - ${tool}: v${info.version} (${info.subtools?.join(', ') || 'no subtools'})`);
        });
    } catch (error) {
        console.log(`❌ Error reading config: ${error.message}`);
    }
}

console.log('\n✅ Multi-tool compatibility system setup verification completed!');
console.log('\n📝 Next steps:');
console.log('   1. Test with VS Code extension');
console.log('   2. Create SKILL files to test hover/signature help');
console.log('   3. Verify compatibility warnings appear');