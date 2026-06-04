#!/usr/bin/env python3
"""Upload benchmark videos to TOS and generate presigned URLs for API use."""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import tos
from tos.exceptions import TosServerError


BUCKET = "arkclaw-tos-2124145136-cn-guangzhou"
BASE_PREFIX = "arkclaw-tos-ci-yemqjzxa0w9t6r1y3a0v-lk0rj/video-highlight-bucket"
ENDPOINT = os.environ["TOS_ENDPOINT"]
REGION = ENDPOINT.split(".", 1)[0].replace("tos-", "")
AK = os.environ["TOS_ACCESS_KEY"]
SK = os.environ["TOS_SECRET_KEY"]

BENCHMARK_DIR = Path(__file__).resolve().parent.parent / "evaluation" / "test_cases" / "benchmark"


def get_tos_client() -> tos.TosClientV2:
    return tos.TosClientV2(AK, SK, ENDPOINT, REGION)


def tos_key_for_case(case_id: str) -> str:
    return f"{BASE_PREFIX}/videos/{case_id}.mp4"


def presigned_url(key: str, expires: int = 7200) -> str:
    client = get_tos_client()
    return client.pre_signed_url(BUCKET, key, expires=expires)


def file_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    client = get_tos_client()
    uploaded = 0
    skipped = 0

    for case_dir in sorted(BENCHMARK_DIR.glob("case_bm_*")):
        video_path = case_dir / "video.mp4"
        if not video_path.exists() or video_path.stat().st_size == 0:
            print(f"[SKIP] {case_dir.name}: empty or missing")
            continue

        key = tos_key_for_case(case_dir.name)
        try:
            existing = client.head_object(BUCKET, key)
            remote_size = int(existing.headers.get("Content-Length", 0))
            local_size = video_path.stat().st_size
            if remote_size == local_size:
                print(f"[SKIP] {case_dir.name}: already uploaded ({local_size / 1e6:.1f}MB)")
                skipped += 1
                continue
            print(f"[REPLACE] {case_dir.name}: size mismatch ({remote_size} -> {local_size})")
        except TosServerError:
            pass  # not uploaded yet

        client.put_object_from_file(BUCKET, key, str(video_path))
        print(f"[OK] {case_dir.name}: uploaded ({video_path.stat().st_size / 1e6:.1f}MB)")
        uploaded += 1

    print(f"\nDone: {uploaded} uploaded, {skipped} skipped")


if __name__ == "__main__":
    main()
