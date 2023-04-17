^Loccer$ - Local error logging
==============================

Loccer is a **zero-dependency** library for creating error logs on a local system. It is designed to be used in air-gaped networks and highly secure environments where alternatives like Sentry is not viable.


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

