def quick_format(obj):
    if obj is None:
        return obj
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    else:
        return repr(obj)
