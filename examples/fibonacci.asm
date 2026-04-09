# Compute Fibonacci(10) using storage slots
# Slot 0 = F(n-2), Slot 1 = F(n-1), Slot 2 = iteration counter
# Result stored in slot 1

# Initialize: F(0) = 0, F(1) = 1, counter = 2
PUSH 0
PUSH 0
SSTORE        ; storage[0] = 0

PUSH 1
PUSH 1
SSTORE        ; storage[1] = 1

PUSH 2
PUSH 2
SSTORE        ; storage[2] = 2 (counter)

# Loop start (pc = 30 after these instructions)
# Load F(n-2) and F(n-1)
PUSH 0
SLOAD         ; F(n-2)
PUSH 1
SLOAD         ; F(n-1)
ADD           ; F(n) = F(n-2) + F(n-1)

# Shift: F(n-2) = old F(n-1)
PUSH 1
SLOAD
PUSH 0
SWAP
SSTORE        ; storage[0] = old F(n-1)

# Store new F(n) as F(n-1)
PUSH 1
SWAP
SSTORE        ; storage[1] = F(n)

# Increment counter
PUSH 2
SLOAD
PUSH 1
ADD
DUP
PUSH 2
SWAP
SSTORE        ; storage[2] = counter + 1

# Check if counter < 10
PUSH 10
LT

# Jump back to loop start if counter < 10
PUSH 30
SWAP
JUMPI

# Done - log result
PUSH 1
SLOAD
LOG
HALT
