"""Definitions of the constants used by the watch tower"""

# Frequency of the checks with hey
CHECK_FREQUENCY = 10

# Endpoint url of the openfaas function
URL = "http://localhost:8080/fucntion/ftest"

# Percentange of tolerance (%)
TOLERANCE = 0.1

# Target latency (ms)
TARGET = 100

# Stabilization window scale up (rounds)
SCALE_UP_ROUNDS = 3

# Stabilization window scale down (rounds)
SCALE_DOWN_ROUNDS = 3

# Function name
NAME = "ftest"
