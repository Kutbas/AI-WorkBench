"""腾讯云 COS v5 图床上传。

cos-python-sdk-v5 是同步 SDK，FastAPI 异步上下文里用 asyncio.to_thread 包装，避免阻塞事件循环。
"""

from __future__ import annotations

import asyncio

from qcloud_cos import CosConfig, CosS3Client


class CosUploadError(RuntimeError):
    pass


def _build_client(cfg: dict) -> CosS3Client:
    secret_id = (cfg.get("secret_id") or "").strip()
    secret_key = (cfg.get("secret_key") or "").strip()
    bucket = (cfg.get("bucket") or "").strip()
    region = (cfg.get("region") or "").strip()
    if not (secret_id and secret_key and bucket and region):
        raise CosUploadError("COS 配置不完整（secret_id/secret_key/bucket/region）")
    conf = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=None, Scheme="https")
    return CosS3Client(conf)


def cos_url(cfg: dict, key: str) -> str:
    """对象的公网访问 URL：https://{bucket}.cos.{region}.myqcloud.com/{key}"""
    return f"https://{cfg['bucket'].strip()}.cos.{cfg['region'].strip()}.myqcloud.com/{key.lstrip('/')}"


def _fmt_cos_error(e: Exception) -> str:
    """CosServiceError 的 str() 是整个响应头 dict，提取错误码/信息更可读。"""
    code = getattr(e, "get_error_code", None)
    if callable(code):
        return f"{code()} {getattr(e, 'get_error_msg', lambda: '')()}"
    return str(e)[:300]


def _put_sync(cfg: dict, key: str, body: bytes) -> str:
    client = _build_client(cfg)
    try:
        client.put_object(Bucket=cfg["bucket"].strip(), Key=key.lstrip("/"), Body=body)
    except CosUploadError:
        raise
    except Exception as e:  # SDK 抛的异常类型繁杂，统一收敛
        raise CosUploadError(f"COS 上传失败: {_fmt_cos_error(e)}") from e
    return cos_url(cfg, key)


async def upload(cfg: dict, key: str, body: bytes) -> str:
    """上传字节到 COS，返回对象 URL。"""
    return await asyncio.to_thread(_put_sync, cfg, key, body)


def _test_sync(cfg: dict) -> str:
    """连通性测试：向目标前缀 put 一个探测对象再删除。

    不用 head_bucket——图床密钥常是子账号、仅授权特定前缀，head_bucket 会被拒但写入正常。
    """
    client = _build_client(cfg)
    bucket = cfg["bucket"].strip()
    prefix = cfg.get("prefix", "").strip().strip("/")
    key = f"{prefix}/.conn_test" if prefix else ".conn_test"
    try:
        client.put_object(Bucket=bucket, Key=key, Body=b"ai-workbench connectivity test")
        client.delete_object(Bucket=bucket, Key=key)
    except Exception as e:
        raise CosUploadError(f"COS 连接失败: {_fmt_cos_error(e)}") from e
    return f"bucket {bucket} 前缀 {prefix or '/'} 可读写"


async def test_connection(cfg: dict) -> str:
    return await asyncio.to_thread(_test_sync, cfg)
