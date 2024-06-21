"""Watch tower for an openfaas function"""

import subprocess
import re
import json
import logging
from threading import Thread
from time import sleep
from queue import Queue
from collections import deque
from openfaas_watchtower.const import (
    TARGET,
    URL,
    CHECK_FREQUENCY,
    SCALE_UP_ROUNDS,
    SCALE_DOWN_ROUNDS,
    TOLERANCE,
    NAME,
)


queue = Queue()
deq = deque(maxlen=max(SCALE_DOWN_ROUNDS, SCALE_UP_ROUNDS))
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# pylint: disable=logging-fstring-interpolation


def run_hey(url, requests=1, concurrency=1):
    """Runs the hey check for latency of the function"""
    command = ["hey", "-n", str(requests), "-c", str(concurrency), "-t", "3", url]

    try:
        # Execute the command
        results = subprocess.run(command, capture_output=True, text=True, check=True)

        # Fetch stdout and stderr
        stdout = results.stdout
        # stderr = result.stderr

        out = parse_output(stdout)
        if out:
            logger.debug(f"Latency: {out}")
            queue.put_nowait(out)
        return

    except subprocess.CalledProcessError as e:
        # Handle errors
        logger.error(f"Error occurred: {e}")
        # return None


def parse_output(stdout):
    """Parsing of the hey output"""

    patterns = {
        "total": r"Total:\s+([\d.]+) secs",
        "slowest": r"Slowest:\s+([\d.]+) secs",
        "fastest": r"Fastest:\s+([\d.]+) secs",
        "average": r"Average:\s+([\d.]+) secs",
        "requests_per_sec": r"Requests/sec:\s+([\d.]+)",
        "total_data": r"Total data:\s+(\d+) bytes",
        "size_per_request": r"Size/request:\s+(\d+) bytes",
    }

    match = re.search(patterns["average"], stdout)
    if not match:
        return None
    return float(match.group(1))


def get_replicas(deployment_name, namespace="openfaas-fn"):
    """Get current replicas of a deployment"""
    try:

        cmd = ["kubectl", "get", "deployment", deployment_name, "-o", "json"]

        if namespace:
            cmd.extend(["-n", namespace])

        res = subprocess.run(cmd, capture_output=True, text=True, check=True)

        deployment_info = json.loads(res.stdout)

        replicas = deployment_info["spec"]["replicas"]
        return replicas
    except subprocess.CalledProcessError:
        return None


class Pipeline:
    """Define a processing pipeline"""

    def __init__(self):
        self.steps = []
        self.queue = deque(maxlen=5)

    def add_step(self, step):
        """Adds a step to the pipeline"""
        self.steps.append(step)

    def run(self, input_data):
        """Runs the pipeline"""
        data = (input_data, self.queue)
        for step in self.steps:
            data = step(data)
            if not data:
                return None
        return data


def step1(data):
    """Hey check"""
    # Run the hey test
    url = data[0]
    return run_hey(url), data[1]


def step2(data):
    """Parsing"""
    stdout = data[0]
    if stdout is None:
        return None
    return parse_output(stdout), data[1]


def step3(data):
    """Verify that latency is under the target"""
    latency = data[0]
    if latency > TARGET:
        pass
    replicas = get_replicas("ftest")
    print(f"Current replicas {replicas}")
    return latency, data[1]


def create_pipeline():
    """Create and returns the pipeline"""
    pipeline = Pipeline()
    pipeline.add_step(step1)
    pipeline.add_step(step2)
    pipeline.add_step(step3)
    return pipeline


def run_hey_continuos():
    """Run hey check every tot"""
    while True:
        run_hey(URL)
        sleep(CHECK_FREQUENCY)


def run_hey_thread():
    "Starts hey requests"
    thread = Thread(target=run_hey_continuos)
    thread.start()


def fetch_latency(counters):
    """Reads latency in the queue"""
    latency = queue.get()
    data = {"latency": latency, "counter_up": counters[0], "counter_down": counters[1]}
    return check_latency(data)


def run_fetch_latency_continuos():
    """Continuos monitoring the queue"""
    counters = (0, 0)
    while True:
        counters = fetch_latency(counters)


def run_fetch_thread():
    "Starts monitoring for hey responses"
    thread = Thread(target=run_fetch_latency_continuos)
    thread.start()


def check_latency(data: dict):
    """Check latency under the target"""

    target_down = (TARGET - (TARGET * TOLERANCE)) / 1000
    target_up = (TARGET + (TARGET * TOLERANCE)) / 1000
    counter_up = 0
    counter_down = 0
    msg = "Nothing to do"
    if data["latency"] < target_down:
        counter_down = data["counter_down"] + 1
        if counter_down >= SCALE_DOWN_ROUNDS:
            scaled = try_scale_down()
            if scaled:
                msg = "Scaled down"
                counter_up = 0
                counter_down = 0
            else:
                msg = "Fail to scale down"
    elif data["latency"] > target_up:
        counter_up = data["counter_up"] + 1
        if counter_up >= SCALE_UP_ROUNDS:
            scaled = try_scale_up()
            if scaled:
                msg = "Scaled up"
                counter_up = 0
                counter_down = 0
            else:
                msg = "Fail to scale up"
    else:
        msg = "Nothing to do"
    logger.debug(msg)
    return (counter_up, counter_down)


def try_scale_down():
    """Tries to scale down replicas with kubectl"""

    replicas = get_replicas(NAME)
    if replicas == 1:
        # can't zero scaling in openfaas free!
        return True

    req_replicas = replicas - 1
    req_replicas_str = "--replicas=" + str(req_replicas)
    deployment = "deployment/" + NAME
    cmd = ["kubectl", "scale", req_replicas_str, deployment, "-n", "openfaas-fn"]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        sleep(1)
        replicas = get_replicas(NAME)
        assert req_replicas == replicas
    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred: {e}")
        return False
    except AssertionError:
        logger.error("Something went wrong")
        return False
    return True


def try_scale_up():
    """Tries to scale up replicas with kubectl"""

    replicas = get_replicas(NAME)
    if replicas == 1:
        # can't zero scaling in openfaas free!
        return True

    req_replicas = replicas + 1
    req_replicas_str = "--replicas=" + str(req_replicas)
    deployment = "deployment/" + NAME
    cmd = ["kubectl", "scale", req_replicas_str, deployment, "-n", "openfaas-fn"]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        sleep(1)
        replicas = get_replicas(NAME)
        assert req_replicas == replicas
    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred: {e}")
        return False
    except AssertionError:
        logger.error("Something went wrong")
        return False
    return True
