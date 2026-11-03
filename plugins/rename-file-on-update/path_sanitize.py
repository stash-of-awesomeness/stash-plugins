"""Path sanitization for renamed scene files and folders."""

import pathlib
import re

# Windows-forbidden characters except path separators (parent stash-plugins PR #5).
_DIRECTORY_UNSAFE_CHARS = re.compile(r'[<>:"|?*]')


def sanitize_directory_path(directory_path: pathlib.Path, config) -> pathlib.Path:
    """
    Apply ``allowUnsafeCharacters`` and ``removeExtraSpacesFromFileName`` to folder paths.

    Filenames use a stricter regex that also strips ``/`` and ``\\``; directory paths keep
    separators so multi-segment ``defaultDirectoryPathFormat`` values remain valid.
    """
    result = directory_path
    path_str = str(result)

    if not config.allow_unsafe_characters:
        path_str = _DIRECTORY_UNSAFE_CHARS.sub("", path_str)
        result = pathlib.Path(path_str)

    if config.remove_extra_spaces_from_file_name:
        path_str = re.sub(r"\s+", " ", str(result))
        result = pathlib.Path(path_str)

    return result
