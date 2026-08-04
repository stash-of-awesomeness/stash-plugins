from stashapi.stashapp import StashInterface
from stashapi import log
from config_parser import Config
from file_manager import StashFile
import api

def rename_scene(stash: StashInterface, config: Config, args):
    log.debug(f"Checking scene with args: {args}")

    scene_id = args["hookContext"]["id"]
    scene = api.get_scene(stash, scene_id)

    log.debug(f"Found scene: {scene}")

    if not config.rename_unorganized and not scene["organized"]:
        log.info("Scene is not marked as organized, ignoring scene.")
        return

    for file in scene["files"]:
        stash_file = StashFile(stash, config, scene, file)
        stash_file.rename_file()

def rename_all_scenes(stash: StashInterface, config: Config):
    log.info("Checking all scenes")
