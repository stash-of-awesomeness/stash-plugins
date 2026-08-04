import random
import string
from datetime import date
import tempfile
import os

from api import SceneDict, SceneFileDict, SceneStudioDict


def gen_string() -> str:
    return "".join(random.choices(string.ascii_letters, k=10))


def gen_id() -> str:
    return str(random.randint(1, 100_000))


def get_isodate() -> str:
    return date.today().isoformat()


def scene_studio_dict_factory(**kwargs: SceneStudioDict):
    return SceneStudioDict(
        id=gen_id(),
        name=gen_string(),
        parent_studio=None,
        **kwargs,
    )


def scene_file_dict_factory(**kwargs: SceneFileDict):
    fname = f"{gen_string()}.mp4"
    if (tmpdir := tempfile.tempdir) is None:
        raise RuntimeError("Can't get temporary directory")
    return SceneFileDict(
        id=gen_id(),
        path=os.path.join(tmpdir, fname),
        basename=fname,
        format="mp4",
        width=1920,
        height=1080,
        duration=1245.12,
        video_codec="h264",
        audio_codec="aac",
        **kwargs,
    )


def scene_dict_factory(**kwargs: SceneDict):
    return SceneDict(
        id=gen_id(),
        title=gen_string(),
        code=gen_id(),
        date=get_isodate(),
        organized=True,
        studio=scene_studio_dict_factory(),
        files=[scene_file_dict_factory()],
        **kwargs,
    )
