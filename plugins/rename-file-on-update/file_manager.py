from operator import itemgetter
from stashapi.stashapp import StashInterface
from stashapi import log


def get_parent_studio_chain(stash, scene):
    current_studio = scene.get("studio", {})
    parent_chain = [current_studio.get("name", "")]

    while current_studio.get("parent_studio"):
        current_studio = stash.find_studio(current_studio.get("parent_studio"))

        parent_chain.append(current_studio.get("name"))

    return "/".join(parent_chain)

def key_getter(key):
    return lambda _, scene: scene.get(key, "")

FILE_VARIABLES = {
    "audio_codec": key_getter("audio_codec"),
    "format": key_getter("format"),
    "height": key_getter("height"),
    "video_codec": key_getter("video_codec"),
    "width": key_getter("width"),
}

SCENE_VARIABLES = {
    "scene_id": key_getter("id"),
    "title": key_getter("title"),
    "date": key_getter("date"),
    "director": key_getter("director"),
    "studio_code": key_getter("code"),
    "studio_name": lambda _, scene: scene.get("studio", {}).get("name", ""),
    "parent_studio_chain": get_parent_studio_chain,
}

def find_variables(format_template) -> list[str]:
    variables = []

    for variable in SCENE_VARIABLES.keys():
        if f"${variable}$" in format_template:
            variables.append(variable)

    return variables

def apply_format(format_template, stash, scene_data, file_data):
    variables = find_variables(format_template)

    for variable in variables:
        if variable in FILE_VARIABLES:
            value = FILE_VARIABLES[variable](stash, file_data)
        elif variable in SCENE_VARIABLES:
            value = SCENE_VARIABLES[variable](stash, scene_data)
        else:
            value = "<unknown>"

        format_template = format_template.replace(f"${variable}$", str(value))

    return format_template


class StashFile:
    def __init__(self, stash: StashInterface, config, scene_data, file_data):
        self.stash = stash
        self.config = config
        self.scene_data = scene_data
        self.file_data = file_data

    def get_old_file_path(self):
        return f'{self.file_data["path"]}{self.file_data["basename"]}'

    def get_new_file_path(self):
        if self.config.default_directory_path_format:
            directory_path = apply_format(self.config.default_directory_path_format, self.stash, self.scene_data, self.file_data)
        else:
            directory_path = self.file_data["path"]

        if self.config.default_file_name_format:
            file_name = apply_format(self.config.default_file_name_format, self.stash, self.scene_data, self.file_data)
        else:
            file_name = self.file_data["basename"]

        return f"{directory_path}/{file_name}"

    def rename_file(self):
        if self.get_old_file_path() == self.get_new_file_path():
            log.info("File paths are the same, no renaming needed.")
            return
