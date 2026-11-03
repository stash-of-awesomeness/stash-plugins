"""Tests for Whisparr v3 naming token replacement."""

import pytest

from whisparr_naming import (
    NamingContext,
    apply_duplicate_suffix,
    apply_naming_pattern,
    clean_title,
    title_the,
)


@pytest.fixture
def sample_context() -> NamingContext:
    return NamingContext(
        scene={
            "title": "The Scene Title S01:E02",
            "code": "ABC-123",
            "date": "2010-01-01",
            "studio": {"name": "Studio Title"},
            "performers": [
                {"name": "Abigail Mac", "gender": "FEMALE", "disambiguation": ""},
                {"name": "John Holmes", "gender": "MALE", "disambiguation": ""},
                {"name": "Lulu Chu", "gender": "TRANSGENDER_FEMALE", "disambiguation": ""},
            ],
            "stash_ids": [
                {"endpoint": "https://stashdb.org/graphql", "stash_id": "155f2559-d1f1-42b1-8cbe-9008542df5ce"},
            ],
            "groups": [{"group": {"name": "Example Collection"}}],
        },
        file_data={
            "basename": "release.name.1080p.x264-EVOLVE.mp4",
            "height": 1080,
            "width": 1920,
            "format": "mp4",
            "video_codec": "h264",
            "audio_codec": "aac",
        },
        studio_network="Network Title",
    )


def test_clean_title_and_title_the():
    assert clean_title("Foo & Bar") == "Foo and Bar"
    assert title_the("The Dark Scene") == "Dark Scene, The"


def test_naming_modal_scene_template(sample_context):
    pattern = "{Studio CleanTitle} - {Release Date} - {Scene CleanTitle} [{Quality Title}]"
    result = apply_naming_pattern(pattern, sample_context)
    assert result == "Studio Title - 2010-01-01 - The Scene Title S01-E02 [1080p]"


def test_separator_and_slug_tokens(sample_context):
    pattern = "{Studio CleanTitleSlug}.{Scene CleanTitle}.{Release Date}{.Quality.Title}"
    result = apply_naming_pattern(pattern, sample_context)
    assert "StudioTitle" in result
    assert "2010-01-01" in result
    assert "1080p" in result


def test_release_short_date(sample_context):
    result = apply_naming_pattern("{Release ShortDate}", sample_context)
    assert result == "10 01 01"


def test_scene_clean_title_no_season_episode(sample_context):
    result = apply_naming_pattern("{Scene CleanTitleNoSeasonEpisode}", sample_context)
    assert "S01" not in result
    assert "E02" not in result


def test_performer_tokens_capped_at_four(sample_context):
    sample_context.scene["performers"] = [
        {"name": f"Performer {index}", "gender": "FEMALE", "disambiguation": ""}
        for index in range(6)
    ]
    result = apply_naming_pattern("{Scene PerformersFemale}", sample_context)
    assert result.count("Performer") == 4


def test_optional_quality_affix_empty(sample_context):
    sample_context.file_data["height"] = 0
    sample_context.file_data["format"] = ""
    pattern = "Title{[Quality Title]}"
    result = apply_naming_pattern(pattern, sample_context)
    assert result == "Title"


def test_stash_id_token(sample_context):
    result = apply_naming_pattern("{StashId}", sample_context)
    assert result == "155f2559-d1f1-42b1-8cbe-9008542df5ce"


def test_studio_network_from_context(sample_context):
    result = apply_naming_pattern("{Studio Network}", sample_context)
    assert result == "Network Title"


def test_folder_path_segments(sample_context):
    pattern = "{Studio CleanTitle}/{Release Year}"
    result = apply_naming_pattern(pattern, sample_context, for_folder=True)
    assert "Studio Title" in result
    assert "2010" in result


def test_duplicate_suffix_placeholder():
    assert apply_duplicate_suffix(" ({index})", 2) == " (2)"
    assert apply_duplicate_suffix(" ($index$)", 3) == " (3)"


def test_truncation_formatter(sample_context):
    sample_context.scene["title"] = "A" * 80
    result = apply_naming_pattern("{Scene CleanTitle:20}", sample_context)
    assert result.endswith("...")
    assert len(result) <= 20
