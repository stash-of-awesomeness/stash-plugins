import typing
from stashapi.stashapp import StashInterface

# Note:
#   - IDs are string formatted ints, e.g. "1".
#   - Dates are YYYY-MM-DD.
#   - Paths are absolute.


class SceneParentStudioDict(typing.TypedDict):
    id: str
    name: str


class SceneStudioDict(SceneParentStudioDict):
    parent_studio: SceneParentStudioDict | None


class SceneFileDict(typing.TypedDict):
    id: str
    path: str
    basename: str
    format: str
    width: int
    height: int
    duration: float
    video_codec: str
    audio_codec: str


class SceneDict(typing.TypedDict):
    id: str
    title: str
    code: str
    date: str
    organized: bool
    studio: SceneStudioDict
    files: list[SceneFileDict]


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


def get_scene(stash: StashInterface, scene_id: int) -> SceneDict:
    return typing.cast(typing.Any, stash.find_scene(scene_id, fragment=SCENE_FRAGMENT))
