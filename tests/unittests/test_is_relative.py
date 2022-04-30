import pytest  # noqa: F401

from barney.Utilities.parsers import is_relative

combinations = [
    ("//dat/corpora/Sensory/AMT/export/collection/speaker/test.wav", False),
    ("./speaker/test.wav", True),
    ("C:\\Users\\ogi\\collection\\speaker\\test.wav", False),
    ("C:/Users/ogi/collection/speaker/test.wav", False),
    ("speaker\\test.wav", True),
    ("speaker/test.wav", True),
    ("/dat/corpora/Sensory/AMT/export/collection/speaker/test.wav", False),
    ("\\\\dat\\corpora\\Sensory\\AMT\\export\\collection\\speaker\\test.wav", False),
    ("test.wav", True),
    (
        "/smb/dat/corpora/Sensory/AMT/export/AMT_en_US_20180821_JA/AMT_en_US_20180821_JA.A70L26UXLTGLC/AMT_en_US_20180821_JA.A70L26UXLTGLC.1534990206716.wav",
        False,
    ),
]


@pytest.mark.parametrize("test_input_path, expected", combinations)
def test_is_relative(test_input_path: str, expected: bool) -> None:
    assert is_relative(test_input_path) is expected
    return None
