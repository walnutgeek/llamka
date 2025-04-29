import pytest

from llamka.llore.config import load_config


@pytest.mark.debug
def test_config():
    config = load_config("data/config.json")
    assert config.models[0].name == "4o"
    assert config.models[0].url[:8] == "https://"
    assert config.models[0].api_key[:3] == "sk-"
    assert config.models[0].params == {"model": "gpt-4o", "temperature": 0.5}
    assert len(config.files) == 4
    for f in config.get_paths():
        assert f.exists()
