"""Code of the function used in dev

Sleeps for the desired time, but return immediately if the Hey header is set.
Uses the python3-http-debian from openfaas template store"""

from time import sleep


def handle(event, context):
    """factorial of a given number"""
    try:
        head = event.headers.get("Hey")
        if head is not None:
            return {"statusCode": 200, "body": ""}
        else:
            base = float(event.query["number"])
            sleep(base)
            # simulate a load
    except Exception as e:
        return {"statusCode": 500, "body": e}
    return {"statusCode": 200, "body": {"value": "Good Morning!"}}
