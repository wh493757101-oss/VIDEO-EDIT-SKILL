"""Shared TOS presigned-URL helper — no base64, no compression, no upload per call."""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

BUCKET = "arkclaw-tos-2124145136-cn-guangzhou"
BASE_PREFIX = "arkclaw-tos-ci-yemqjzxa0w9t6r1y3a0v-lk0rj/video-highlight-bucket"


def _get_tos_client():
    import tos

    endpoint = os.environ["TOS_ENDPOINT"]
    region = endpoint.split(".", 1)[0].replace("tos-", "")
    return tos.TosClientV2(
        os.environ["TOS_ACCESS_KEY"],
        os.environ["TOS_SECRET_KEY"],
        endpoint,
        region,
    )


def ensure_tos_url(local_path: str) -> str:
    """确保视频在 TOS 上，返回签名 URL。已存在且大小匹配则跳过上传。"""
    path = Path(local_path)
    key = f"{BASE_PREFIX}/videos/{path.name}"

    client = _get_tos_client()
    try:
        existing = client.head_object(BUCKET, key)
        remote_size = int(existing.headers.get("Content-Length", 0))
        if remote_size == path.stat().st_size:
            logger.info("TOS 视频已存在: %s (%d bytes)", key, remote_size)
        else:
            logger.info("TOS 视频大小不匹配，重新上传: %s", key)
            client.put_object_from_file(BUCKET, key, local_path)
    except Exception:
        logger.info("上传视频到 TOS: %s -> %s", local_path, key)
        client.put_object_from_file(BUCKET, key, local_path)

    url = client.pre_signed_url(BUCKET, key, expires=7200)
    return url


def ensure_tos_video_path(local_path: str) -> str:
    """如果 TOS 已配置，上传并返回签名 URL；否则返回本地路径（base64 回退）。"""
    if os.environ.get("TOS_ACCESS_KEY") and os.environ.get("TOS_ENDPOINT"):
        try:
            return ensure_tos_url(local_path)
        except Exception as e:
            logger.warning("TOS 上传失败，回退到本地文件: %s", e)
    return local_path
