"""Tests for file_manager path sanitization."""

import pathlib

import pytest

from config_parser import Config
from path_sanitize import sanitize_directory_path


def test_sanitize_directory_strips_unsafe_chars_but_keeps_separators():
    config = Config({"allowUnsafeCharacters": False})
    path = pathlib.Path("/media/studio: bad/name")
    result = sanitize_directory_path(path, config)
    assert ":" not in str(result)
    assert str(result).replace("\\", "/").count("/") >= 2


def test_sanitize_directory_collapses_spaces_when_enabled():
    config = Config(
        {
            "allowUnsafeCharacters": True,
            "removeExtraSpacesFromFileName": True,
        }
    )
    path = pathlib.Path("/media/foo   bar/baz")
    result = sanitize_directory_path(path, config)
    assert "   " not in str(result)
