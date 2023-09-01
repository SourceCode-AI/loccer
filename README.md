^Loccer$ - Local error logging
==============================

Loccer is a **zero-dependency** library for creating error logs on a local system. It is designed to be used in air-gaped networks and highly secure environments where alternatives like Sentry are not viable. Logs are stored by default as a json formatted object per line.


Usage
-----

```python
import loccer

# This will capture/log any unhandled exceptions by hooking into sys.excepthook
loccer.install()


# You can also use loccer manually at certain places
capture_exception = loccer.Loccer()
# You can also use `loccer.capture_exception` to use the default loccer instance created previously by loccer.install()

try:
    1 / 0
except:
    # Call it as a function to capture current exception
    capture_exception()

with capture_exception:
    # Use it as a context manager
    1 / 0


# Use it as a decorator
@capture_exception
def func():
    1 / 0

func()
```

Loccer is capable also of collecting additional data through integrations, the current list of built-in integration supported are as follows:

- `platform` integration:

   - Gathers information about Python version, operating system version, hostname, environment variables and so forth

- `flask` integration:

   - Obtains details from HTTP request for example URL, parameters, method, HTTP headers, cookies form data and miscellaneous flask related properties

- `quart` integration:

   - Identical to flask integration but for Quart framework.

- `asyncio` integration:

   - Gathers information on unhandled exception from asyncio context. That includes the asyncio loop and active coroutines at moment of error


Loccer can be also extended with integrations that provide new output formats or forward data to external systems. The current built-in output formats are:

- `NullOutput` - behaves like `/dev/null` in Linux
- `InMemoryOutput` - retains log messages inside memory. No disk activity required. Logs can be retrieved programmatically.
- `StderrOutput` - prints JSON formatted logs to stderr
- `JSONStreamOuput` - write logs into the [TextIO](https://docs.python.org/3.12/library/typing.html#typing.TextIO) type stream
- `JSONFileOutput` - emits JSON logs into a file. Supports rotation when reaching max size, with optional GZIP compression of configurable number of backups.


Full example
------------

Full example of using Loccer in a Quart application with additional integrations and output formats:

```python
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
async def index_error():
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


```



Output example
--------------

The `JSONFileOutput` emits one JSON object per line, the example output below has been reformatted to multiple lines with some information stripped for better readability. The captured exception is from the full example demo application listed above.

```json
{
  "loccer_type": "exception",
  "timestamp": "2023-09-01T13:15:47.517464",
  "exc_type": "RuntimeError",
  "msg": "test exception",
  "integrations": {
    "platform": {
      "username": "redacted_username",
      "hostname": "redacted.local",
      "uname": {
        "system": "Darwin",
        "node": "redacted.local",
        "release": "22.6.0",
        "version": "Darwin Kernel Version [REDACTED]",
        "machine": "arm64",
        "processor": "arm"
      },
      "python": {
        "compiler": "Clang 14.0.3 (clang-1403.0.22.14.1)",
        "branch": "",
        "implementation": "CPython",
        "revision": "",
        "version": "3.11.4"
      },
      "environment_variables": {
        "PATH": "/usr/local/bin:[REDACTED]",
        "__CFBundleIdentifier": "com.jetbrains.pycharm",
        "SHELL": "/bin/zsh",
        "TERM": "xterm-256color",
        "COMMAND_MODE": "unix2003",
        "TERMINAL_EMULATOR": "JetBrains-JediTerm",
        "LC_CTYPE": "UTF-8",
        "...": "output stripped for readability"
      }
    },
    "asyncio": {
      "coros": {
        "Task-2": {
          "coro": "<coroutine object observe_changes at 0x102a55000>",
          "is_done": false
        },
        "Task-11": {
          "coro": "<coroutine object ASGIHTTPConnection.handle_messages at 0x102c64c40>",
          "is_done": false
        },
        "Task-3": {
          "coro": "<coroutine object Lifespan.handle_lifespan at 0x102b57010>",
          "is_done": false
        },
        "Task-7": {
          "coro": "<coroutine object worker_serve.<locals>._server_callback at 0x102b3d900>",
          "is_done": false
        },
        "Task-5": {
          "coro": "<coroutine object raise_shutdown at 0x102b58f40>",
          "is_done": false
        },
        "Task-10": {
          "coro": "<coroutine object _handle at 0x102b3dc60>",
          "is_done": false
        },
        "Task-12": {
          "coro": "<coroutine object ASGIHTTPConnection.handle_request at 0x102c64f40>",
          "is_done": false
        },
        "Task-1": {
          "coro": "<coroutine object serve at 0x102b07840>",
          "is_done": false
        }
      },
      "global_context": {
        "<ContextVar name='quart.app_ctx' at 0x10206f0b0>": "<quart.ctx.AppContext object at 0x1025bc950>",
        "<ContextVar name='quart.request_ctx' at 0x10206f100>": "<quart.ctx.RequestContext object at 0x1025bc150>"
      }
    },
    "quart": {
      "quart_context": true,
      "endpoint": "index_error",
      "client_ip": "127.0.0.1",
      "url": "/",
      "method": "GET",
      "headers": {
        "Remote-Addr": "127.0.0.1",
        "Host": "localhost:8080",
        "Sec-Fetch-Site": "none",
        "Cookie": "[READCTED]",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Mode": "navigate",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": "Mozilla/5.0 [REDACTED]",
        "Accept-Language": "sk-SK,sk;q=0.9",
        "Sec-Fetch-Dest": "document",
        "Accept-Encoding": "gzip, deflate"
      },
      "user_agent": "Mozilla/5.0 [REDACTED]",
      "is_json": false,
      "content_length": null,
      "content_type": null,
      "files": {
      },
      "cookies": {
        "csrftoken": "[REDACTED]",
      }
    }
  },
  "frames": [
    {
      "filename": "[REDACTED]/Loccer/venv/lib/python3.11/site-packages/quart/app.py",
      "lineno": 1650,
      "name": "handle_request",
      "line": "return await self.full_dispatch_request(request_context)",
      "locals": {
        "self": "<Quart 'quart_app'>",
        "request": "<Request 'http://localhost:8080/' [GET]>",
        "request_context": "<quart.ctx.RequestContext object at 0x102cb3f50>",
        "error": "RuntimeError('test exception')"
      }
    },
    {
      "filename": "[REDACTED]/Loccer/venv/lib/python3.11/site-packages/quart/app.py",
      "lineno": 1675,
      "name": "full_dispatch_request",
      "line": "result = await self.handle_user_exception(error)",
      "locals": {
        "self": "<Quart 'quart_app'>",
        "request_context": "<quart.ctx.RequestContext object at 0x102cb3f50>",
        "result": "None"
      }
    },
    {
      "filename": "[REDACTED]/Loccer/venv/lib/python3.11/site-packages/quart/app.py",
      "lineno": 1107,
      "name": "handle_user_exception",
      "line": "raise error",
      "locals": {
        "self": "<Quart 'quart_app'>",
        "error": "RuntimeError('test exception')",
        "handler": "None"
      }
    },
    {
      "filename": "[REDACTED]/Loccer/venv/lib/python3.11/site-packages/quart/app.py",
      "lineno": 1673,
      "name": "full_dispatch_request",
      "line": "result = await self.dispatch_request(request_context)",
      "locals": {
        "self": "<Quart 'quart_app'>",
        "request_context": "<quart.ctx.RequestContext object at 0x102cb3f50>",
        "result": "None"
      }
    },
    {
      "filename": "[REDACTED]/Loccer/venv/lib/python3.11/site-packages/quart/app.py",
      "lineno": 1718,
      "name": "dispatch_request",
      "line": "return await self.ensure_async(handler)(**request_.view_args)",
      "locals": {
        "self": "<Quart 'quart_app'>",
        "request_context": "<quart.ctx.RequestContext object at 0x102cb3f50>",
        "request_": "<Request 'http://localhost:8080/' [GET]>",
        "handler": "<function index_error at 0x102b73f60>"
      }
    },
    {
      "filename": "[REDACTED]/Loccer/venv/lib/python3.11/site-packages/quart/utils.py",
      "lineno": 61,
      "name": "_wrapper",
      "line": "result = await loop.run_in_executor(",
      "locals": {
        "args": "()",
        "kwargs": "{}",
        "loop": "<_UnixSelectorEventLoop running=True closed=False debug=True>",
        "func": "<function index_error at 0x102b73f60>"
      }
    },
    {
      "filename": "/opt/homebrew/Cellar/python@3.11/3.11.4_1/Frameworks/Python.framework/Versions/3.11/lib/python3.11/concurrent/futures/thread.py",
      "lineno": 58,
      "name": "run",
      "line": "result = self.fn(*self.args, **self.kwargs)",
      "locals": {
        "self": "None"
      }
    },
    {
      "filename": "[REDACTED]/Loccer/examples/quart_app.py",
      "lineno": 21,
      "name": "index_error",
      "line": "raise RuntimeError(\"test exception\")",
      "locals": null
    }
  ],
  "globals": {
    "__name__": "'quart.app'",
    "__doc__": "None",
    "__package__": "'quart'",
    "__loader__": "<_frozen_importlib_external.SourceFileLoader object at 0x10197dad0>",
    "__file__": "'[REDACTED]/Loccer/venv/lib/python3.11/site-packages/quart/app.py'",
    "__cached__": "'[REDACTED]/Loccer/venv/lib/python3.11/site-packages/quart/__pycache__/app.cpython-311.pyc'",
    "OrderedDict": "<class 'collections.OrderedDict'>",
    "timedelta": "<class 'datetime.timedelta'>",
    "_cv_websocket": "<ContextVar name='quart.websocket_ctx' at 0x102786d40>",
    "g": "<quart.g of 'quart_app'>",
    "request": "<Request 'http://localhost:8080/' [GET]>",
    "request_ctx": "<quart.ctx.RequestContext object at 0x102cb3f50>",
    "session": "{}",
    "websocket": "<LocalProxy unbound>",
    "websocket_ctx": "<LocalProxy unbound>",
    "_split_blueprint_path": "<functools._lru_cache_wrapper object at 0x102831170>",
    "find_package": "<function find_package at 0x102966e80>",
    "get_debug_flag": "<function get_debug_flag at 0x1029667a0>",
    "get_env": "<function get_env at 0x1029668e0>",
    "get_flashed_messages": "<function get_flashed_messages at 0x102966b60>",
    "DefaultJSONProvider": "<class 'quart.json.provider.DefaultJSONProvider'>",
    "JSONProvider": "<class 'quart.json.provider.JSONProvider'>",
    "create_logger": "<function create_logger at 0x102a71260>",
    "QuartMap": "<class 'quart.routing.QuartMap'>",
    "_convert_timedelta": "<function _convert_timedelta at 0x10196e7a0>",
    "Quart": "<class 'quart.app.Quart'>",
    "_cancel_all_tasks": "<function _cancel_all_tasks at 0x102a71800>",
    "_windows_signal_support": "<function _windows_signal_support at 0x102aa6660>",
    "...": "output stripped for readability"
  }
}
```

