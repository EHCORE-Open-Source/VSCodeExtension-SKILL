/**
 * Prompt generation system for SKILL universal procedures.
 * Creates comprehensive hover and signature help prompts from sklangref documentation.
 * 
 * STRICT REQUIREMENT: All code, comments, and documentation must be in English only.
 */

import { BuiltinProcedureInfo, ParameterInfo } from './types';

export class SkillPromptGenerator {
    /**
     * Generate enhanced hover prompt for a universal procedure
     */
    generateHoverPrompt(procedure: BuiltinProcedureInfo): string {
        const doc = procedure.documentation;
        let prompt = '';

        // Header with procedure name and category
        prompt += `**🔧 ${procedure.name}** *(${procedure.category})*\n\n`;

        // Summary
        if (doc.summary) {
            prompt += `📋 **Summary:** ${doc.summary}\n\n`;
        }

        // Syntax
        if (doc.syntax) {
            prompt += `**Syntax:**\n\`\`\`skill\n${doc.syntax}\n\`\`\`\n\n`;
        }

        // Parameters section
        if (doc.parameters && doc.parameters.length > 0) {
            prompt += `**Parameters:**\n`;
            doc.parameters.forEach(param => {
                const requiredText = param.required ? '' : ' *(optional)*';
                const typeText = param.type ? ` \`${param.type}\`` : '';
                const defaultText = param.default_value ? ` (default: \`${param.default_value}\`)` : '';
                
                prompt += `• **\`${param.name}\`**${typeText}${requiredText}${defaultText}  \n`;
                prompt += `  ${param.description}\n\n`;
            });
        }

        // Return value
        if (doc.return_value) {
            prompt += `**Returns:** ${doc.return_value}\n\n`;
        }

        // Examples
        if (doc.examples && doc.examples.length > 0) {
            prompt += `**Examples:**\n`;
            doc.examples.forEach(example => {
                prompt += `\`\`\`skill\n${example}\n\`\`\`\n\n`;
            });
        }

        // Notes
        if (doc.notes) {
            prompt += `**💡 Notes:** ${doc.notes}\n\n`;
        }

        // Source reference
        prompt += `---\n*📚 Source: ${procedure.source}*`;

        return prompt;
    }

    /**
     * Generate signature help prompt for a universal procedure
     */
    generateSignaturePrompt(procedure: BuiltinProcedureInfo): string {
        const doc = procedure.documentation;
        let prompt = '';

        // Brief summary for signature help
        if (doc.summary) {
            prompt += `📋 ${doc.summary}\n\n`;
        }

        // Quick parameter reference
        if (doc.parameters && doc.parameters.length > 0) {
            prompt += `**Parameters:**\n`;
            doc.parameters.forEach((param, index) => {
                const requiredText = param.required ? '**required**' : '*optional*';
                const typeText = param.type ? ` (\`${param.type}\`)` : '';
                
                prompt += `${index + 1}. **\`${param.name}\`**${typeText} - ${requiredText}  \n`;
                prompt += `   ${param.description}\n\n`;
            });
        }

        // Return value (brief)
        if (doc.return_value) {
            prompt += `**Returns:** ${doc.return_value}`;
        }

        return prompt;
    }

    /**
     * Generate parameter-specific prompt for signature help
     */
    generateParameterPrompt(procedure: BuiltinProcedureInfo, parameterIndex: number): string {
        const doc = procedure.documentation;
        
        if (!doc.parameters || parameterIndex >= doc.parameters.length) {
            return '';
        }

        const param = doc.parameters[parameterIndex];
        let prompt = '';

        prompt += `**\`${param.name}\`**`;
        
        if (param.type) {
            prompt += ` (\`${param.type}\`)`;
        }

        const requiredText = param.required ? ' - **Required**' : ' - *Optional*';
        prompt += requiredText;

        if (param.default_value) {
            prompt += ` (default: \`${param.default_value}\`)`;
        }

        prompt += `\n\n${param.description}`;

        return prompt;
    }

    /**
     * Generate autocomplete item description
     */
    generateAutocompleteDescription(procedure: BuiltinProcedureInfo): string {
        const doc = procedure.documentation;
        let description = '';

        // Brief summary
        if (doc.summary) {
            description += doc.summary;
        } else {
            description += `${procedure.category} function`;
        }

        // Add parameter count info
        if (doc.parameters) {
            const requiredCount = doc.parameters.filter(p => p.required).length;
            const totalCount = doc.parameters.length;
            
            if (requiredCount === totalCount) {
                description += ` (${totalCount} param${totalCount !== 1 ? 's' : ''})`;
            } else {
                description += ` (${requiredCount} required, ${totalCount - requiredCount} optional)`;
            }
        }

        return description;
    }

    /**
     * Generate quick reference card for a procedure
     */
    generateQuickReference(procedure: BuiltinProcedureInfo): string {
        const doc = procedure.documentation;
        let ref = '';

        // Compact syntax
        if (doc.syntax) {
            ref += `**${procedure.name}:** \`${doc.syntax}\`\n`;
        }

        // Brief description
        if (doc.summary) {
            ref += `${doc.summary}\n`;
        }

        // Quick example
        if (doc.examples && doc.examples.length > 0) {
            ref += `*Example:* \`${doc.examples[0]}\`\n`;
        }

        return ref;
    }

    /**
     * Generate category-based grouping prompt
     */
    generateCategoryPrompt(category: string, procedures: BuiltinProcedureInfo[]): string {
        let prompt = `## ${category}\n\n`;

        prompt += `**Available Functions (${procedures.length}):**\n\n`;

        procedures.forEach(proc => {
            const doc = proc.documentation;
            prompt += `• **\`${proc.name}\`** - ${doc.summary || 'No description available'}\n`;
            
            if (doc.syntax) {
                prompt += `  *Syntax:* \`${doc.syntax}\`\n`;
            }
            
            prompt += '\n';
        });

        return prompt;
    }

    /**
     * Generate learning-focused prompt with examples
     */
    generateLearningPrompt(procedure: BuiltinProcedureInfo): string {
        const doc = procedure.documentation;
        let prompt = '';

        prompt += `# Learning ${procedure.name}\n\n`;

        // What it does
        if (doc.summary) {
            prompt += `## What it does\n${doc.summary}\n\n`;
        }

        // How to use it
        if (doc.syntax) {
            prompt += `## Syntax\n\`\`\`skill\n${doc.syntax}\n\`\`\`\n\n`;
        }

        // Parameters explained
        if (doc.parameters && doc.parameters.length > 0) {
            prompt += `## Parameters\n`;
            doc.parameters.forEach((param, index) => {
                prompt += `### ${index + 1}. ${param.name}\n`;
                prompt += `- **Type:** ${param.type || 'any'}\n`;
                prompt += `- **Required:** ${param.required ? 'Yes' : 'No'}\n`;
                if (param.default_value) {
                    prompt += `- **Default:** \`${param.default_value}\`\n`;
                }
                prompt += `- **Description:** ${param.description}\n\n`;
            });
        }

        // Examples with explanations
        if (doc.examples && doc.examples.length > 0) {
            prompt += `## Examples\n`;
            doc.examples.forEach((example, index) => {
                prompt += `### Example ${index + 1}\n`;
                prompt += `\`\`\`skill\n${example}\n\`\`\`\n\n`;
            });
        }

        // Important notes
        if (doc.notes) {
            prompt += `## Important Notes\n${doc.notes}\n\n`;
        }

        return prompt;
    }
}

export const skillPromptGenerator = new SkillPromptGenerator();