from stashapi.stashapp import StashInterface
from stashapi import log
from config_parser import Config
from file_manager import StashFile

SCENE_FRAGMENT = """
id
title
code
date
organized

studio {
    id
    name
    parent_studio {
        id
        name
    }
}

files {
    id
    path
    basename

    format
    width
    height
    duration
    video_codec
    audio_codec
}
"""

def rename_scene(stash: StashInterface, config: Config, args):
    log.debug(f"Checking scene with args: {args}")

    scene_id = args["hookContext"]["id"]
    scene = stash.find_scene(scene_id, fragment=SCENE_FRAGMENT)

    log.debug(f"Found scene: {scene}")

    if not config.rename_unorganized and not scene["organized"]:
        log.info("Scene is not marked as organized, ignoring scene.")
        return

    for file in scene["files"]:
        stash_file = StashFile(stash, config, scene, file)
        stash_file.rename_file()

def rename_all_scenes(stash: StashInterface, config: Config):
    log.info("Checking all scenes")
