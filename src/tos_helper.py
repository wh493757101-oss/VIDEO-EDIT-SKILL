"""Shared TOS helper — presigned URLs for video, report upload."""
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


def _compute_tos_key(local_path: str) -> str:
    """从本地路径推导 TOS key。匹配 benchmark/ 或 results/ 的相对结构。"""
    path = Path(local_path).resolve()
    path_str = str(path).replace("\\", "/")
    # 尝试匹配 benchmark 结构
    if "/benchmark/" in path_str:
        rel = path_str.split("/benchmark/", 1)[1]
        return f"{BASE_PREFIX}/benchmark/{rel}"
    # 尝试匹配 results 结构（Judge 视频）
    if "/results/" in path_str:
        rel = path_str.split("/results/", 1)[1]
        return f"{BASE_PREFIX}/results/{rel}"
    # 回退：只用文件名
    return f"{BASE_PREFIX}/uploads/{path.name}"


def ensure_tos_url(local_path: str) -> str:
    """确保文件在 TOS 上（已存在则跳过），返回签名 HTTPS URL。"""
    key = _compute_tos_key(local_path)
    client = _get_tos_client()

    try:
        client.head_object(BUCKET, key)
        logger.info("TOS 已存在: %s", key)
    except Exception:
        logger.info("上传到 TOS: %s", key)
        client.put_object_from_file(BUCKET, key, local_path)

    return client.pre_signed_url(BUCKET, key, expires=7200)


def ensure_tos_video_path(local_path: str) -> str:
    """如果 TOS 已配置，返回签名 URL；否则返回本地路径（base64 回退）。"""
    if os.environ.get("TOS_ACCESS_KEY") and os.environ.get("TOS_ENDPOINT"):
        try:
            return ensure_tos_url(local_path)
        except Exception as e:
            logger.warning("TOS 失败，回退本地: %s", e)
    return local_path


def upload_report(local_path: str) -> str:
    """上传报告文件到 TOS，返回 TOS key。"""
    key = _compute_tos_key(local_path)
    client = _get_tos_client()
    client.put_object_from_file(BUCKET, key, local_path)
    logger.info("报告已上传: %s", key)
    return key


def upload_input_video(local_path: str) -> str:
    """上传原始视频到 TOS input/，返回签名 URL。"""
    key = f"{BASE_PREFIX}/input/{Path(local_path).name}"
    client = _get_tos_client()
    client.put_object_from_file(BUCKET, key, local_path)
    logger.info("原始视频已上传: %s", key)
    return client.pre_signed_url(BUCKET, key, expires=7200)


def upload_output_video(local_path: str) -> str:
    """上传集锦视频到 TOS output/，返回签名 URL。"""
    key = f"{BASE_PREFIX}/output/{Path(local_path).name}"
    client = _get_tos_client()
    client.put_object_from_file(BUCKET, key, local_path)
    logger.info("集锦视频已上传: %s", key)
    return client.pre_signed_url(BUCKET, key, expires=7200)


def delete_local_clips(results_dir: str) -> None:
    """删除评测过程中生成的临时视频片段目录，只保留报告。"""
    root = Path(results_dir)
    deleted = 0
    for d in root.glob("video_*"):
        if d.is_dir():
            import shutil
            shutil.rmtree(d)
            deleted += 1
    # 清理孤立的视频/临时文件
    for f in root.glob("*.mp4"):
        f.unlink()
        deleted += 1
    if deleted:
        logger.info("已清理 %d 个临时视频", deleted)
