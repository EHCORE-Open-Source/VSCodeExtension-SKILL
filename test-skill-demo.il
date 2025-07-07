; Demo SKILL file to test enhanced hover and signature help
; This file demonstrates the multi-tool compatibility system

; Test universal procedures with hover and signature help
(printf "Testing universal procedures\n")

; Arithmetic operations
(setq result (plus 1 2 3 4 5))
(printf "Sum: %d\n" result)

; List operations
(setq myList '(a b c d e))
(setq firstElement (car myList))
(setq restElements (cdr myList))
(setq newList (cons 'x myList))

; String operations
(setq greeting (strcat "Hello" " " "World"))
(setq partial (substring greeting 1 5))

; Control flow
(if (> result 10)
    (printf "Result is greater than 10\n")
    (printf "Result is 10 or less\n")
)

; Iteration
(foreach item '(1 2 3 4 5)
    (when (> item 3)
        (printf "Large number: %d\n" item)
    )
)

; List processing
(setq doubled (mapcar 'times '(1 2 3 4) '(2 2 2 2)))
(setq found (member 'c myList))
(setq assocList '((name "John") (age 30) (city "NYC")))
(setq nameEntry (assoc 'name assocList))

; Comparison
(unless (equal firstElement 'a)
    (printf "Unexpected first element\n")
)

; File operations (hover to see compatibility info)
(load "some-file.il")

; Local bindings
(let ((x 10) (y 20))
    (printf "Local sum: %d\n" (plus x y))
)