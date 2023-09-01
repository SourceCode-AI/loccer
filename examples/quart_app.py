import asyncio

import quart

import loccer
from loccer.integrations.platform_context import PlatformIntegration
from loccer.integrations.quart_context import QuartContextIntegration
from loccer.integrations.asyncio_context import AsyncioContextIntegration
from loccer.outputs.file_stream import JSONFileOutput


app = quart.Quart(__name__)

asyncio_ctx = AsyncioContextIntegration()
quart_ctx = QuartContextIntegration()
quart_ctx.init_app(app)


@app.route("/")
def index_error():
    raise RuntimeError("test exception")



loccer.install(
    output_handlers=(JSONFileOutput(
        filename="errors.log",
        max_files=3,
        max_size=(1024**2) * 10,  # 10MB
        compressed=True,
    ),),
    integrations=(
        PlatformIntegration(),
        asyncio_ctx,
        quart_ctx
    )
)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    # Some integrations may require additional activation outside the `loccer.install` call
    loop.set_exception_handler(asyncio_ctx.loop_exception_handler)
    app.run(debug=True, loop=loop, port=8080)

