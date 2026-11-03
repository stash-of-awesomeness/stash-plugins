from stashapi.stashapp import StashInterface
from stashapi import log
import pathlib
import re

from path_sanitize import sanitize_directory_path
from whisparr_naming import (
    NamingContext,
    apply_duplicate_suffix,
    apply_naming_pattern,
)


MOVE_FILE_MUTATION = """
mutation MoveFiles($input: MoveFilesInput!) {
    moveFiles(input: $input)
}
"""


def get_parent_studio_chain(stash, scene):
    """Return slash-separated parent studio names from root to immediate parent."""
    current_studio = scene.get("studio") or {}
    parent_chain = [current_studio.get("name", "")]

    while current_studio.get("parent_studio"):
        current_studio = stash.find_studio(current_studio.get("parent_studio"))
        parent_chain.append(current_studio.get("name"))

    return "/".join(reversed(parent_chain))


def get_root_studio_name(stash, scene) -> str:
    """Top-level studio name in the hierarchy, used as a network fallback."""
    current_studio = scene.get("studio") or {}
    if not current_studio:
        return ""

    root_name = current_studio.get("name") or ""
    while current_studio.get("parent_studio"):
        current_studio = stash.find_studio(current_studio.get("parent_studio"))
        root_name = current_studio.get("name") or root_name
    return root_name


class StashFile:
    def __init__(self, stash: StashInterface, config, scene_data, file_data):
        self.stash = stash
        self.config = config
        self.scene_data = scene_data
        self.file_data = file_data
        self.duplicate_index = 0
        self._studio_network = get_root_studio_name(stash, scene_data)

    def _naming_context(self) -> NamingContext:
        return NamingContext(
            scene=self.scene_data,
            file_data={**self.file_data, "index": self.duplicate_index},
            studio_network=self._studio_network,
            duplicate_index=self.duplicate_index,
        )

    def get_old_file_path(self) -> pathlib.Path:
        path = pathlib.Path(self.file_data["path"])
        return path.absolute()

    def get_new_file_folder(self) -> pathlib.Path:
        if self.config.default_directory_path_format:
            directory_path = apply_naming_pattern(
                self.config.default_directory_path_format,
                self._naming_context(),
                for_folder=True,
                replace_illegal=not self.config.allow_unsafe_characters,
            )
            directory_path = pathlib.Path(directory_path).absolute()
        else:
            path = pathlib.Path(self.file_data["path"])
            directory_path = path.parent.absolute()

        return sanitize_directory_path(directory_path, self.config)

    def get_new_file_name(self) -> str:
        if not self.config.default_file_name_format:
            return self.file_data["basename"]

        path = pathlib.Path(self.file_data["basename"])
        stem = path.stem
        extension = path.suffix

        file_name = apply_naming_pattern(
            self.config.default_file_name_format,
            self._naming_context(),
            for_folder=False,
            replace_illegal=not self.config.allow_unsafe_characters,
        )

        if extension and not file_name.endswith(extension):
            file_name = f"{file_name}{extension}"

        if self.duplicate_index:
            duplicate_suffix = apply_duplicate_suffix(
                self.config.duplicate_file_suffix,
                self.duplicate_index,
            )
            if extension:
                base_name = file_name[: -len(extension)]
                file_name = f"{base_name}{duplicate_suffix}{extension}"
            else:
                file_name = f"{file_name}{duplicate_suffix}"

        if not self.config.allow_unsafe_characters:
            file_name = re.sub(r'[<>:"/\\|?*]', "", file_name)

        if self.config.remove_extra_spaces_from_file_name:
            file_name = re.sub(r"\s+", " ", file_name)

        return file_name

    def get_new_file_path(self) -> pathlib.Path:
        return self.get_new_file_folder() / self.get_new_file_name()

    def rename_related_files(self, old_path: pathlib.Path, new_path: pathlib.Path, dry_run: bool):
        if not self.config.rename_related_files:
            return

        old_directory = old_path.parent
        new_directory = new_path.parent
        related_files = [
            path
            for path in old_directory.glob(f"{old_path.stem}.*")
            if path != old_path
        ]

        if not related_files:
            return

        for related_file in related_files:
            target_path = new_directory / f"{new_path.stem}{related_file.suffix}"

            if related_file == target_path:
                continue

            if target_path.exists():
                log.warning(
                    f"Related file already exists at {target_path}, skipping rename for {related_file}"
                )
                continue

            log.info(f"Renaming related file from {related_file} to {target_path}")

            if dry_run:
                continue

            target_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                related_file.rename(target_path)
            except OSError as error:
                log.error(
                    f"Failed to rename related file from {related_file} to {target_path}: {error}"
                )

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
            log.warning(
                f"File already exists at {new_path}, adding duplicate suffix: {self.duplicate_index}"
            )
            new_path = self.get_new_file_path()

            if old_path == new_path:
                log.info(
                    "File paths are the same after adding duplicate suffix, no renaming needed."
                )
                return

        log.info(f"Renaming file from {old_path} to {new_path}")
        if self.config.dry_run:
            log.info("Dry run enabled, not actually renaming the file.")
            self.rename_related_files(old_path, new_path, dry_run=True)
            return

        moved_file = self.stash.call_GQL(
            MOVE_FILE_MUTATION,
            {
                "input": {
                    "ids": [self.file_data["id"]],
                    "destination_folder": str(self.get_new_file_folder()),
                    "destination_basename": self.get_new_file_name(),
                }
            },
        )

        log.info(f"File renamed successfully: {moved_file}")
        self.rename_related_files(old_path, new_path, dry_run=False)
