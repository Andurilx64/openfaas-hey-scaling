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

This may not reflect the real latency for the end-users, but could save a lot resources and not slow down too much the user traffic, expecially if the monitoring is very fine-grained;
if the function is over-invoked the latency of these hey calls will also increase, due to queuing, causing the watch tower to scale up the function. 

## Installation and Usage

The software is managed by **poetry** (make sure you have it installed on your machine), and all the dependecies are installed in a python virtual environment. To use the software, run this command from the main directory (where Makefile is located):

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
TARGET = 75

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
The code of this function can be found in `openfaas_watchtower/ftest.py`.  

To simulate some sort of load (quite heavt in this case), hey is used again (two distinct terminals run this generator):

```bash
hey -z 2m -c 50 -q 5  http://localhost:8080/function/ftest?number=50
```

The output summary of the hey call is pasted below.  

```text
Summary:  
  Total:	121.7041 secs  
  Slowest:	0.6253 secs  
  Fastest:	0.0103 secs  
  Average:	0.0659 secs  
  Requests/sec:	236.5410   
  
  Total data:	2187888 bytes  
  Size/request:	76 bytes  

Response time histogram:  
  0.010 [1]	|  
  0.072 [19446]	|■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■  
  0.133 [7999]	|■■■■■■■■■■■■■■■■  
  0.195 [1203]	|■■  
  0.256 [92]	|  
  0.318 [10]	|  
  0.379 [22]	|  
  0.441 [7]	|  
  0.502 [1]	|  
  0.564 [6]	|  
  0.625 [1]	|  


Latency distribution:  
  10% in 0.0304 secs  
  25% in 0.0430 secs  
  50% in 0.0593 secs  
  75% in 0.0811 secs  
  90% in 0.1092 secs  
  95% in 0.1312 secs  
  99% in 0.1752 secs  

Details (average, fastest, slowest):  
  DNS+dialup:	0.0000 secs, 0.0103 secs, 0.6253 secs  
  DNS-lookup:	0.0000 secs, 0.0000 secs, 0.0186 secs  
  req write:	0.0000 secs, 0.0000 secs, 0.0270 secs  
  resp wait:	0.0657 secs, 0.0102 secs, 0.6120 secs  
  resp read:	0.0001 secs, -0.0000 secs, 0.0299 secs  
  
Status code distribution:  
  [200]	28788 responses  
```

The _ftest_ fucntion correctly scales up during the load (up to limit of 5 replicas :smiley:), and scales down after the hey execution. The average response time is below our targer latency (75)! 

The same test was replicated, this time with the default Openfaas Cummunity Edition Autoscaler, with the results listed below.

```text
Summary:  
  Total:	120.0989 secs  
  Slowest:	0.5995 secs  
  Fastest:	0.0084 secs  
  Average:	0.0645 secs  
  Requests/sec:	248.1621  
  
  Total data:	2265104 bytes  
  Size/request:	76 bytes  

Response time histogram:  
  0.008 [1]	|  
  0.067 [18113]	|■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■  
  0.127 [10490]	|■■■■■■■■■■■■■■■■■■■■■■■  
  0.186 [995]	|■■  
  0.245 [124]	|  
  0.304 [35]	|  
  0.363 [1]	|  
  0.422 [0]	|  
  0.481 [20]	|  
  0.540 [13]	|  
  0.599 [12]	|  


Latency distribution:  
  10% in 0.0291 secs  
  25% in 0.0419 secs  
  50% in 0.0601 secs  
  75% in 0.0788 secs  
  90% in 0.1027 secs  
  95% in 0.1216 secs  
  99% in 0.1690 secs  

Details (average, fastest, slowest):  
  DNS+dialup:	0.0000 secs, 0.0084 secs, 0.5995 secs  
  DNS-lookup:	0.0000 secs, 0.0000 secs, 0.0245 secs  
  req write:	0.0000 secs, 0.0000 secs, 0.0154 secs  
  resp wait:	0.0643 secs, 0.0083 secs, 0.5793 secs  
  resp read:	0.0001 secs, -0.0000 secs, 0.0326 secs  

Status code distribution:  
  [200]	29804 responses  
```

To simulate an arbitrary long or short lived function one can use the `openfaas_watchtower/sleepy.py` function template. For example, generating a load for a function with execution time of 0.75 seconds can be done with:

```bash
hey -n 300 -c 10 -q 2 http://localhost:8080/function/sleepy?number=0.75
```

The watchtower autoscaler provided in this project can be tuned to adapt also to work with such slow function (like _sleepy_), with an average latency time very similar to the execution time of the fucntion.

```text

Summary:
  Total:	32.5851 secs
  Slowest:	2.3274 secs
  Fastest:	0.7607 secs
  Average:	1.0469 secs
  Requests/sec:	9.2067
  
  Total data:	7800 bytes
  Size/request:	26 bytes

Response time histogram:
  0.761 [1]	|
  0.917 [215]	|■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
  1.074 [0]	|
  1.231 [0]	|
  1.387 [4]	|■
  1.544 [46]	|■■■■■■■■■
  1.701 [6]	|■
  1.857 [0]	|
  2.014 [0]	|
  2.171 [0]	|
  2.327 [28]	|■■■■■


Latency distribution:
  10% in 0.7640 secs
  25% in 0.7669 secs
  50% in 0.7727 secs
  75% in 1.4286 secs
  90% in 1.5959 secs
  95% in 2.2354 secs
  99% in 2.2564 secs

Details (average, fastest, slowest):
  DNS+dialup:	0.0001 secs, 0.7607 secs, 2.3274 secs
  DNS-lookup:	0.0000 secs, 0.0000 secs, 0.0011 secs
  req write:	0.0000 secs, 0.0000 secs, 0.0016 secs
  resp wait:	1.0466 secs, 0.7606 secs, 2.3249 secs
  resp read:	0.0001 secs, 0.0000 secs, 0.0027 secs

Status code distribution:
  [200]	300 responses
```