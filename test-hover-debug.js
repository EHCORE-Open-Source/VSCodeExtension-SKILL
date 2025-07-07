/**
 * Debug script to test hover and signature help functionality
 */

const path = require('path');
const fs = require('fs');

// Simulate the path resolution that happens in the compiled extension
const outDir = path.join(__dirname, 'out');
const dbPath1 = path.join(outDir, 'builtin-procedures', 'databases', 'universal-procedures.json');
const dbPath2 = path.join(__dirname, 'src', 'builtin-procedures', 'databases', 'universal-procedures.json');

console.log('🔍 Testing Database Path Resolution');
console.log('='.repeat(40));

console.log('\n📁 Path Testing:');
console.log(`Compiled path: ${dbPath1}`);
console.log(`Exists: ${fs.existsSync(dbPath1) ? '✅ YES' : '❌ NO'}`);

console.log(`Source path: ${dbPath2}`);
console.log(`Exists: ${fs.existsSync(dbPath2) ? '✅ YES' : '❌ NO'}`);

// Test the database loading
let database = null;
let usedPath = null;

if (fs.existsSync(dbPath1)) {
    try {
        database = JSON.parse(fs.readFileSync(dbPath1, 'utf8'));
        usedPath = dbPath1;
        console.log('\n✅ Loaded database from compiled path');
    } catch (error) {
        console.log(`\n❌ Error loading from compiled path: ${error.message}`);
    }
} else if (fs.existsSync(dbPath2)) {
    try {
        database = JSON.parse(fs.readFileSync(dbPath2, 'utf8'));
        usedPath = dbPath2;
        console.log('\n✅ Loaded database from source path');
    } catch (error) {
        console.log(`\n❌ Error loading from source path: ${error.message}`);
    }
} else {
    console.log('\n❌ Database not found in either location');
}

if (database) {
    console.log('\n📊 Database Info:');
    console.log(`Used path: ${usedPath}`);
    console.log(`Total procedures: ${Object.keys(database.procedures).length}`);
    console.log(`Categories: ${database.metadata.categories.join(', ')}`);
    
    console.log('\n🔧 Sample Procedures:');
    const sampleProcs = ['car', 'printf', 'plus', 'if', 'let'];
    sampleProcs.forEach(proc => {
        if (database.procedures[proc]) {
            const info = database.procedures[proc];
            console.log(`✅ ${proc}: ${info.documentation.summary}`);
        } else {
            console.log(`❌ ${proc}: Not found`);
        }
    });
    
    console.log('\n🎯 Test Specific Function (car):');
    if (database.procedures.car) {
        const carInfo = database.procedures.car;
        console.log(`Name: ${carInfo.name}`);
        console.log(`Scope: ${carInfo.scope}`);
        console.log(`Category: ${carInfo.category}`);
        console.log(`Syntax: ${carInfo.documentation.syntax}`);
        console.log(`Summary: ${carInfo.documentation.summary}`);
        console.log(`Parameters: ${carInfo.documentation.parameters.length}`);
    }
} else {
    console.log('\n❌ No database available for testing');
}

console.log('\n' + '='.repeat(40));
console.log('🏁 Debug test completed');