#!/usr/bin/env python3
"""Video highlight annotation tool.

Usage:
    python scripts/annotate.py video.mp4
    python scripts/annotate.py video.mp4 -o ground_truth.json

Controls:
    Space       Play / Pause
    S           Mark segment START
    E           Mark segment END (saves segment)
    A / D       Seek backward / forward 5s
    Z / C       Seek backward / forward 1s (fine)
    W / ↑↓       Speed up / down
    R           Reset current start marker
    X           Delete last segment
    Q / Esc     Quit and save
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2


def fmt_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:06.3f}"


@dataclass
class State:
    segments: list[dict]
    current_start: float | None = None
    paused: bool = False
    speed: float = 1.0
    current_time: float = 0.0
    current_frame: int = 0
    duration: float = 0.0
    total_frames: int = 0
    fps: float = 30.0
    message: str = ""
    message_until: float = 0.0
    flash_color: tuple[int, int, int] | None = None
    flash_until: float = 0.0
    last_frame: object = None


def load_existing(path: Path) -> list[dict]:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("highlights", [])
        except (json.JSONDecodeError, KeyError):
            return []
    return []


def seek(cap: cv2.VideoCapture, target_sec: float) -> None:
    """Seek to target_sec, clamped to valid range."""
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    target_frame = max(0, min(total - 1, int(target_sec * fps)))
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)


def draw_ui(state: State):
    """Draw overlay on last_frame and return annotated image."""
    frame = state.last_frame
    if frame is None:
        return None

    h, w = frame.shape[:2]
    out = frame.copy()

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.45, min(0.7, w / 1920))
    thick = max(1, int(font_scale * 2))

    white = (240, 240, 240)
    green = (100, 255, 100)
    yellow = (255, 255, 100)
    red = (100, 100, 255)
    gray = (180, 180, 180)
    dark = (30, 30, 30)

    # ── Top bar (flash color on keypress) ──
    bar_h = int(44 * font_scale * 1.2)
    bar_color = dark
    if state.flash_color and time.time() < state.flash_until:
        bar_color = state.flash_color
    cv2.rectangle(out, (0, 0), (w, bar_h), bar_color, -1)
    cv2.line(out, (0, bar_h), (w, bar_h), (60, 60, 60), 1)

    left_x = int(8 * font_scale)
    y1 = int(26 * font_scale)

    # current time / total
    time_s = f"{fmt_time(state.current_time)} / {fmt_time(state.duration)}"
    cv2.putText(out, time_s, (left_x, y1), font, font_scale, white, thick)

    # frame count
    frame_s = f"|  Frame: {state.current_frame}/{state.total_frames}"
    tx = left_x + cv2.getTextSize(time_s, font, font_scale, thick)[0][0] + 12
    cv2.putText(out, frame_s, (tx, y1), font, font_scale, gray, thick)

    # speed
    speed_s = f"|  {state.speed:.1f}x"
    tx2 = tx + cv2.getTextSize(frame_s, font, font_scale, thick)[0][0] + 12
    cv2.putText(out, speed_s, (tx2, y1), font, font_scale, gray, thick)

    # status (right side) — large + colored circle dot
    if state.current_start is not None:
        status = "REC"
        status_color = (70, 70, 255)  # bright red
    elif state.paused:
        status = "PAUSE"
        status_color = (80, 200, 200)  # yellow-cyan
    else:
        status = "PLAY"
        status_color = green

    status_scale = font_scale * 1.3
    (sw, sh), sb = cv2.getTextSize(status, font, status_scale, thick + 1)
    status_x = w - sw - int(14 * font_scale)
    # colored dot before status
    dot_r = int(5 * font_scale)
    dot_x = status_x - dot_r - int(6 * font_scale)
    dot_y = y1 - int(4 * font_scale)
    cv2.circle(out, (dot_x, dot_y), dot_r, status_color, -1)
    cv2.putText(out, status, (status_x, y1), font, status_scale, status_color, thick + 1)

    # ── Segment list (upper-right, below top bar) ──
    seg_x = w - int(320 * font_scale)
    seg_y = bar_h + int(22 * font_scale)
    cv2.putText(out, "Segments:", (seg_x, seg_y), font, font_scale * 0.85, yellow, thick)

    visible = min(len(state.segments), 10)
    for i in range(visible):
        idx = len(state.segments) - visible + i
        seg = state.segments[idx]
        dur = seg["end_time"] - seg["start_time"]
        color = white if idx >= len(state.segments) - 1 else gray
        txt = f"#{idx + 1}  {fmt_time(seg['start_time'])} -> {fmt_time(seg['end_time'])}  [{dur:.1f}s]"
        row_y = seg_y + (i + 1) * int(20 * font_scale)
        cv2.putText(out, txt, (seg_x, row_y), font, font_scale * 0.6, color, max(1, thick - 1))

    # ── Current start marker indicator ──
    if state.current_start is not None:
        marker_s = f">>> Start: {fmt_time(state.current_start)} <<<"
        (mw, _), _ = cv2.getTextSize(marker_s, font, font_scale * 0.8, thick)
        marker_y = bar_h + int(40 * font_scale)
        cv2.putText(out, marker_s, ((w - mw) // 2, marker_y), font, font_scale * 0.8, red, thick + 1)

    # ── Message (centered, large, with background) ──
    if state.message and time.time() < state.message_until:
        msg_scale = font_scale * 1.1
        (mw, mh), _ = cv2.getTextSize(state.message, font, msg_scale, thick + 1)
        msg_x = (w - mw) // 2
        msg_y = h // 2 + h // 6
        pad = int(12 * font_scale)
        cv2.rectangle(out, (msg_x - pad, msg_y - mh - pad), (msg_x + mw + pad, msg_y + pad), dark, -1)
        cv2.rectangle(out, (msg_x - pad, msg_y - mh - pad), (msg_x + mw + pad, msg_y + pad), (100, 100, 100), 1)
        cv2.putText(out, state.message, (msg_x, msg_y), font, msg_scale, (200, 255, 200), thick + 1)

    # ── Bottom shortcut bar ──
    bottom_h = int(32 * font_scale)
    cv2.rectangle(out, (0, h - bottom_h), (w, h), dark, -1)
    cv2.line(out, (0, h - bottom_h), (w, h - bottom_h), (60, 60, 60), 1)

    shortcuts = "[S]tart  [E]nd  [Space]Play  [A/D]Seek+-5s  [Z/C]Fine+-1s  [W/↑↓]Speed  [R]Reset  [X]Del  [Q]uit"
    by = h - int(8 * font_scale)
    cv2.putText(out, shortcuts, (int(8 * font_scale), by), font, font_scale * 0.55, gray, max(1, thick - 1))

    # ── Progress bar ──
    if state.duration > 0:
        pb_y = h - bottom_h - 4
        progress = state.current_time / state.duration
        pb_x = int(w * progress)
        cv2.line(out, (0, pb_y), (w, pb_y), (60, 60, 60), 3)
        cv2.line(out, (0, pb_y), (pb_x, pb_y), green, 3)

        # Segment markers on progress bar
        for seg in state.segments:
            sx = int(w * seg["start_time"] / state.duration)
            ex = int(w * seg["end_time"] / state.duration)
            cv2.line(out, (sx, pb_y - 3), (sx, pb_y + 3), yellow, 1)
            cv2.line(out, (ex, pb_y - 3), (ex, pb_y + 3), yellow, 1)

    return out


def show_message(state: State, msg: str, duration: float = 3.0, flash: tuple[int, int, int] | None = None) -> None:
    state.message = msg
    state.message_until = time.time() + duration
    if flash:
        state.flash_color = flash
        state.flash_until = time.time() + 0.4


def main() -> None:
    parser = argparse.ArgumentParser(description="Video highlight annotation tool")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("-o", "--output", help="Output JSON path (default: ground_truth.json next to video)")
    args = parser.parse_args()

    video_path = Path(args.video).resolve()
    if not video_path.exists():
        print(f"[ERROR] Video not found: {video_path}")
        sys.exit(1)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {video_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    output_path = Path(args.output).resolve() if args.output else video_path.parent / "ground_truth.json"

    state = State(
        segments=load_existing(output_path),
        duration=duration,
        total_frames=total_frames,
        fps=fps,
    )

    if state.segments:
        show_message(state, f"Loaded {len(state.segments)} existing segments from {output_path.name}", 3.0)

    cv2.namedWindow("Video Annotation Tool", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Video Annotation Tool", 1280, 720)
    cv2.setWindowProperty("Video Annotation Tool", cv2.WND_PROP_TOPMOST, 1)
    print("[INFO] Click on the video window to enable keyboard controls")
    print("[INFO] S=Start  E=End  Space=Play/Pause  A/D=Seek  Q=Quit")

    # Arrow key constants (Windows)
    UP = 2490368
    DOWN = 2621440
    LEFT = 2424832
    RIGHT = 2555904

    frame_interval = 1.0 / fps  # seconds per frame at 1x
    last_frame_time = time.time()

    while True:
        now = time.time()

        # Advance frame based on playback speed, not waitKey timing
        if not state.paused and (now - last_frame_time) >= frame_interval / state.speed:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
                if not ret:
                    break
            state.current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            state.current_time = state.current_frame / fps
            state.last_frame = frame
            last_frame_time = now

        # Always show current frame
        if state.last_frame is not None:
            display = draw_ui(state)
            if display is not None:
                cv2.imshow("Video Annotation Tool", display)

        # Short fixed delay — key scanning always responsive (~100 polls/sec)
        raw_key = cv2.waitKey(10)
        # waitKey may not return extended keys on Windows; try waitKeyEx as fallback
        if raw_key == -1:
            raw_key = cv2.waitKeyEx(1)
        if raw_key == -1:
            continue

        # ── ASCII keys ──
        if raw_key == 27 or raw_key == ord("q"):
            break
        elif raw_key == ord(" "):
            state.paused = not state.paused
        elif raw_key == ord("s"):
            state.current_start = state.current_time
            show_message(state, f"Start: {fmt_time(state.current_time)}", flash=(0, 200, 200))
        elif raw_key == ord("e"):
            if state.current_start is not None and state.current_time > state.current_start:
                seg = {
                    "start_time": round(state.current_start, 3),
                    "end_time": round(state.current_time, 3),
                    "label": "",
                    "score": 1.0,
                }
                state.segments.append(seg)
                dur = state.current_time - state.current_start
                show_message(state, f"Saved #{len(state.segments)} [{dur:.1f}s]", flash=(0, 220, 0))
                state.current_start = None
            elif state.current_start is not None:
                show_message(state, "End time must be after start time", flash=(60, 60, 255))
        elif raw_key == ord("r"):
            if state.current_start is not None:
                show_message(state, f"Cleared start ({fmt_time(state.current_start)})", flash=(120, 80, 200))
                state.current_start = None
        elif raw_key == ord("a"):
            seek(cap, state.current_time - 5.0)
            state.current_time = max(0, state.current_time - 5.0)
            state.paused = False
        elif raw_key == ord("d"):
            seek(cap, state.current_time + 5.0)
            state.current_time = min(duration, state.current_time + 5.0)
            state.paused = False
        elif raw_key == ord("z"):
            seek(cap, state.current_time - 1.0)
            state.current_time = max(0, state.current_time - 1.0)
            state.paused = False
        elif raw_key == ord("c"):
            seek(cap, state.current_time + 1.0)
            state.current_time = min(duration, state.current_time + 1.0)
            state.paused = False
        elif raw_key == ord("x"):
            if state.segments:
                removed = state.segments.pop()
                show_message(state, f"Deleted #{len(state.segments) + 1}", flash=(60, 60, 255))
        elif raw_key == ord("w"):
            state.speed = min(8.0, state.speed * 1.5)
            show_message(state, f"Speed: {state.speed:.1f}x")
        # ── Arrow keys ──
        elif raw_key == UP:
            state.speed = min(8.0, state.speed * 1.5)
            show_message(state, f"Speed: {state.speed:.1f}x")
        elif raw_key == DOWN:
            state.speed = max(0.25, state.speed / 1.5)
            show_message(state, f"Speed: {state.speed:.1f}x")
        elif raw_key == LEFT:
            seek(cap, state.current_time - 5.0)
            state.current_time = max(0, state.current_time - 5.0)
            state.paused = False
        elif raw_key == RIGHT:
            seek(cap, state.current_time + 5.0)
            state.current_time = min(duration, state.current_time + 5.0)
            state.paused = False

    # ── Save ──
    output = {"highlights": state.segments}
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Saved {len(state.segments)} segments to {output_path}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
