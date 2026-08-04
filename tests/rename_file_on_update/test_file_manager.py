from pathlib import Path
from unittest import mock
import typing
from itertools import product

import pytest

from file_manager import StashFile
from config_parser import Config
from api import SceneStudioDict
import factories as f


@pytest.fixture
def renamer_config():
    return Config({})


@pytest.fixture
def stash_file(renamer_config):
    with mock.patch("stashapi.stashapp.StashInterface", autospec=True) as stash:
        scene = f.scene_dict_factory()
        yield StashFile(
            stash,
            renamer_config,
            scene,
            scene["files"][0],
        )


def test_get_old_file_path(stash_file: StashFile):
    """
    Method return absolute path to a file.
    """
    stash_file.file_data["path"] = "foo/bar.mp4"
    fp = stash_file.get_old_file_path()
    assert isinstance(fp, Path)
    assert str(fp).startswith("/")


def test_get_new_file_folder_no_default_directory_format(stash_file: StashFile):
    """
    Default behaviour when no directory formatter specfied.
    """
    stash_file.config = Config({})
    stash_file.file_data["path"] = "/media/foo/bar.mp4"
    assert str(stash_file.get_new_file_folder()).endswith("foo")


def test_get_new_file_folder_no_fromatting(stash_file: StashFile):
    """
    A static directory formatter.
    """
    stash_file.config = Config({"defaultDirectoryPathFormat": "/scenes/"})
    assert str(stash_file.get_new_file_folder()) == "/scenes"


def test_get_new_file_folder_formatted_studio_chain(stash_file: StashFile):
    """
    Studio chain formatter applyed on directory template.
    """
    typing.cast(mock.MagicMock, stash_file.stash).find_studio.return_value = (
        SceneStudioDict(
            name="A",
            id=f.gen_id(),
            parent_studio=None,
        )
    )
    stash_file.config = Config(
        {"defaultDirectoryPathFormat": "/scenes/$parent_studio_chain$"}
    )
    stash_file.scene_data["studio"]["name"] = "C"
    # It is a bit weird here, stash will return studio -> parent studio,
    # but to get grandparent studio, you'll need to query parent studio,
    # get its parent (grandparent) stuido id and query it again.
    # Code is written in way it ignores name of the studio we query, instead
    # using whatever is in response, B should be A if we we want to follow
    # it.
    stash_file.scene_data["studio"]["parent_studio"] = SceneStudioDict(
        name="B",
        id=f.gen_id(),
        parent_studio=None,
    )

    assert str(stash_file.get_new_file_folder()) == "/scenes/A/C"


def test_get_new_file_folder_formatted_studio_chain_no_parent(stash_file: StashFile):
    """
    Studio chain formatter when studio has no parent, shouldn't do any API calls.
    """
    typing.cast(mock.MagicMock, stash_file.stash).find_studio.side_effect = (
        AssertionError("You should not!")
    )
    stash_file.config = Config(
        {"defaultDirectoryPathFormat": "/scenes/$parent_studio_chain$"}
    )
    stash_file.scene_data["studio"]["name"] = "C"
    stash_file.scene_data["studio"]["parent_studio"] = None
    assert str(stash_file.get_new_file_folder()) == "/scenes/C"


@pytest.mark.parametrize(
    "var,fn",
    tuple(
        product(
            (
                "audio_codec",
                "format",
                "height",
                "video_codec",
                "width",
                "title",
                "date",
            ),
            ("get_new_file_folder", "get_new_file_name"),
        )
    ),
)
def test_simple_vars_path_and_name_subs(
    stash_file: StashFile,
    var: str,
    fn: str,
):
    """
    Test all simple, non-computed vars available directly on a scene or file.
    Both directory formatter and file formatter should behave exacetely the same.
    """
    stash_file.config = Config(
        {
            "defaultDirectoryPathFormat": f"/${var}$",
            "defaultFileNameFormat": f"${var}$",
        }
    )
    vars = dict(stash_file.scene_data) | dict(stash_file.file_data)
    ret = str(getattr(stash_file, fn)()).lstrip("/")
    assert ret == f"{vars[var]}"


def test_get_new_file_name_index_var(stash_file: StashFile):
    """
    Index variable is taken from the duplicate_index class attr.
    """
    stash_file.duplicate_index = 42
    stash_file.config = Config({"defaultFileNameFormat": "$title$.$ext$"})
    stash_file.scene_data["title"] = "Inside"
    assert str(stash_file.get_new_file_name()) == "Inside (42).mp4"


def test_get_new_file_name_uniq(stash_file: StashFile):
    """
    Uniq file has no index inserted.
    """
    stash_file.duplicate_index = 0
    stash_file.config = Config({"defaultFileNameFormat": "$title$.$ext$"})
    stash_file.scene_data["title"] = "Inside"
    assert str(stash_file.get_new_file_name()) == "Inside.mp4"


@pytest.mark.parametrize("fn", ("get_new_file_folder", "get_new_file_name"))
def test_month_var(stash_file: StashFile, fn: str):
    """
    Month computed formatter.
    """
    stash_file.config = Config(
        {
            "defaultDirectoryPathFormat": "/$month$",
            "defaultFileNameFormat": "$month$",
        }
    )
    stash_file.scene_data["date"] = "2000-01-02"
    ret = str(getattr(stash_file, fn)()).lstrip("/")
    assert ret == "01"


@pytest.mark.parametrize("fn", ("get_new_file_folder", "get_new_file_name"))
def test_year_var(stash_file: StashFile, fn: str):
    """
    Month computed formatter.
    """
    stash_file.config = Config(
        {
            "defaultDirectoryPathFormat": "/$year$",
            "defaultFileNameFormat": "$year$",
        }
    )
    stash_file.scene_data["date"] = "2000-01-02"
    ret = str(getattr(stash_file, fn)()).lstrip("/")
    assert ret == "2000"


@pytest.mark.parametrize("fn", ("get_new_file_folder", "get_new_file_name"))
def test_studio_name_var(stash_file: StashFile, fn: str):
    """
    Extracted studio name.
    """
    stash_file.config = Config(
        {
            "defaultDirectoryPathFormat": "/$studio_name$",
            "defaultFileNameFormat": "$studio_name$",
        }
    )
    stash_file.scene_data["studio"]["name"] = "S"
    ret = str(getattr(stash_file, fn)()).lstrip("/")
    assert ret == "S"


@pytest.mark.parametrize("fn", ("get_new_file_folder", "get_new_file_name"))
def test_studio_code_var(stash_file: StashFile, fn: str):
    """
    Extracted studio code.
    """
    stash_file.config = Config(
        {
            "defaultDirectoryPathFormat": "/$studio_code$",
            "defaultFileNameFormat": "$studio_code$",
        }
    )
    stash_file.scene_data["code"] = "12442"
    ret = str(getattr(stash_file, fn)()).lstrip("/")
    assert ret == "12442"


def test_get_new_file_path(stash_file: StashFile):
    """
    Returns full file path to move file to.
    """
    stash_file.config = Config(
        {
            "defaultDirectoryPathFormat": "/scenes",
            "defaultFileNameFormat": "$title$.$ext$",
        }
    )
    stash_file.scene_data["title"] = "foo"
    assert stash_file.get_new_file_path() == Path("/scenes/foo.mp4")


def test_rename_file(stash_file: StashFile, tmp_path: Path):
    """
    E2E Rename test.
    """
    # Prepare "old" path.
    old = tmp_path / "old" / "file.mp4"
    old.parent.mkdir(exist_ok=True)
    old.touch()
    # Alter files array, then assign it to `file_data`, no reason,
    # just looks closer to real.
    stash_file.scene_data["files"][0]["path"] = str(old)
    stash_file.scene_data["files"][0]["basename"] = old.name
    stash_file.scene_data["files"][0]["id"] = "833"
    stash_file.file_data = stash_file.scene_data["files"][0]
    stash_file.scene_data["title"] = "known name"

    # Prepare "new" path.
    new = tmp_path / "new"
    new.mkdir(exist_ok=True)

    typing.cast(mock.MagicMock, stash_file.stash).call_GQL.return_value = "hehahu"

    stash_file.config = Config(
        {
            "defaultDirectoryPathFormat": str(new / "scenes"),
            "defaultFileNameFormat": "$title$.$ext$",
        }
    )

    stash_file.rename_file()
    typing.cast(mock.MagicMock, stash_file.stash).call_GQL.assert_has_calls(
        [
            mock.call(
                mock.ANY,
                {
                    "input": {
                        "ids": ["833"],
                        "destination_folder": new / "scenes",
                        "destination_basename": "known name.mp4",
                    },
                },
            ),
        ]
    )
