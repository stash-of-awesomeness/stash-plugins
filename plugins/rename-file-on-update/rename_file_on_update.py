from stashapi.stashapp import StashInterface
import json
import sys

from config_parser import Config
from renamer import rename_scene, rename_all_scenes

STASH_DATA = json.loads(sys.stdin.read())

ARGS = STASH_DATA["args"]
ACTION = ARGS.get("action")

stash = StashInterface(STASH_DATA["server_connection"])
stash_config = stash.get_configuration()

config = Config(stash_config["plugins"].get("rename-file-on-update", {}))

if "hookContext" in ARGS:
    hook_data = ARGS["hookContext"]
    hook_type = hook_data.get("type")

    if hook_type == "Scene.Update.Post":
        rename_scene(stash, config, ARGS)
elif ACTION == "rename-all":
    rename_all_scenes(stash, config)
