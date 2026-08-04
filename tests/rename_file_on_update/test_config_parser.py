import pytest

from config_parser import Config


@pytest.mark.parametrize(
    "key,value",
    (
        ("DEFAULT_DIRECTORY_PATH_FORMAT", ""),
        ("DEFAULT_FILE_NAME_FORMAT", ""),
        ("DRY_RUN", False),
        ("RENAME_UNORGANIZED", False),
        ("RENAME_RELATED_FILES", True),
        ("REMOVE_EXTRA_SPACES_FROM_FILE_NAME", False),
        ("DUPLICATE_FILE_SUFFIX", " ($index$)"),
    ),
)
def test_config_defaults(key, value):
    """
    Default configuration values.
    """
    conf = Config({})
    assert getattr(conf, key) == value


def test_missing_config_return_none():
    """
    Config not in defaults.
    """
    conf = Config({})
    assert conf.MISSING == None


@pytest.mark.parametrize(
    "inkey,outkey,outval",
    (
        ("foo", "FOO", 1),
        ("fooBar", "FOO_BAR", 1),
        # only snakeCase supported.
        ("Foo", "FOO", None),
        ("FooBar", "FOO_BAR", None),
    ),
)
def test_non_default_config(inkey, outkey, outval):
    """
    A key-value outside defaults.
    """
    conf = Config({inkey: 1})
    assert getattr(conf, outkey) == outval


def test_default_override():
    """
    A default value key be overriden.
    """
    conf = Config({"renameRelatedFiles": False})
    assert conf.RENAME_RELATED_FILES is False

def test_snake_case_accessable():
    """
    duplicate_file_suffix attribute accessable.
    """
    conf = Config({})
    assert conf.duplicate_file_suffix is not None
