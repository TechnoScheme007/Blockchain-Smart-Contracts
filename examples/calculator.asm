# Simple calculator: (10 + 20) * 3 = 90
# Result stored in slot 1

PUSH 10
PUSH 20
ADD           ; 30
PUSH 3
MUL           ; 90
DUP           ; duplicate for storage
PUSH 1        ; key = 1
SWAP
SSTORE        ; storage[1] = 90
LOG           ; log the result
HALT
