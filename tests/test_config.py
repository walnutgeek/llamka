from typing import Any

from llamka.llore.config import BotConfig, Config, FileGlob, load_config
from llamka.misc import EnsureJson


def sanitize_api_key(o: Any) -> Any:
    if isinstance(o, list):
        return list(map(sanitize_api_key, o))
    elif isinstance(o, dict):
        dd = {}
        for k, v in o.items():
            if k == "api_key":
                v = f"{v[:3]}..."
            dd[k] = sanitize_api_key(v)
        return dd
    else:
        return o


EnsureJson("config.json", "tests/", "data/", sanitize_api_key).forward().backward()
EnsureJson("cryptoduck.json", "tests/", "data/bots/", None).forward().backward()


def test_config():
    config, bots = load_config("data/config.json")
    assert isinstance(config, Config)
    list_of_keys = list(config.llm_models.keys())
    assert list_of_keys == ["4o", "phi4", "llama3.2", "mistral"]
    _4o = config.llm_models[list_of_keys[0]]
    assert _4o.model_name == "gpt-4o"
    assert _4o.url[:8] == "https://"
    assert _4o.api_key is not None
    assert _4o.api_key[:3] == "sk-"
    _phi4 = config.llm_models[list_of_keys[1]]
    assert _phi4.model_name == "phi4:latest"
    assert _phi4.api_key is None
    assert _phi4.url[:7] == "http://"
    for bot in bots:
        assert isinstance(bot, BotConfig)
        assert isinstance(bot.files[0], FileGlob)
        assert bot.files[0].dir is not None
        assert bot.files[0].glob is not None
