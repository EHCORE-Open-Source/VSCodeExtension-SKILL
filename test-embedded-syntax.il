/*
Test file for embedded language syntax highlighting in SKILL comments

Example 1: YAML syntax highlighting
```yaml
# Configuration file example
server:
  host: localhost
  port: 8080
  ssl:
    enabled: true
    certificate: /path/to/cert.pem

database:
  type: postgresql
  connection:
    host: db.example.com
    port: 5432
    user: admin
    password: secret123

features:
  - name: auto-save
    enabled: true
    interval: 300
  - name: backup
    enabled: false
    schedule: "0 2 * * *"
```

Example 2: Markdown syntax highlighting
```markdown
# SKILL Function Documentation

## Overview
This is a **powerful** function that does _amazing_ things.

### Features
- Feature 1: Fast processing
- Feature 2: Low memory usage
- Feature 3: Easy to use

### Code Example
\`\`\`skill
procedure(myFunction(arg1 arg2)
    let((result)
        result = arg1 + arg2
        println("Result: %L" result)
    )
)
\`\`\`

> **Note**: This function requires SKILL version 6.1 or higher.

### See Also
- [Related Function 1](#)
- [Related Function 2](#)
```

Example 3: JSON syntax highlighting
```json
{
  "name": "SKILL Configuration",
  "version": "1.0.0",
  "settings": {
    "autoComplete": true,
    "searchFolderPath": "/home/user/skill",
    "theme": "dark"
  },
  "procedures": [
    {
      "name": "myProcedure",
      "parameters": ["arg1", "arg2"],
      "returnType": "list"
    }
  ],
  "shortcuts": {
    "compile": "Ctrl+B",
    "run": "F5",
    "debug": "F9"
  }
}
```

Example 4: Mixed usage in procedure documentation
*/

/*
<@summary>
🎯 Process configuration data from multiple formats

This procedure can handle configuration in various formats:

```yaml
config:
  mode: production
  debug: false
```

Or in JSON:

```json
{
  "config": {
    "mode": "production",
    "debug": false
  }
}
```
</@summary>

<configData>
📥 Configuration data in YAML or JSON format
Can be a string or data structure
</configData>

<@return>
📤 Parsed configuration as a property list
</@return>

<@note>
⚠️ Supported formats:
- YAML (requires yaml parser)
- JSON (native support)
- XML (limited support)
</@note>

<@example>
💡 Usage with YAML:

```yaml
server:
  host: localhost
  port: 8080
```

```skill
config = parseConfig(yamlString)
println("Host: %s" config->server->host)
```
</@example>
*/
procedure(parseConfig(configData @optional (format "yaml"))
    let((result parser)
        ; Parse based on format
        case(format
            ("yaml"
                parser = getYamlParser()
                result = parser->parse(configData)
            )
            ("json"
                result = parseJSON(configData)
            )
            (t
                error("Unsupported format: %s" format)
            )
        )
        result
    )
)

/*
Another example with embedded documentation
```markdown
## Task List
- [x] Implement YAML support
- [x] Implement JSON support
- [ ] Implement XML support
- [ ] Add validation

### Priority Matrix
| Task | Priority | Status |
|------|----------|--------|
| YAML | High | Done |
| JSON | High | Done |
| XML  | Low  | Todo |
```
*/

; Regular SKILL code
procedure(testFunction()
    println("Testing embedded syntax highlighting")
)
