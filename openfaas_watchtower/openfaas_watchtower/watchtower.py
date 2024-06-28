"""Watch tower for an openfaas function"""

import subprocess
import re
import json
import logging
from math import ceil
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
    LOG_LEVEL,
    SCALE_DOWN_INCREMENT,
    SCALE_UP_INCREMENT,
)


LOG_MAPPING = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

queue = Queue()
deq = deque(maxlen=max(SCALE_DOWN_ROUNDS, SCALE_UP_ROUNDS))
logging.basicConfig(
    level=LOG_MAPPING[LOG_LEVEL], format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# pylint: disable=logging-fstring-interpolation


def run_hey(url, requests=3, concurrency=3):
    """Runs the hey check for latency of the function"""
    command = [
        "hey",
        "-n",
        str(requests),
        "-c",
        str(concurrency),
        "-H",
        "Hey: hey",
        "-t",
        "3",
        url,
    ]

    try:
        # Execute the command
        results = subprocess.run(command, capture_output=True, text=True, check=True)

        # Fetch stdout and stderr
        stdout = results.stdout
        # stderr = result.stderr

        out = parse_output(stdout, requests)
        if out:
            logger.debug(f"Latency: {out}")
            queue.put_nowait(out)
        return

    except subprocess.CalledProcessError as e:
        # Handle errors
        logger.error(f"Error occurred: {e}")
        # return None


def parse_output(stdout, requests=3):
    """Parsing of the hey output"""

    patterns = {
        "total": r"Total:\s+([\d.]+) secs",
        "slowest": r"Slowest:\s+([\d.]+) secs",
        "fastest": r"Fastest:\s+([\d.]+) secs",
        "average": r"Average:\s+([\d.]+) secs",
        "requests_per_sec": r"Requests/sec:\s+([\d.]+)",
        "total_data": r"Total data:\s+(\d+) bytes",
        "size_per_request": r"Size/request:\s+(\d+) bytes",
        "status code": r"\[200\]\s+(\d+)\s+responses",
        "responses": r"(\d+)",
    }

    match = re.search(patterns["average"], stdout)
    code = re.search(patterns["status code"], stdout)
    num = re.search(patterns["responses"], str(code.group(1)))
    if not match:
        return None
    if not num or int(num.group(1)) != requests:
        logger.warning("Some response not 200 ok")
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
    msg += ": " + str(get_replicas(NAME)) + " replicas"
    logger.info(msg)
    return (counter_up, counter_down)


def try_scale_down():
    """Tries to scale down replicas with kubectl"""

    replicas = get_replicas(NAME)
    if replicas == 1:
        # can't zero scaling in openfaas community-edition!
        return False

    req_replicas = scale_down_repl_calc(replicas)
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
    if replicas == 5:
        # can't scale over 5 in openfaas community-edition!
        return False

    req_replicas = scale_up_repl_calc(replicas)
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


def scale_down_repl_calc(current_repl: int):
    """Calculates the number of replicas required"""

    next_repl = ceil(current_repl - (current_repl * SCALE_DOWN_INCREMENT))
    if next_repl < 1:
        return 1
    return next_repl


def scale_up_repl_calc(current_repl: int):
    """Calculates the number of replicas required"""

    next_repl = ceil(current_repl + (current_repl * SCALE_UP_INCREMENT))
    if next_repl > 5:
        return 5
    return next_repl
