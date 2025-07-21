from operator import itemgetter
from stashapi import log

SCENE_VARIABLES = {
    "scene_id": itemgetter("id"),
    "title": itemgetter("title"),
    "date": itemgetter("date"),
    "director": itemgetter("director"),
    "studio_code": itemgetter("code"),
}

def find_variables(format_template) -> list[str]:
    variables = []

    for variable in SCENE_VARIABLES.keys():
        if f"${variable}$" in format_template:
            variables.append(variable)

    return variables

def apply_format(format_template, scene_data, file_data):
    variables = find_variables(format_template)

    for variable in variables:
        value = SCENE_VARIABLES[variable](scene_data)
        format_template = format_template.replace(f"${variable}$", str(value))

    return format_template

class StashFile:
    def __init__(self, config, scene_data, file_data):
        self.config = config
        self.scene_data = scene_data
        self.file_data = file_data

    def get_old_file_path(self):
        return f'{self.file_data["path"]}{self.file_data["basename"]}'

    def get_new_file_path(self):
        directory_path = apply_format(self.config["default_directory_path_format"], self.scene_data, self.file_data)
        file_name = apply_format(self.config["default_file_name_format"], self.scene_data, self.file_data)

        return f"{directory_path}/{file_name}"

    def rename_file(self):
        if self.get_old_file_path() == self.get_new_file_path():
            log.info("File paths are the same, no renaming needed.")
            return
