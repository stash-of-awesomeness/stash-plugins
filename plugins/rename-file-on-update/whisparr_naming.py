"""
Whisparr v3 (Eros) file naming token engine for Stash scenes.

Ports token parsing and replacement from Whisparr-Eros ``FileNameBuilder.cs`` so
patterns copied from Whisparr Media Management settings behave the same way, using
Stash GraphQL scene and file metadata as the data source.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional

# --- Regexes (from Whisparr-Eros FileNameBuilder.cs) ---

TITLE_REGEX = re.compile(
    r"(?P<tag>\{(?:imdb-|edition-))?"
    r"\{(?P<prefix>[- ._\[(]*)(?P<token>(?:[a-z0-9]+)"
    r"(?:(?P<separator>[- ._]+)(?:[a-z0-9]+))?)"
    r"(?::(?P<customFormat>[ ,a-z0-9|+-]+(?<![- ])))?"
    r"(?P<suffix>[-} ._)\]]*)\}",
    re.IGNORECASE,
)

SIMPLE_TOKEN_REGEX = re.compile(r"\s|_|\W")

FILENAME_CLEANUP_REGEX = re.compile(r"([- ._])(\1)+")
TRIM_SEPARATORS_REGEX = re.compile(r"[- ._]+$")

SCENIFY_REMOVE_CHARS = re.compile(
    r"(?<=\s)(,|<|>|/|\\|;|:|'|\"|\||`|'|~|!|\?|@|\$|%|\^|\*|-|_|=){1}(?=\s)"
    r"|('|`|'|:|\?|,)(?=(?:(?:s|m|t|ve|ll|d|re)\s)|\s|$)"
    r"|(\(|\)|\[|\]|\{|\})",
    re.IGNORECASE,
)
SCENIFY_REPLACE_CHARS = re.compile(r"[/]")
EMOJI_REGEX = re.compile(r"[\uD800-\uDFFF]")
TITLE_PREFIX_REGEX = re.compile(r"^(The|An|A) (.*?)((?: *\([^)]+\))*)$", re.IGNORECASE)
RESERVED_DEVICE_NAMES_REGEX = re.compile(
    r"^(?:aux|com[1-9]|con|lpt[1-9]|nul|prn)\.", re.IGNORECASE
)
SEASON_EPISODE_IN_TITLE_REGEX = re.compile(r"\s*-?\s*S\d+:E\d+\s*", re.IGNORECASE)

BAD_CHARACTERS = ["\\", "/", "<", ">", "?", "*", "|", '"']
GOOD_CHARACTERS = ["+", "+", "", "", "!", "-", "", ""]

PERFORMER_OTHER_GENDERS = frozenset(
    {"TRANSGENDER_MALE", "TRANSGENDER_FEMALE", "NON_BINARY", "INTERSEX"}
)


@dataclass
class TokenMatch:
    """Parsed token instance from a naming pattern."""

    tag: str
    prefix: str
    separator: str
    suffix: str
    token: str
    custom_format: Optional[str]

    def default_value(self, default: str) -> str:
        """Whisparr ``TokenMatch.DefaultValue`` — affixes suppress defaults."""
        if not self.prefix and not self.suffix:
            return default
        return ""


@dataclass
class NamingOptions:
    """Subset of Whisparr ``NamingConfig`` used when cleaning token output."""

    replace_illegal_characters: bool = True
    colon_replacement_smart: bool = True


@dataclass
class NamingContext:
    """
    Stash scene and file fields used to resolve naming tokens.

    ``studio_network`` may be set to the root parent studio name when Stash has no
    Whisparr-style network field.
    """

    scene: Mapping
    file_data: Mapping
    studio_network: str = ""
    duplicate_index: int = 0


class TokenHandlerMap:
    """Dictionary keyed by Whisparr token strings with fuzzy equality."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[TokenMatch], str]] = {}

    @staticmethod
    def simplify(token: str) -> str:
        return SIMPLE_TOKEN_REGEX.sub("", token).lower()

    def set(self, token_key: str, handler: Callable[[TokenMatch], str]) -> None:
        self._handlers[self.simplify(token_key)] = handler

    def get(self, token: str, default: Callable[[TokenMatch], str]) -> Callable[[TokenMatch], str]:
        return self._handlers.get(self.simplify(token), default)


def remove_diacritics(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def title_the(title: str) -> str:
    if not title:
        return ""
    return TITLE_PREFIX_REGEX.sub(r"\2, \1\3", title)


def title_first_character(title: str) -> str:
    if not title:
        return "_"
    for index in (0, 1):
        if index < len(title) and title[index].isalnum():
            return remove_diacritics(title[index : index + 1]).upper()[:1]
    return "_"


def clean_title(title: str) -> str:
    if not title or not str(title).strip():
        return ""
    title = str(title).replace("&", "and")
    title = SCENIFY_REPLACE_CHARS.sub(" ", title)
    title = EMOJI_REGEX.sub(" ", title)
    title = SCENIFY_REMOVE_CHARS.sub("", title)
    return remove_diacritics(title)


def clean_title_no_season_episode(title: str) -> str:
    if not title or not str(title).strip():
        return ""
    title = clean_title(title)
    title = SEASON_EPISODE_IN_TITLE_REGEX.sub("", title)
    return re.sub(r"\s+", " ", title).strip()


def slug_title(title: str) -> str:
    title = title.replace(" ", "")
    title = SCENIFY_REMOVE_CHARS.sub("", title)
    title = SCENIFY_REPLACE_CHARS.sub(" ", title)
    return title


def clean_performer(name: str) -> str:
    """Whisparr ``CleanPerformer`` — scrub performer names for filename tokens."""
    if not name:
        return ""
    cleaned = clean_title(name)
    return re.sub(r"[^\w\s]", "", cleaned).strip()


def truncate_text(input_text: str, formatter: Optional[str]) -> str:
    if not input_text or not str(input_text).strip():
        return ""
    text = str(input_text)
    max_length = 0
    if formatter:
        try:
            max_length = int(formatter.split(",")[0].strip())
        except ValueError:
            max_length = 0
    if max_length == 0 or len(text) <= abs(max_length):
        return text
    if max_length < 0:
        tail = text[::-1][: abs(max_length) - 3].rstrip(" .")[::-1]
        return f"{{ellipsis}}{tail}"
    head = text[: max_length - 3].rstrip(" .")
    return f"{head}{{ellipsis}}"


def clean_file_name(name: str, options: NamingOptions) -> str:
    result = name
    if options.replace_illegal_characters:
        if options.colon_replacement_smart:
            result = result.replace(": ", " - ")
            result = result.replace(":", "-")
        else:
            result = result.replace(":", "-")
    else:
        result = result.replace(":", "")
    for bad, good in zip(BAD_CHARACTERS, GOOD_CHARACTERS):
        if options.replace_illegal_characters:
            result = result.replace(bad, good)
        else:
            result = result.replace(bad, "")
    return result.lstrip(" .").rstrip(" ")


def clean_folder_name(name: str) -> str:
    name = FILENAME_CLEANUP_REGEX.sub(lambda m: m.group(1), name)
    return name.strip(" .")


def replace_reserved_device_names(input_text: str) -> str:
    def repl(match: re.Match) -> str:
        return match.group(0).replace(".", "_")

    return RESERVED_DEVICE_NAMES_REGEX.sub(repl, input_text)


def _scene_title(context: NamingContext) -> str:
    return context.scene.get("title") or ""


def _studio_title(context: NamingContext) -> str:
    studio = context.scene.get("studio") or {}
    return studio.get("name") or ""


def _release_date(context: NamingContext) -> str:
    return context.scene.get("date") or ""


def _release_year(context: NamingContext) -> int:
    date = _release_date(context)
    if date and len(date) >= 4 and date[:4].isdigit():
        return int(date[:4])
    return 0


def _performers(context: NamingContext) -> list:
    return sorted(
        context.scene.get("performers") or [],
        key=lambda p: (p.get("name") or "").lower(),
    )


def _performer_name(performer: Mapping) -> str:
    return performer.get("name") or ""


def _performer_alias(performer: Mapping) -> str:
    disambiguation = (performer.get("disambiguation") or "").strip()
    if disambiguation:
        return disambiguation
    return _performer_name(performer)


def _gender_female(performer: Mapping) -> bool:
    return performer.get("gender") == "FEMALE"


def _gender_male(performer: Mapping) -> bool:
    return performer.get("gender") == "MALE"


def _gender_other(performer: Mapping) -> bool:
    return performer.get("gender") in PERFORMER_OTHER_GENDERS


def _join_performers(names: list[str]) -> str:
    return " ".join(names[:4])


def _stash_id_by_endpoint(stash_ids: list, needles: tuple[str, ...]) -> str:
    for entry in stash_ids or []:
        endpoint = (entry.get("endpoint") or "").lower()
        for needle in needles:
            if needle in endpoint:
                return entry.get("stash_id") or ""
    return ""


def _primary_stash_id(context: NamingContext) -> str:
    stash_ids = context.scene.get("stash_ids") or []
    found = _stash_id_by_endpoint(stash_ids, ("stash",))
    if found:
        return found
    if stash_ids:
        return stash_ids[0].get("stash_id") or ""
    return ""


def _collection_title(context: NamingContext) -> str:
    groups = context.scene.get("groups") or []
    if not groups:
        return ""
    first = groups[0].get("group") or {}
    return first.get("name") or ""


def _quality_title_from_file(file_data: Mapping) -> str:
    height = file_data.get("height") or 0
    if height >= 2160:
        return "2160p"
    if height >= 1080:
        return "1080p"
    if height >= 720:
        return "720p"
    if height >= 480:
        return "480p"
    fmt = (file_data.get("format") or "").strip()
    if fmt:
        return fmt
    return ""


def _quality_proper_real(basename: str) -> tuple[str, str]:
    upper = basename.upper()
    proper = "Proper" if "PROPER" in upper else ""
    real = "REAL" if re.search(r"\bREAL\b", upper) else ""
    return proper, real


def _release_group_from_basename(basename: str) -> str:
    stem = Path(basename).stem
    match = re.search(r"-([A-Za-z0-9]+)$", stem)
    if match:
        return match.group(1)
    return ""


def _original_filename(file_data: Mapping, multiple_tokens: bool) -> str:
    if multiple_tokens:
        return ""
    basename = file_data.get("basename") or ""
    return Path(basename).stem


def _original_title(file_data: Mapping, multiple_tokens: bool) -> str:
    name = _original_filename(file_data, multiple_tokens)
    return clean_file_name(name, NamingOptions()) if name else ""


def build_token_handlers(context: NamingContext, multiple_tokens: bool) -> TokenHandlerMap:
    """Register all Whisparr v3 scene/movie/file tokens for a Stash rename context."""
    handlers = TokenHandlerMap()
    scene_title = _scene_title(context)
    studio = _studio_title(context)
    release_date = _release_date(context)
    release_year = _release_year(context)
    file_data = context.file_data
    basename = file_data.get("basename") or ""
    performers = _performers(context)

    def performer_tokens(
        filter_fn: Callable[[Mapping], bool],
        name_fn: Callable[[Mapping], str],
        clean: bool = False,
    ) -> Callable[[TokenMatch], str]:
        def resolve(_: TokenMatch) -> str:
            selected = [p for p in performers if filter_fn(p)]
            names = []
            for performer in selected:
                raw = name_fn(performer)
                names.append(clean_performer(raw) if clean else raw)
            return _join_performers(names)

        return resolve

    all_p = lambda _: True  # noqa: E731

    # --- Scene title tokens ---
    handlers.set("{Scene Title}", lambda m: truncate_text(scene_title, m.custom_format))
    handlers.set(
        "{Scene CleanTitle}",
        lambda m: truncate_text(clean_title(scene_title), m.custom_format),
    )
    handlers.set(
        "{Scene TitleThe}",
        lambda m: truncate_text(title_the(scene_title), m.custom_format),
    )
    handlers.set(
        "{Scene TitleFirstCharacter}",
        lambda m: truncate_text(title_first_character(title_the(scene_title)), m.custom_format),
    )
    handlers.set(
        "{Scene CleanTitleNoSeasonEpisode}",
        lambda m: truncate_text(clean_title_no_season_episode(scene_title), m.custom_format),
    )

    # --- Scene metadata / performers ---
    if release_date:
        handlers.set("{Release Date}", lambda _: release_date)
        handlers.set(
            "{Release ShortDate}",
            lambda _: release_date.replace("-", " ")[2:] if len(release_date) > 2 else release_date,
        )
    else:
        handlers.set("{Release Date}", lambda _: "Unknown")

    if release_year:
        handlers.set("{Release Year}", lambda _: str(release_year))
    else:
        handlers.set("{Release Year}", lambda _: "")

    handlers.set("{Scene Code}", lambda _: context.scene.get("code") or "")

    handlers.set("{Scene Performers}", performer_tokens(all_p, _performer_name))
    handlers.set("{Scene PerformersFemale}", performer_tokens(_gender_female, _performer_name))
    handlers.set("{Scene PerformersMale}", performer_tokens(_gender_male, _performer_name))
    handlers.set("{Scene PerformersOther}", performer_tokens(_gender_other, _performer_name))
    handlers.set("{Scene PerformersAlias}", performer_tokens(all_p, _performer_alias))
    handlers.set(
        "{Scene PerformersFemaleAlias}", performer_tokens(_gender_female, _performer_alias)
    )
    handlers.set("{Scene PerformersMaleAlias}", performer_tokens(_gender_male, _performer_alias))
    handlers.set(
        "{Scene PerformersOtherAlias}", performer_tokens(_gender_other, _performer_alias)
    )
    handlers.set("{Scene CleanPerformers}", performer_tokens(all_p, _performer_name, clean=True))
    handlers.set(
        "{Scene CleanPerformersFemale}",
        performer_tokens(_gender_female, _performer_name, clean=True),
    )
    handlers.set(
        "{Scene CleanPerformersMale}",
        performer_tokens(_gender_male, _performer_name, clean=True),
    )
    handlers.set(
        "{Scene CleanPerformersOther}",
        performer_tokens(_gender_other, _performer_name, clean=True),
    )
    handlers.set(
        "{Scene CleanPerformersAlias}",
        performer_tokens(all_p, _performer_alias, clean=True),
    )
    handlers.set(
        "{Scene CleanPerformersFemaleAlias}",
        performer_tokens(_gender_female, _performer_alias, clean=True),
    )
    handlers.set(
        "{Scene CleanPerformersMaleAlias}",
        performer_tokens(_gender_male, _performer_alias, clean=True),
    )
    handlers.set(
        "{Scene CleanPerformersOtherAlias}",
        performer_tokens(_gender_other, _performer_alias, clean=True),
    )

    # --- Studio tokens ---
    if studio:
        handlers.set("{Studio Title}", lambda _: studio)
        handlers.set("{Studio TitleSlug}", lambda _: slug_title(studio))
        handlers.set("{Studio CleanTitle}", lambda _: clean_title(studio))
        handlers.set("{Studio CleanTitleSlug}", lambda _: slug_title(clean_title(studio)))
        handlers.set("{Studio TitleThe}", lambda _: title_the(studio))
        handlers.set(
            "{Studio TitleFirstCharacter}",
            lambda _: title_the(studio)[:1].upper() if title_the(studio) else "",
        )

    network = context.studio_network or ""
    handlers.set("{Studio Network}", lambda _: network)
    handlers.set("{Studio CleanNetwork}", lambda _: clean_title(network))
    handlers.set("{Studio CleanNetworkSlug}", lambda _: slug_title(clean_title(network)))

    # --- ID tokens ---
    stash_ids = context.scene.get("stash_ids") or []
    handlers.set("{StashId}", lambda _: _primary_stash_id(context))
    handlers.set(
        "{ImdbId}",
        lambda _: _stash_id_by_endpoint(stash_ids, ("imdb",)),
    )
    handlers.set(
        "{TmdbId}",
        lambda _: _stash_id_by_endpoint(stash_ids, ("tmdb", "themoviedb")),
    )

    # --- Movie tokens (mapped to scene metadata) ---
    handlers.set("{Movie Title}", lambda m: truncate_text(scene_title, m.custom_format))
    handlers.set(
        "{Movie CleanTitle}",
        lambda m: truncate_text(clean_title(scene_title), m.custom_format),
    )
    handlers.set(
        "{Movie TitleThe}",
        lambda m: truncate_text(title_the(scene_title), m.custom_format),
    )
    handlers.set(
        "{Movie CleanTitleThe}",
        lambda m: truncate_text(clean_title(title_the(scene_title)), m.custom_format),
    )
    handlers.set(
        "{Movie TitleFirstCharacter}",
        lambda _: title_first_character(title_the(scene_title)),
    )
    handlers.set(
        "{Movie Collection}",
        lambda m: truncate_text(_collection_title(context), m.custom_format),
    )

    # --- Quality ---
    quality_title = _quality_title_from_file(file_data)
    proper, real = _quality_proper_real(basename)
    quality_full = " ".join(part for part in (quality_title, proper, real) if part).strip()
    handlers.set("{Quality Title}", lambda _: quality_title)
    handlers.set("{Quality Full}", lambda _: quality_full)
    handlers.set("{Quality Proper}", lambda _: proper)
    handlers.set("{Quality Real}", lambda _: real)

    # --- MediaInfo (partial — Stash file fields only) ---
    video_codec = file_data.get("video_codec") or ""
    audio_codec = file_data.get("audio_codec") or ""
    handlers.set("{MediaInfo Video}", lambda _: video_codec)
    handlers.set("{MediaInfo VideoCodec}", lambda _: video_codec)
    handlers.set("{MediaInfo Audio}", lambda _: audio_codec)
    handlers.set("{MediaInfo AudioCodec}", lambda _: audio_codec)
    handlers.set("{MediaInfo Simple}", lambda _: f"{video_codec} {audio_codec}".strip())
    handlers.set("{MediaInfo Full}", lambda _: f"{video_codec} {audio_codec}".strip())
    handlers.set("{MediaInfo VideoBitDepth}", lambda _: "")
    handlers.set("{MediaInfo AudioChannels}", lambda _: "")
    handlers.set("{MediaInfo AudioLanguages}", lambda _: "")
    handlers.set("{MediaInfo AudioLanguagesAll}", lambda _: "")
    handlers.set("{MediaInfo SubtitleLanguages}", lambda _: "")
    handlers.set("{MediaInfo SubtitleLanguagesAll}", lambda _: "")
    handlers.set("{MediaInfo 3D}", lambda _: "")
    handlers.set("{MediaInfo VideoDynamicRange}", lambda _: "")
    handlers.set("{MediaInfo VideoDynamicRangeType}", lambda _: "")

    # --- Original / release group ---
    handlers.set(
        "{Original Title}",
        lambda _: _original_title(file_data, multiple_tokens),
    )
    handlers.set(
        "{Original Filename}",
        lambda _: _original_filename(file_data, multiple_tokens),
    )
    release_group = _release_group_from_basename(basename)

    def release_group_handler(match: TokenMatch) -> str:
        if release_group:
            return truncate_text(release_group, match.custom_format)
        return match.default_value("Whisparr")

    handlers.set("{Release Group}", release_group_handler)

    # --- Unsupported in Stash (empty but valid) ---
    handlers.set("{Edition Tags}", lambda _: "")
    handlers.set("{Custom Formats}", lambda _: "")
    handlers.set("{Custom Format}", lambda _: "")

    return handlers


def replace_token(
    match: re.Match,
    handlers: TokenHandlerMap,
    options: NamingOptions,
) -> str:
    """Replace a single regex match using registered handlers."""
    custom = match.group("customFormat")
    token_match = TokenMatch(
        tag=match.group("tag") or "",
        prefix=match.group("prefix") or "",
        separator=match.group("separator") or "",
        suffix=match.group("suffix") or "",
        token=match.group("token") or "",
        custom_format=custom if custom else None,
    )

    handler = handlers.get(token_match.token, lambda _: "")
    replacement_text = handler(token_match).strip()

    token_letters = [c for c in token_match.token if c.isalpha()]
    if token_letters and all(c.islower() for c in token_letters):
        replacement_text = replacement_text.lower()
    elif token_letters and all(c.isupper() for c in token_letters):
        replacement_text = replacement_text.upper()

    if token_match.separator:
        replacement_text = replacement_text.replace(" ", token_match.separator)

    replacement_text = clean_file_name(replacement_text, options)

    if replacement_text:
        replacement_text = token_match.tag + token_match.prefix + replacement_text + token_match.suffix

    return replacement_text


def replace_tokens(pattern: str, handlers: TokenHandlerMap, options: NamingOptions) -> str:
    return TITLE_REGEX.sub(
        lambda m: replace_token(m, handlers, options),
        pattern,
    )


def apply_naming_pattern(
    pattern: str,
    context: NamingContext,
    *,
    for_folder: bool = False,
    replace_illegal: bool = True,
) -> str:
    """
    Apply a Whisparr v3 naming pattern to Stash scene/file data.

    Path separators split folder patterns into components; file patterns are
    processed as a single component.
    """
    if not pattern:
        return ""

    options = NamingOptions(replace_illegal_characters=replace_illegal)
    multiple_tokens = len(TITLE_REGEX.findall(pattern)) > 1
    handlers = build_token_handlers(context, multiple_tokens)

    segments = re.split(r"[\\/]", pattern) if for_folder or ("\\" in pattern or "/" in pattern) else [pattern]
    components: list[str] = []

    for segment in segments:
        if not segment:
            continue
        component = replace_tokens(segment, handlers, options).strip()
        component = FILENAME_CLEANUP_REGEX.sub(lambda m: m.group(1), component)
        component = TRIM_SEPARATORS_REGEX.sub("", component)
        component = component.replace("{ellipsis}", "...")
        component = replace_reserved_device_names(component)
        if for_folder:
            component = clean_folder_name(component)
        if component:
            components.append(component)

    return str(Path(*components)) if for_folder and len(components) > 1 else (components[0] if components else "")


def apply_duplicate_suffix(template: str, index: int) -> str:
    """
    Expand the plugin duplicate-file suffix template.

    Supports ``{index}`` (preferred) and legacy ``$index$``.
    """
    text = template.replace("{index}", str(index))
    return text.replace("$index$", str(index))
