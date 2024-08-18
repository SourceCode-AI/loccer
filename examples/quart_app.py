import asyncio
import logging

import quart

import loccer
from loccer.integrations.quart_context import QuartContextIntegration
from loccer.integrations.asyncio_context import AsyncioContextIntegration
from loccer.outputs.file_stream import JSONFileOutput


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
app = quart.Quart(__name__)

asyncio_ctx = AsyncioContextIntegration()
quart_ctx = QuartContextIntegration()
quart_ctx.init_app(app)


@app.route("/")
async def index_error():
    raise RuntimeError("test exception")


loccer.install(
    output_handlers=(
        JSONFileOutput(
            filename="errors.log",
            max_files=3,
            max_size=(1024**2) * 10,  # 10MB
            compressed=True,
        ),
    ),
    integrations=loccer.DEFAULT_INTEGRATIONS + (
        asyncio_ctx,
        quart_ctx
    ),
)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    # Some integrations may require additional activation outside the `loccer.install` call
    loop.set_exception_handler(asyncio_ctx.loop_exception_handler)
    port = 8080
    debug = True
    logger.info("Starting the application", extra={"port": port, "debug": debug})
    app.run(debug=debug, loop=loop, port=port)
    # now go and open the page at http://localhost:8080/ to generate an error report
