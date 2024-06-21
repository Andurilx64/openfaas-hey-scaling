"""Code of the function used in dev

Factorial of a given number, but return immediately if the Hey header is set.
Uses the python3-http-debian from openfaas template store"""


def handle(event, context):
    """factorial of a given number"""
    value = 0
    try:
        head = event.headers.get("Hey")
        if head is not None:
            return {"statusCode": 200, "body": ""}
        else:
            base = int(event.query["number"])
            value = 1
            for i in range(1, base + 1):
                value *= i
    except Exception as e:
        return {"statusCode": 500, "body": e}
    return {"statusCode": 200, "body": {"value": value}}
