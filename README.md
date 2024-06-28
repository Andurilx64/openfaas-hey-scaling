# OpenFaas - Watch Tower Autoscaler based on latency

This project is about the implementation of a fine-grained watch tower for a function deployed with OpenFaas Community Edition (v. 0.27.8) over a Kubernetes cluster. The watch-tower aims to continously monitor the function response time,
using [hey](https://github.com/rakyll/hey) (an HTTP load generator) to invoke the function, fetch the latency and based on the latter decide to scale up or down the function (or neither).  
 

This software is meant to run on a Kubernetes master node: the function is scaled directly using Kubernetes' `kubetcl scale`.  
To avoid conflicts between this autoscaler and the Openfaas autoscaler, remove the auto-generated alert for the function in Prometheus, or scale to zero replicas the Alert Manager with this command:

```bash
kubectl scale deployment alertmanager --replicas=0 -n openfaas
```

**Note**: scale out the alert manager stop the alarming service for all the Openfaas functions, not just the one monitored by the watch tower, be careful.  

To avoid that every invocation of the funtion for monitoring purpose is too much expensive, use this pattern:

1. In your target function fetch the http headers
2. If the header 'Hey' is present, the function returns immediately

The strucure of the hey monitoring request is just like this:
```bash
hey -n 1 -c 1 -H "Hey: hey" http://localhost:8080/function/<function-name>
```

This may not reflect the real latency for the end-users, but could save a lot resources and not slow down too the user traffic, expecially if the monitoring is very fine-grained;
if the function is over-invoked the latency of these hey calls will also increase, due to queuing, causing the watch tower to scale up the function. 

## Installation and Usage

The software is managed by **poetry**, and all the dependecies are installed in a python virtual environment. To use the software, run this command from the main directory (where Makefile is located):

```bash
make run
```

## Configuration

This software is meant to be highly configurable. To change the configuration, edit `openfaas_watchtower/openfaas_watchtower/const.py`. Every parameter is listed below.

1. **CHECK_FREQUENCY**: how many seconds between each hey request for monitoring;
2. **URL**: where to find the fucntion;
3. **NAME**: name of the function;
4. **LOG_LEVEL**: logging level;
5. **TARGET**: latency target for the monitoring calls, in milliseconds;
6. **TOLERANCE**: percentage of tolerance for the target value;
7. **SCALE_UP_ROUNDS**: how many consecutive rounds wait for upscaling the function, i.e. number of consecutive hey requests with latency > target;
8. **SCALE_DOWN_ROUNDS**: how many consecutive rounds wait for downscaling the function, i.e. number of consecutive hey requests with latency < target;
9. **SCALE_UP_INCREMENT**: percentage increase of the number of replicas when scale up;
10. **SCALE_DOWN_INCREMENT**: percentage decrease of the number of replicas when scale down.

An example of a full configuration:
```python
"""Definitions of the constants used by the watch tower"""

# Frequency of the checks with hey
CHECK_FREQUENCY = 5

# Endpoint url of the openfaas function
URL = "http://localhost:8080/function/ftest"

# Percentange of tolerance (%)
TOLERANCE = 0.2

# Target latency (ms)
TARGET = 100

# Stabilization window scale up (rounds)
SCALE_UP_ROUNDS = 2

# Stabilization window scale down (rounds)
SCALE_DOWN_ROUNDS = 12

# Scale up replicas increment (%)
SCALE_UP_INCREMENT = 0.2

# Scale down replicas increment (%)
SCALE_DOWN_INCREMENT = 1.0

# Function name
NAME = "ftest"

# Logger level ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LOG_LEVEL = "DEBUG"
```

## Testing

The software is tested with a simple custum function that returns the factiorial of a given number (named _ftest_), using the `python3-http-debian` template, from Openfaas template store.

To simulate some sort of load, hey is used again:

```bash
hey -z 2m -c 50 -q 5  http://localhost:8080/function/ftest?number=50
```

The output summary of the hey call is pasted below.  

```text
Summary:  
  Total:	120.1224 secs  
  Slowest:	1.8184 secs  
  Fastest:	0.0122 secs  
  Average:	0.1106 secs  
  Requests/sec:	244.4173  
  
  Total data:	2231360 bytes  
  Size/request:	76 bytes  

Response time histogram:  
  0.012 [1]	|  
  0.193 [26647]	|■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■  
  0.373 [2413]	|■■■■  
  0.554 [199]	|  
  0.735 [56]	|  
  0.915 [6]	|  
  1.096 [9]	|  
  1.277 [13]	|  
  1.457 [13]	|  
  1.638 [2]	|  
  1.818 [1]	|  


Latency distribution:  
  10% in 0.0491 secs  
  25% in 0.0671 secs  
  50% in 0.0941 secs  
  75% in 0.1261 secs  
  90% in 0.1866 secs  
  95% in 0.2390 secs  
  99% in 0.3781 secs  
  
Details (average, fastest, slowest):  
  DNS+dialup:	0.0000 secs, 0.0122 secs, 1.8184 secs  
  DNS-lookup:	0.0000 secs, -0.0000 secs, 0.0047 secs  
  req write:	0.0000 secs, 0.0000 secs, 0.0159 secs  
  resp wait:	0.1105 secs, 0.0122 secs, 1.8183 secs  
  resp read:	0.0001 secs, -0.0000 secs, 0.0138 secs  
  
Status code distribution:  
  [200]	29360 responsens  
```

The _ftest_ fucntion correctly scales up during the load (up to limit of 5 replicas :smiley:), and scales down after the hey execution.



