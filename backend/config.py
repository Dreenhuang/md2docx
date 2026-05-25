import json
import os

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'default_config.json')
USER_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'user_config.json')

DEFAULT_CONFIG = {
    "paper_size": "A4",
    "orientation": "portrait",
    "margin_left": 20,
    "margin_right": 20,
    "margin_top": 16,
    "margin_bottom": 16,
    "font_family": "微软雅黑",
    "font_size_body": "小四(12pt)",
    "line_spacing": 16,
    "first_line_indent": 2,
    "enable_header": True,
    "enable_footer": True,
}


class ConfigManager:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._config = dict(DEFAULT_CONFIG)
        return cls._instance

    @classmethod
    def load_default(cls) -> dict:
        return dict(DEFAULT_CONFIG)

    @classmethod
    def get(cls) -> dict:
        if cls._config is None:
            cls._config = dict(DEFAULT_CONFIG)
        return dict(cls._config)

    @classmethod
    def update(cls, updates: dict) -> dict:
        if cls._config is None:
            cls._config = dict(DEFAULT_CONFIG)
        for key, value in updates.items():
            if key in cls._config:
                cls._config[key] = value
        return dict(cls._config)

    @classmethod
    def reset(cls) -> dict:
        cls._config = dict(DEFAULT_CONFIG)
        return dict(cls._config)

    @classmethod
    def save_user_config(cls) -> bool:
        try:
            os.makedirs(os.path.dirname(USER_CONFIG_PATH), exist_ok=True)
            with open(USER_CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(cls._config, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    @classmethod
    def load_user_config(cls) -> dict:
        if os.path.exists(USER_CONFIG_PATH):
            try:
                with open(USER_CONFIG_PATH, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    cls._config = {**DEFAULT_CONFIG, **loaded}
                    return dict(cls._config)
            except Exception:
                pass
        return dict(cls._config)

    @classmethod
    def validate(cls, config: dict) -> dict:
        validated = dict(DEFAULT_CONFIG)
        for key, value in config.items():
            if key in validated:
                if key.startswith('margin_'):
                    try:
                        v = float(value)
                        validated[key] = max(0, min(100, v))
                    except (ValueError, TypeError):
                        pass
                elif key == 'line_spacing':
                    try:
                        v = float(value)
                        validated[key] = max(6, min(48, v))
                    except (ValueError, TypeError):
                        pass
                elif key == 'first_line_indent':
                    try:
                        v = int(value)
                        validated[key] = max(0, min(10, v))
                    except (ValueError, TypeError):
                        pass
                elif key in ('enable_header', 'enable_footer'):
                    validated[key] = bool(value)
                else:
                    validated[key] = value
        return validated
