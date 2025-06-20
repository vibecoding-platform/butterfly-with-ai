"""
設定管理のテスト
"""

import tempfile
from pathlib import Path

import pytest

from wrapper.config import WrapperConfig


def test_default_config():
    """デフォルト設定のテスト"""
    config = WrapperConfig()

    assert config.debug is False
    assert config.enable_ai is True
    assert config.ai_service.endpoint == "http://localhost:8000"
    assert config.monitor.buffer_size == 8192
    assert config.session.session_timeout == 3600


def test_config_from_toml():
    """TOML設定ファイルからの読み込みテスト"""
    toml_content = """
debug = true
enable_ai = false

[ai_service]
endpoint = "http://example.com"
timeout = 60

[monitor]
buffer_size = 4096
poll_interval = 0.2
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        f.flush()

        config = WrapperConfig.load_from_file(Path(f.name))

        assert config.debug is True
        assert config.enable_ai is False
        assert config.ai_service.endpoint == "http://example.com"
        assert config.ai_service.timeout == 60
        assert config.monitor.buffer_size == 4096
        assert config.monitor.poll_interval == 0.2


def test_environment_overrides():
    """環境変数による設定上書きのテスト"""
    import os

    # 環境変数を設定
    os.environ["AETHERTERM_DEBUG"] = "true"
    os.environ["AETHERTERM_AI_ENDPOINT"] = "http://test.com"
    os.environ["AETHERTERM_ENABLE_AI"] = "false"

    try:
        config = WrapperConfig()
        config.apply_environment_overrides()

        assert config.debug is True
        assert config.enable_ai is False
        assert config.ai_service.endpoint == "http://test.com"

    finally:
        # 環境変数をクリーンアップ
        for key in ["AETHERTERM_DEBUG", "AETHERTERM_AI_ENDPOINT", "AETHERTERM_ENABLE_AI"]:
            os.environ.pop(key, None)


if __name__ == "__main__":
    pytest.main([__file__])
