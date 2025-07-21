import json
import sys

STASH_DATA = json.loads(sys.stdin.read())

ACTION = STASH_DATA["args"].get("action")
