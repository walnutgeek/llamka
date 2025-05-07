import shutil
from pathlib import Path
from typing import NamedTuple

from llamka.llore.config import BotConfig, Config, FileGlob, load_config


class EnsureFile(NamedTuple):
    src: Path
    target_dir: Path

    def ensure(self):
        target = self.target_dir / self.src.name
        if not target.exists():
            self.target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(self.src, target)


EnsureFile(Path("tests/config.json"), Path("data/")).ensure()
EnsureFile(Path("tests/cryptoduck.json"), Path("data/bots/")).ensure()


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
