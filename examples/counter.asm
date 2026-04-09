# Counter contract: increments storage slot 0 each time it's called
# Slot 0 holds the counter value

PUSH 0        ; key = 0
SLOAD         ; load current value
PUSH 1        ; increment by 1
ADD
PUSH 0        ; key = 0
SWAP          ; stack: [key, value]
SSTORE        ; storage[0] = value + 1
PUSH 0
SLOAD         ; load to verify
LOG           ; log the new value
HALT
