; Test file for hover and signature help functionality

; Test complete functions from complete-skill-functions.json
result = gdmAddSpecToSpecList(mySpec mySpecList)
status = gdmcancel(mySpec)
data = gdmci(mySpec "description")

; Test universal functions
list1 = append(list1 list2)
value = car(myList)
length = length(myList)

; Test built-in functions
result = abs(-5)
text = buildString(strings)