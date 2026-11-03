# Whisparr v3 naming tokens (rename-file-on-update)

This plugin uses the same **brace token syntax** as [Whisparr v3 (Whisparr-Eros)](https://github.com/Whisparr/Whisparr-Eros) scene and movie naming. Copy patterns from Whisparr **Settings → Media Management → Scene Naming** (or the naming modal token list in `NamingModal.tsx`).

## Breaking change (v0.2.0)

Version **0.1.x** used Stash-style `$variable$` placeholders. Those are **removed**. Update `defaultDirectoryPathFormat` and `defaultFileNameFormat` to Whisparr tokens before upgrading.

## Example patterns

| Pattern | Example output (illustrative) |
| --- | --- |
| `{Studio CleanTitle} - {Release Date} - {Scene CleanTitle} [{Quality Title}]` | `Studio Title - 2010-01-01 - The Scene Title [1080p]` |
| `{Studio CleanTitleSlug}.{Scene CleanTitle}.{Release Date}{.Quality.Title}` | Dots between words when using `{Token.Subtoken}` separators |

Token **case** in the pattern controls output case (e.g. `{studio cleantitle}` → lowercase).

Optional **affixes** around tokens (Whisparr behavior): `{[Quality Title]}` omits brackets when quality is empty.

## Stash data mapping

| Token group | Stash source |
| --- | --- |
| Scene title tokens | `scene.title` |
| `{Scene Code}` | `scene.code` |
| `{Release Date}`, `{Release ShortDate}`, `{Release Year}` | `scene.date` |
| Performer tokens | `scene.performers` (`name`, `gender`, `disambiguation` as alias) |
| Studio tokens | `scene.studio.name` |
| `{Studio Network}`, `{Studio CleanNetwork}`, `{Studio CleanNetworkSlug}` | Root **parent** studio name (Stash has no network field) |
| `{StashId}` | `scene.stash_ids` (prefers Stash endpoint) |
| `{ImdbId}`, `{TmdbId}` | Matching `stash_ids` endpoints |
| `{Movie *}` | Mapped from scene title / first group name |
| `{Quality *}` | Derived from file `height` / `format`; Proper/REAL from basename |
| `{MediaInfo VideoCodec}`, `{MediaInfo AudioCodec}`, `{MediaInfo Simple}`, `{MediaInfo Full}` | File `video_codec`, `audio_codec` |
| `{Original Filename}`, `{Original Title}` | Current file basename |
| `{Release Group}` | Parsed from basename suffix `-Group`; default `Whisparr` if no affixes |

## Tokens that resolve empty

No Stash equivalent today (patterns still parse cleanly):

- `{Edition Tags}`
- `{Custom Formats}`, `{Custom Format:…}`
- `{MediaInfo AudioLanguages}`, subtitle languages, HDR/3D/bit depth/channel tokens

## Plugin-only

| Placeholder | Use |
| --- | --- |
| `{index}` | Duplicate file suffix setting only (not a Whisparr token) |

Legacy `$index$` in the duplicate suffix is still replaced for older configs.

## Reference

- Whisparr-Eros token UI: [NamingModal.tsx](https://github.com/Whisparr/Whisparr-Eros/blob/eros-develop/frontend/src/Settings/MediaManagement/Naming/NamingModal.tsx)
- Replacement logic: [FileNameBuilder.cs](https://github.com/Whisparr/Whisparr-Eros/blob/eros-develop/src/NzbDrone.Core/Organizer/FileNameBuilder.cs)
