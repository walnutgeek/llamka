from pathlib import Path
from typing import Any

import pytest

from llamka.llore.config import BotConfig, Config, FileGlob, load_config
from llamka.misc import EnsureJson


def sanitize_api_key(o: Any) -> Any:
    if isinstance(o, list):
        return list(map(sanitize_api_key, o))
    elif isinstance(o, dict):
        dd = {}
        for k, v in o.items():
            if k in ["api_key", "x-api-key"]:
                v = f"{v[:3]}..."
            dd[k] = sanitize_api_key(v)
        return dd
    else:
        return o


EnsureJson("config.json", "tests/", "data/", sanitize_api_key).forward().backward()
EnsureJson("cryptoduck.json", "tests/", "data/bots/", None).forward().backward()


@pytest.mark.debug
def test_config():
    parent_dir, config, bots = load_config("data/config.json", root=".")
    assert parent_dir == Path(".").absolute()
    assert config is not None
    assert bots is not None
    assert len(bots) == 1
    parent_dir, config, bots = load_config("data/config.json")
    assert parent_dir is None
    assert isinstance(config, Config)
    list_of_keys = list(config.llm_models.keys())
    assert list_of_keys == ["4o", "sonnet", "phi4", "llama3.2", "mistral"]
    _4o = config.llm_models[list_of_keys[0]]
    assert _4o.model_name == "gpt-4o"
    assert _4o.url[:8] == "https://"
    assert _4o.api_key is not None
    assert _4o.api_key[:3] == "sk-"
    _phi4 = config.llm_models[list_of_keys[2]]
    assert _phi4.model_name == "phi4:latest"
    assert _phi4.api_key is None
    assert _phi4.url[:7] == "http://"
    assert len(bots) == 1
    assert bots[0].name == "cryptoduck"
    assert len(bots[0].files) == 1
    for bot in bots:
        assert isinstance(bot, BotConfig)
        assert isinstance(bot.files[0], FileGlob)
        assert bot.files[0].dir is not None
        assert bot.files[0].glob is not None
