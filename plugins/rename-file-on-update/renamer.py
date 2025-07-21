from stashapi.stashapp import StashInterface
from stashapi import log
from config_parser import Config
from file_manager import StashFile


def rename_scene(stash: StashInterface, config: Config, args):
    log.info(f"Checking scene with args: {args}")

    scene_id = args["hookContext"]["id"]
    scene = stash.get_scene(scene_id)

    if not config.rename_unorganized and not scene["organized"]:
        log.info("Scene is not marked as organized, ignoring scene.")
        return

    for file in scene["files"]:
        stash_file = StashFile(config, scene, file)

        old_path = stash_file.get_old_file_path()
        new_path = stash_file.get_new_file_path()

        log.info(f"Renaming file from {old_path} to {new_path}")

        stash_file.rename_file()

def rename_all_scenes(stash: StashInterface, config: Config):
    log.info("Checking all scenes")
