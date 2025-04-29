import shutil
from pathlib import Path

import pytest

from llamka.llore.config import load_config

data_config = Path("data/config.json")
stub_config = Path("tests/config.json")
if not data_config.exists():
    data_config.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(stub_config, data_config)


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
