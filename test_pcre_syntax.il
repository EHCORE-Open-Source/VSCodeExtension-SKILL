; ============================================================================
; PCRE & REX Syntax Highlighting Test Suite
; This file comprehensively tests PCRE and REX syntax highlighting
; ============================================================================
;
; ⚠️ IMPORTANT: REX vs PCRE Differences
; ============================================================================
; REX is a SIMPLER regular expression system than PCRE!
;
; REX does NOT support these PCRE features:
; - \s \d \w character classes → Use [0-9], [a-z], [ \t] instead
; - \b word boundary → Use \< and \> instead
; - {n,m} quantifiers → Only * and + are supported
; - (?:...) non-capturing groups → Not supported
; - (?=...) lookahead/lookbehind → Not supported
; - \t \r \n control characters → Not supported
;
; REX grouping uses ESCAPED parens: \( \)  (not unescaped like PCRE)
; REX backreferences: \1 \2 \3 (same as PCRE)
; ============================================================================

; ============================================================================
; PCRE Tests - Basic Escape Sequences
; ============================================================================

; Test 1.1: Character class escapes
pcreCompile( "\\s+\\S+\\d+\\D+\\w+\\W+" )        ; Whitespace, digit, word classes
pcreCompile( "\\b\\w+\\b" )                      ; Word boundaries
pcreCompile( "\\Btest\\B" )                      ; Non-word boundaries

; Test 1.2: Special character escapes
pcreCompile( "\\(\\)\\[\\]\\{\\}\\." )          ; Escaped metacharacters
pcreCompile( "\\+\\*\\?\\|\\^\\$" )             ; Escaped operators
pcreCompile( "a\\.b\\*c\\+d\\?" )               ; Mixed escapes

; Test 1.3: Whitespace and control characters
pcreCompile( "\\t\\r\\n\\f\\v" )                ; Tab, return, newline, form feed, vertical tab

; ============================================================================
; PCRE Tests - Character Sets
; ============================================================================

; Test 2.1: Basic character sets
pcreCompile( "[abc]" )                           ; Simple character set
pcreCompile( "[^abc]" )                          ; Negated character set
pcreCompile( "[a-zA-Z0-9]" )                    ; Range character set
pcreCompile( "[a-z&&[^aeiou]]" )                ; Character set intersection

; Test 2.2: Character set with escapes
pcreCompile( "[\\s\\d\\w]" )                    ; Character classes in sets
pcreCompile( "[\\(\\)\\[\\]]" )                 ; Escaped metacharacters in sets
pcreCompile( "[^()\\[\\]]" )                    ; Mixed escapes in negated sets

; Test 2.3: POSIX character classes
pcreCompile( "[[:alnum:]]" )                    ; Alphanumeric
pcreCompile( "[[:alpha:]][[:digit:]]" )         ; Alpha and digit
pcreCompile( "[[:space:]][[:punct:]]" )         ; Space and punctuation

; ============================================================================
; PCRE Tests - Quantifiers
; ============================================================================

; Test 3.1: Basic quantifiers
pcreCompile( "a*b+c?d{2}e{2,}f{2,5}" )         ; All quantifier types
pcreCompile( "\\s*\\d+\\w?" )                   ; Quantifiers with character classes
pcreCompile( "\\(test\\)*" )                    ; Quantifiers with escaped parens

; Test 3.2: Non-greedy quantifiers
pcreCompile( ".*?" )                            ; Non-greedy any
pcreCompile( "\\s+?" )                          ; Non-greedy whitespace
pcreCompile( "\\w{2,5}?" )                      ; Non-greedy range

; Test 3.3: Quantifier ? vs. Special group ? - Different highlighting
pcreCompile( "a?" )                             ; Quantifier: a is optional (should be operator color)
pcreCompile( "\\d?" )                           ; Quantifier: digit is optional (should be operator color)
pcreCompile( "(?:abc)" )                        ; Special group: ?:  (should be keyword/group color)
pcreCompile( "(?=test)" )                       ; Special group: ?=  (should be keyword/group color)
pcreCompile( "a?(?:b+)?c?" )                    ; Mixed: quantifier ? and group ? (different colors)

; ============================================================================
; PCRE Tests - Groups and Alternation
; ============================================================================

; Test 4.1: Capturing groups
pcreCompile( "(abc)" )                          ; Simple capturing group
pcreCompile( "(\\w+)\\s+(\\d+)" )              ; Multiple capturing groups
pcreCompile( "((\\w+)\\s+(\\d+))" )            ; Nested capturing groups

; Test 4.2: Non-capturing groups
pcreCompile( "(?:abc)" )                        ; Non-capturing group
pcreCompile( "(?:abc|def|ghi)" )               ; Alternation in non-capturing group
pcreCompile( "(?:\\s*\\d+)*" )                 ; Non-capturing with quantifier

; Test 4.3: Special groups
pcreCompile( "(?=abc)" )                        ; Positive lookahead
pcreCompile( "(?!abc)" )                        ; Negative lookahead
pcreCompile( "(?<=abc)" )                       ; Positive lookbehind
pcreCompile( "(?<!abc)" )                       ; Negative lookbehind
pcreCompile( "(?i)case" )                       ; Case-insensitive flag
pcreCompile( "(?-i)CASE" )                      ; Case-sensitive flag
pcreCompile( "(?:(?i)abc)(?-i)DEF" )           ; Mixed flags

; Test 4.4: Alternation
pcreCompile( "abc|def|ghi" )                   ; Simple alternation
pcreCompile( "\\(abc\\)|\\(def\\)" )           ; Alternation with escaped parens
pcreCompile( "(?:one|two|three)\\s+(?:a|b)" ) ; Complex alternation

; ============================================================================
; PCRE Tests - Anchors and Boundaries
; ============================================================================

; Test 5.1: Anchors
pcreCompile( "^start" )                         ; Start anchor
pcreCompile( "end$" )                           ; End anchor
pcreCompile( "^complete$" )                     ; Both anchors
pcreCompile( "^\\s*(?:abc|def)\\s*$" )         ; Anchors with groups

; Test 5.2: Word boundaries
pcreCompile( "\\bword\\b" )                     ; Word boundary
pcreCompile( "\\B\\w+\\B" )                     ; Non-word boundary

; ============================================================================
; PCRE Tests - Real-World Patterns
; ============================================================================

; Test 6.1: Original problematic pattern
pcreCompile( "cdfCreateParam\\s*\\([^)]*(?:\\([^)]*\\)[^)]*)*\\)" )

; Test 6.2: Email pattern
pcreCompile( "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}" )

; Test 6.3: URL pattern
pcreCompile( "https?://[a-zA-Z0-9.-]+(?:/[^\\s]*)?" )

; Test 6.4: Phone number pattern
pcreCompile( "\\(?\\d{3}\\)?[-.\\s]?\\d{3}[-.\\s]?\\d{4}" )

; Test 6.5: IP address pattern
pcreCompile( "(?:\\d{1,3}\\.){3}\\d{1,3}" )

; Test 6.6: HTML tag pattern
pcreCompile( "<([a-zA-Z][a-zA-Z0-9]*)\\b[^>]*>.*?</\\1>" )

; Test 6.7: Date pattern (YYYY-MM-DD)
pcreCompile( "\\d{4}-\\d{2}-\\d{2}" )

; Test 6.8: Nested parentheses
pcreCompile( "\\((?:[^()]|\\([^()]*\\))*\\)" )

; Test 6.9: Balanced brackets
pcreCompile( "\\[(?:[^\\[\\]]|\\[[^\\[\\]]*\\])*\\]" )

; ============================================================================
; PCRE Tests - All PCRE Match Functions
; ============================================================================

; Test 7.1: pcreMatchAssocList - Basic matching
pcreMatchAssocList( "\\d+" "abc123def" )
pcreMatchAssocList( "\\w+@\\w+\\.\\w+" "user@domain.com" )
pcreMatchAssocList( "(?:abc|def)\\s*\\(\\d+\\)" "abc(123)" )

; Test 7.2: pcreMatchList - Pattern matching with list results
pcreMatchList( "\\w+" "hello world test" )
pcreMatchList( "\\d{2,4}" "Year 2024 has 365 days" )
pcreMatchList( "\\([^)]*\\)" "test(123)and(456)" )

; Test 7.3: pcreMatchp - Boolean pattern matching
pcreMatchp( "^\\d+$" "12345" )
pcreMatchp( "\\s*\\(\\w+\\)" " (hello)" )
pcreMatchp( "[a-zA-Z]+@[a-zA-Z]+\\.com" "user@example.com" )

; ============================================================================
; REX Tests - Basic Patterns
; ============================================================================

; Test 8.1: Basic rex patterns
rexCompile( "abc" )                             ; Literal string
rexCompile( "a.c" )                             ; Any character
rexCompile( "a*b+c" )                           ; Basic quantifiers

; Test 8.2: Rex escaped groups (REX uses \( \) for grouping, NOT unescaped ())
rexCompile( "\\(abc\\)" )                       ; Escaped parentheses (rex syntax)
rexCompile( "\\([a-z]+\\) +\\([0-9]+\\)" )     ; Multiple groups (REX: space, not \s)
rexCompile( "\\(\\(nested\\)\\)" )             ; Nested escaped groups

; Test 8.3: Rex character sets (same as PCRE)
rexCompile( "[abc]" )                           ; Character set
rexCompile( "[^abc]" )                          ; Negated character set
rexCompile( "[a-zA-Z0-9]" )                    ; Range in character set

; Test 8.4: Rex word boundaries (REX uses \< \>, NOT \b)
rexCompile( "\\<word\\>" )                      ; Word boundaries (rex syntax)
rexCompile( "\\<[a-z]+\\>" )                    ; Word boundary with pattern (not \w+)

; Test 8.5: Rex backreferences (\n references group n)
rexCompile( "\\([a-z]+\\) +\\1" )              ; Backreference \1 (not \w+, not \s+)

; ============================================================================
; REX Tests - All REX Match Functions
; ============================================================================

; Test 9.1: rexMatchp - Boolean pattern matching
rexMatchp( "abc" "test abc test" )
rexMatchp( "\\([0-9]+\\)" "value(123)" )        ; REX: use [0-9]+, not \d+
rexMatchp( "\\<word\\>" "word boundary" )

; Test 9.2: rexMatchAssocList - Pattern matching with association list
rexMatchAssocList( "\\([a-z]+\\)" "test(hello)world" )  ; REX: use [a-z]+, not \w+
rexMatchAssocList( "\\<[a-z]+\\>" "word boundary test" )
rexMatchAssocList( "[0-9]+" "value123test" )

; Test 9.3: rexMatchList - Pattern matching with list results
rexMatchList( "[a-z]+" "hello world test" )     ; REX: use [a-z]+, not \w+
rexMatchList( "\\([0-9]+\\)" "value(123)and(456)" )     ; REX: use [0-9]+, not \d+
rexMatchList( "\\<[a-z]+\\>" "word boundaries here" )   ; REX: use [a-z]+, not \w+

; ============================================================================
; Edge Cases and Mixed Tests
; ============================================================================

; Test 10.1: Empty and minimal patterns
pcreCompile( "" )                               ; Empty pattern
pcreCompile( "." )                              ; Single dot
pcreCompile( "\\s" )                            ; Single escape

; Test 10.2: Very long patterns
pcreCompile( "(?:(?:(?:(?:a|b)|(?:c|d))|(?:(?:e|f)|(?:g|h)))|(?:(?:(?:i|j)|(?:k|l))|(?:(?:m|n)|(?:o|p))))" )

; Test 10.3: Multiple escape levels
pcreCompile( "\\\\\\s*\\\\\\d+" )              ; Double escapes

; Test 10.4: Octal escape sequences
pcreCompile( "\\101\\102\\103" )               ; Octal: ABC (101=A, 102=B, 103=C)
pcreCompile( "[\\000-\\177]" )                 ; Octal range: ASCII (0-127)
pcreCompile( "[\\000-\\377]" )                 ; Octal range: Full byte (0-255)

; ============================================================================
; Test 11: Multiple String Parameters - First Parameter Only Highlighting
; ============================================================================

; Test 11.1: PCRE functions with multiple string parameters
; The first string should have PCRE syntax highlighting
; The second and subsequent strings should have plain string highlighting
pcreCompile( "\\d+" "this should be plain string" )
pcreMatchList( "\\w+" "test string 123" )
pcreMatchAssocList( "\\s*\\([^)]*\\)" "value(123)" "another plain string" )
pcreMatchp( "^[a-z]+$" "teststring" )

; Test 11.2: REX functions with multiple string parameters
; The first string should have REX syntax highlighting
; The second and subsequent strings should have plain string highlighting
rexCompile( "\\([0-9]+\\)" "plain string" )
rexMatchList( "\\<[a-z]+\\>" "word boundary test" )
rexMatchAssocList( "[a-z]+" "test" "more plain text" )
rexMatchp( "\\<word\\>" "word boundary" )

; Test 11.3: Complex patterns with multiple parameters
pcreCompile( "(?:abc|def)\\s*\\(\\d+\\)" "description string" "metadata" )
rexCompile( "\\([a-z]+\\)[ ]+\\1" "test backreference" )

; Test 11.4: First parameter empty or minimal
pcreCompile( "" "non-empty second parameter" )
pcreCompile( "." "single dot pattern, plain string here" )
rexCompile( "[a-z]" "simple pattern, plain string" )

; ============================================================================
; Test 12: Nested Bracket Color Cycling (4 Levels)
; ============================================================================
; This test verifies that nested groups use different colors for each level
; Level 1 -> Level 2 -> Level 3 -> Level 4 -> Level 1 (循環)

; Test 12.1: Simple nested groups (2 levels)
pcreCompile( "(a(b)c)" )                                    ; Level 1 -> Level 2
pcreCompile( "(?:a(?:b)c)" )                               ; Non-capturing nested

; Test 12.2: Triple nested groups (3 levels)
pcreCompile( "(a(b(c)d)e)" )                               ; Level 1 -> 2 -> 3
pcreCompile( "(?:a(?:b(?:c)d)e)" )                         ; Non-capturing 3 levels

; Test 12.3: Quadruple nested groups (4 levels)
pcreCompile( "(a(b(c(d)e)f)g)" )                           ; Level 1 -> 2 -> 3 -> 4
pcreCompile( "(?:a(?:b(?:c(?:d)e)f)g)" )                   ; Non-capturing 4 levels

; Test 12.4: Five levels - tests color cycling (Level 4 -> Level 1)
pcreCompile( "(a(b(c(d(e)f)g)h)i)" )                       ; Levels: 1->2->3->4->1
pcreCompile( "(?:a(?:b(?:c(?:d(?:e)f)g)h)i)" )             ; Cycling colors

; Test 12.5: Deep nesting with lookahead/lookbehind
pcreCompile( "(?=a(?!b(?<=c(?<!d(e)))))" )                 ; Mixed special groups
pcreCompile( "((?:abc)(?=def)(?!ghi))" )                   ; Mixed group types

; Test 12.6: Complex nested pattern with multiple types
pcreCompile( "(outer(?:inner(?=lookahead(?<!lookbehind(capture))))))" )

; Test 12.7: Very deep nesting (8 levels - 2 complete cycles)
pcreCompile( "(1(2(3(4(5(6(7(8)7)6)5)4)3)2)1)" )           ; 8 nested levels
pcreCompile( "(?:a(?:b(?:c(?:d(?:e(?:f(?:g(?:h)g)f)e)d)c)b)a)" )

; Test 12.8: Mixed capturing and non-capturing groups
pcreCompile( "(a(?:b(c(?:d(e)d)c)b)a)" )                   ; Level 1 capture, Level 2 non-capture, etc.

; Test 12.9: Nested groups with character sets and quantifiers
pcreCompile( "([a-z]+(?:[0-9]+(?:[A-Z]+(?:[a-z0-9]+)*)*)*)" )

; Test 12.10: Real-world nested pattern example
pcreCompile( "\\((?:[^()]|\\((?:[^()]|\\([^()]*\\))*\\))*\\)" )  ; Balanced parentheses with 3-level nesting

; ============================================================================
; End of Test Suite
; ============================================================================
