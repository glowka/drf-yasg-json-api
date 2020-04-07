import pprint
import json


def print_swagger(swagger):
    pprint.pprint(json.loads(json.dumps(swagger)))
