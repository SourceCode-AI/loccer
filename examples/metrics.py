import sys
import pprint
import time
import logging

import loccer
from loccer.outputs.file_stream import JSONFileOutput


logger = logging.Logger(__name__)
logger.setLevel(logging.DEBUG)

loccer.install(
    enable_logging=logger,
    output_handlers=(JSONFileOutput(
        filename="metrics_logs.json",
    ),),
)


@loccer.span("decompose")
def factorize(value: int) -> list[int]:
    loccer.span.set("value", value)
    factors = []
    for x in range(2, value):
        if value % x == 0:
            rem = value // x
            logger.info("Found a factor of %d / %d = %d ", value, x, rem)
            loccer.span.set("divisor", x)
            time.sleep(0.3)  # Add artificial delay
            factors.append(x)
            factors.extend(factorize(rem))
            break

    if not factors and value > 1:
        logger.debug("No factors for %d found", value)
        factors.append(value)
    return factors


if __name__ == "__main__":
    with loccer.trace("metrics_demo") as tr:
        if len(sys.argv) == 1:
            numbers = [7919*3*7*7907*7901*42]
        else:
            numbers = [int(x) for x in sys.argv[1:]]

        for x in numbers:
            factors = factorize(x)
            print(f"Factors for `{x}` are: {factors}")

    pprint.pprint(tr.snapshot())
