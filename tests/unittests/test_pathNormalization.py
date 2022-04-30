from pathlib import Path

import pytest

from barney.Utilities.parsers import normalizePath

combinations = [
    ("/dat/corpora", "//dat/corpora"),
    ("/smb/dat/corpora", "//dat/corpora"),
    ("//dat/corpora", "//dat/corpora"),
    ((Path.home() / "test").as_posix(), (Path.home() / "test").as_posix()),
]

combinations = [
    ("/dat/corpora", "//dat/corpora"),
    ("/smb/dat/corpora", "//dat/corpora"),
    ("//dat/corpora", "//dat/corpora"),
    ((Path.home() / "test").as_posix(), (Path.home() / "test").as_posix()),
]


@pytest.mark.parametrize("test_input_path, normalized", combinations)
def test_pathNormalization(test_input_path: str, normalized: str) -> None:
    assert (
        normalizePath(test_input_path) == normalized
    ), f"Original input {test_input_path}, Output {normalized}"
    return None
