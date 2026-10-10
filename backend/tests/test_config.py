"""Configuration regression tests use dummy credentials only; no model calls."""
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import config


@pytest.fixture
def config_env(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    config.get_settings.cache_clear()
    app_dir = tmp_path / "backend" / "app"
    app_dir.mkdir(parents=True)
    monkeypatch.setattr(config, "__file__", str(app_dir / "config.py"))
    yield tmp_path
    config.get_settings.cache_clear()


def test_loads_backend_dotenv_independently_of_cwd(config_env, monkeypatch):
    (config_env / ".env").write_text("GEMINI_API_KEY=dummy-wrong-location\n")
    (config_env / "backend" / ".env").write_text("GEMINI_API_KEY=dummy-backend-key\n")
    monkeypatch.chdir(config_env)
    config._load_dotenv_once()
    assert config.os.environ["GEMINI_API_KEY"] == "dummy-backend-key"
    assert config.get_settings().gemini_api_key == "dummy-backend-key"


def test_existing_process_environment_takes_precedence(config_env, monkeypatch):
    (config_env / "backend" / ".env").write_text("GEMINI_API_KEY=dummy-file-key\n")
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-process-key")
    config._load_dotenv_once()
    assert config.get_settings().gemini_api_key == "dummy-process-key"


def test_missing_dotenv_does_not_supply_a_key(config_env):
    config._load_dotenv_once()
    assert config.get_settings().gemini_api_key is None


def test_cached_settings_require_refresh_after_environment_changes(config_env, monkeypatch):
    assert config.get_settings().gemini_api_key is None
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-later-key")
    assert config.get_settings().gemini_api_key is None
    config.get_settings.cache_clear()
    assert config.get_settings().gemini_api_key == "dummy-later-key"


def test_gemini_factory_receives_loaded_key(config_env, monkeypatch):
    (config_env / "backend" / ".env").write_text("GEMINI_API_KEY=dummy-factory-key\n")
    config._load_dotenv_once()
    received = {}
    sentinel = object()

    def fake_gemini_model(**kwargs):
        received.update(kwargs)
        return sentinel

    monkeypatch.setitem(sys.modules, "strands.models.gemini", SimpleNamespace(GeminiModel=fake_gemini_model))
    assert config.get_model("fast") is sentinel
    assert received["client_args"]["api_key"] == "dummy-factory-key"


def test_import_loads_dotenv_before_first_settings_call(tmp_path, monkeypatch):
    source = Path(config.__file__).read_text()
    app_dir = tmp_path / "backend" / "app"
    app_dir.mkdir(parents=True)
    copied_config = app_dir / "config.py"
    copied_config.write_text(source)
    (tmp_path / "backend" / ".env").write_text("GEMINI_API_KEY=dummy-import-key\n")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    namespace = runpy.run_path(str(copied_config))
    get_settings = namespace["get_settings"]
    assert get_settings.cache_info().currsize == 0
    assert get_settings().gemini_api_key == "dummy-import-key"
