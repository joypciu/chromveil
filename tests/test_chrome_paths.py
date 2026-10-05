from chromveil.chrome_paths import find_system_chrome
from chromveil.profile import default_driver_name


def test_default_driver_is_patchright_when_installed():
    assert default_driver_name() == "patchright"


def test_find_system_chrome_optional():
    path = find_system_chrome()
    if path:
        assert path.lower().endswith("chrome.exe")
