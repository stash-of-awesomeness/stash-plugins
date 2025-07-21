from operator import itemgetter
from stashapi.stashapp import StashInterface
from stashapi import log
import pathlib
import re


MOVE_FILE_MUTATION = """
mutation MoveFiles($input: MoveFilesInput!) {
    moveFiles(input: $input)
}
"""


def get_parent_studio_chain(stash, scene):
    current_studio = scene.get("studio", {})
    parent_chain = [current_studio.get("name", "")]

    while current_studio.get("parent_studio"):
        current_studio = stash.find_studio(current_studio.get("parent_studio"))

        parent_chain.append(current_studio.get("name"))

    return "/".join(reversed(parent_chain))

def key_getter(key):
    return lambda _, data: data.get(key, "")

FILE_VARIABLES = {
    "audio_codec": key_getter("audio_codec"),
    "ext": lambda _, file: file.get("basename", "").split(".")[-1],
    "format": key_getter("format"),
    "height": key_getter("height"),
    "index": key_getter("index"),
    "video_codec": key_getter("video_codec"),
    "width": key_getter("width"),
}

SCENE_VARIABLES = {
    "scene_id": key_getter("id"),
    "title": key_getter("title"),
    "date": key_getter("date"),
    "director": key_getter("director"),
    "month": lambda _, scene: scene.get("date", "").split("-")[1] if scene.get("date") else "",
    "parent_studio_chain": get_parent_studio_chain,
    "studio_code": key_getter("code"),
    "studio_name": lambda _, scene: scene.get("studio", {}).get("name", ""),
    "year": lambda _, scene: scene.get("date", "").split("-")[0] if scene.get("date") else "",
}

def find_variables(format_template) -> list[str]:
    variables = []

    for variable in FILE_VARIABLES.keys():
        if f"${variable}$" in format_template:
            variables.append(variable)

    for variable in SCENE_VARIABLES.keys():
        if f"${variable}$" in format_template:
            variables.append(variable)

    return variables


def clean_optional_from_format(formatted_string: str) -> str:
    # Erase entire optional section if there is an unused variable
    formatted_string = re.sub(r"\{.*\$\w+\$.*\}", "", formatted_string)

    # Remove any remaining curly braces
    formatted_string = formatted_string.replace(r"{", "").replace(r"}", "")

    return formatted_string


def apply_format(format_template: str, stash: StashInterface, scene_data, file_data)-> str:
    variables = find_variables(format_template)

    formatted_template = format_template

    for variable in variables:
        if variable in FILE_VARIABLES:
            value = FILE_VARIABLES[variable](stash, file_data)
        elif variable in SCENE_VARIABLES:
            value = SCENE_VARIABLES[variable](stash, scene_data)

        if not value:
            continue

        formatted_template = formatted_template.replace(f"${variable}$", str(value))

    formatted_template = clean_optional_from_format(formatted_template)

    return formatted_template


class StashFile:
    def __init__(self, stash: StashInterface, config, scene_data, file_data):
        self.stash = stash
        self.config = config
        self.scene_data = scene_data
        self.file_data = file_data
        self.duplicate_index = 0

    def get_old_file_path(self) -> pathlib.Path:
        path = pathlib.Path(self.file_data["path"])

        return path.absolute()

    def get_new_file_folder(self) -> pathlib.Path:
        if self.config.default_directory_path_format:
            directory_path = apply_format(self.config.default_directory_path_format, self.stash, self.scene_data, self.file_data)
        else:
            path = pathlib.Path(self.file_data["path"])
            directory_path = path.parent.absolute()

        return pathlib.Path(directory_path)
    
    def get_new_file_name(self) -> str:
        if self.config.default_file_name_format:
            file_data = {**self.file_data, "index": self.duplicate_index}
            file_name = apply_format(self.config.default_file_name_format, self.stash, self.scene_data, file_data)

            if self.duplicate_index:
                duplicate_suffix = apply_format(self.config.duplicate_file_suffix, self.stash, self.scene_data, file_data)
                base_name = file_name.rsplit(".", 1)[0]
                extension = file_name.rsplit(".", 1)[1]

                file_name = f"{base_name}{duplicate_suffix}.{extension}"

            if self.config.remove_extra_spaces_from_file_name:
                file_name = re.sub(r"\s+", " ", file_name)
        else:
            file_name = self.file_data["basename"]

        return file_name

    def get_new_file_path(self) -> pathlib.Path:
        return self.get_new_file_folder() / self.get_new_file_name()

    def rename_file(self):
        old_path = self.get_old_file_path()
        new_path = self.get_new_file_path()

        if not old_path.exists():
            log.warning(f"File for scene does not exist on disk: {old_path}")
            return

        if old_path == new_path:
            log.info("File paths are the same, no renaming needed.")
            return

        log.debug(f"Checking if a file exists at {new_path}")
        while new_path.exists():
            self.duplicate_index += 1
            log.warning(f"File already exists at {new_path}, adding duplicate suffix: {self.duplicate_index}")
            new_path = self.get_new_file_path()

            if old_path == new_path:
                log.info("File paths are the same after adding duplicate suffix, no renaming needed.")
                return

        log.info(f"Renaming file from {old_path} to {new_path}")
        if self.config.dry_run:
            log.info("Dry run enabled, not actually renaming the file.")
            return

        moved_file = self.stash.call_GQL(
            MOVE_FILE_MUTATION,
            {"input": {
                    "ids": [self.file_data["id"]],
                    "destination_folder": self.get_new_file_folder(),
                    "destination_basename": self.get_new_file_name(),
                }
            }
        )

        log.info(f"File renamed successfully: {moved_file}")
