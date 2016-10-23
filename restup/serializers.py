import json
from .utils import ExtraJsonEncoder


class JsonSerializer(object):

    def deserialize(self, body):
        if isinstance(body, bytes):
            return json.loads(body.decode("utf8"))
        return json.loads(body)

    def serialize(self, data):
        return json.dumps(data, cls=ExtraJsonEncoder)
