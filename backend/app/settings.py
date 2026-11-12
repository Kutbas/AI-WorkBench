"""配置管理。

优先级：data/config.json（运行时权威，设置页修改的就是它）> 环境变量（首次种子）> 内置默认。
真实密钥只存在于本机/服务器的 .env 与 data/config.json，两者均不入库。
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR") or (Path(__file__).resolve().parent.parent.parent / "data")).resolve()
CONFIG_PATH = DATA_DIR / "config.json"

# 占位默认：不含任何真实密钥（真实值经 .env 种子写入 config.json）
DEFAULTS: dict = {
    "dmxapi": {
        "base_url": "https://www.dmxapi.cn",
        "api_key": "",
    },
    "imagegen": {
        "model": "gpt-image-2.5-sunburst-ssvip",
        "size": "2048x1152",  # 2K 横版 16:9
        "quality": "high",
        "n": 1,
        "output_format": "png",
        "moderation": "low",
        "background": "auto",
    },
    "cos": {
        "secret_id": "",
        "secret_key": "",
        "bucket": "",  # 形如 graphbed-1331926955（含 AppId 后缀）
        "region": "ap-shanghai",
        "prefix": "GraphBed/",
    },
    "access_token": "",
}

# 环境变量 → 配置路径（仅在该项当前为空时作为种子写入）
_ENV_MAP: dict[str, tuple[str | None, str]] = {
    "DMXAPI_BASE_URL": ("dmxapi", "base_url"),
    "DMXAPI_API_KEY": ("dmxapi", "api_key"),
    "COS_SECRET_ID": ("cos", "secret_id"),
    "COS_SECRET_KEY": ("cos", "secret_key"),
    "COS_BUCKET": ("cos", "bucket"),
    "COS_REGION": ("cos", "region"),
    "COS_PREFIX": ("cos", "prefix"),
    "ACCESS_TOKEN": (None, "access_token"),
}

_config: dict = {}


def _deep_merge(base: dict, override: dict) -> dict:
    """override 并入 base（override 优先），返回新 dict；只递归两边都是 dict 的键。"""
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load_config() -> dict:
    """加载配置：读 config.json（与默认值深合并补全新字段）；不存在则用默认+env 种子新建。"""
    global _config
    if CONFIG_PATH.is_file():
        stored = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        _config = _deep_merge(DEFAULTS, stored)
    else:
        _config = copy.deepcopy(DEFAULTS)
        seeded = False
        for env_name, (section, key) in _ENV_MAP.items():
            env_val = os.environ.get(env_name, "").strip()
            if not env_val:
                continue
            if section is None:
                _config[key] = env_val
            else:
                _config[section][key] = env_val
            seeded = True
        _atomic_write(CONFIG_PATH, _config)
        if seeded:
            print(f"[settings] 已从环境变量种子化 {CONFIG_PATH}")
    return get_config()


def get_config() -> dict:
    return copy.deepcopy(_config)


def save_config(updates: dict) -> dict:
    """以 updates 覆盖合并当前配置并原子写盘。"""
    global _config
    _config = _deep_merge(_config, updates)
    _atomic_write(CONFIG_PATH, _config)
    return get_config()
