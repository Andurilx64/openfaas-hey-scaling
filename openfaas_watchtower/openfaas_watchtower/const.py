"""Definitions of the constants used by the watch tower"""

# Frequency of the checks with hey
CHECK_FREQUENCY = 5

# Endpoint url of the openfaas function
URL = "http://localhost:8080/function/ftest"

# Percentange of tolerance (%)
TOLERANCE = 0.1

# Target latency (ms)
TARGET = 75

# Stabilization window scale up (rounds)
SCALE_UP_ROUNDS = 1

# Stabilization window scale down (rounds)
SCALE_DOWN_ROUNDS = 6

# Scale up replicas increment (%)
SCALE_UP_INCREMENT = 0.2

# Scale down replicas increment (%)
SCALE_DOWN_INCREMENT = 1.0

# Function name
NAME = "ftest"

# Logger level ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LOG_LEVEL = "DEBUG"
