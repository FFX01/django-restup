import datetime
import decimal
import traceback

try:
    import json
except ImportError:
    import simplejson as json


class ExtraJsonEncoder(json.JSONEncoder):

    def default(self, data):
        if isinstance(data, (datetime.datetime, datetime.date, datetime.time)):
            return data.isoformat()
        elif isinstance(data, decimal.Decimal):
            return str(data)
        else:
            return super(ExtraJsonEncoder, self).default(data)


def format_traceback(exc_info):
    stack = traceback.format_stack()
    stack = stack[:-2]
    stack.extend(traceback.format_tb(exc_info[2]))
    stack.extend(traceback.format_exception_only(exc_info[0], exc_info[1]))
    stack_str = "Traceback (most recent call last):\n"
    stack_str += "".join(stack)
    stack_str = stack_str[:-1]
    return stack_str
