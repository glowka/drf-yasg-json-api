import json
import pprint


def print_swagger(swagger):
    pprint.pprint(json.loads(json.dumps(swagger)))
