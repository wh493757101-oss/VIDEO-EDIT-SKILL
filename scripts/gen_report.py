#!/usr/bin/env python3
"""Generate comprehensive report.txt from report.json per EVALUATION_PLAN spec."""
from __future__ import annotations

import json
import sys

REPORT_JSON = "evaluation/results/benchmark_20260604_final/all/report.json"
REPORT_TXT = "evaluation/results/benchmark_20260604_final/all/report.txt"


def main() -> None:
    data = json.load(open(REPORT_JSON, encoding="utf-8"))
    e = data["iou_eval"]
    seg = data.get("segment_judge", {})
    vid = data.get("video_judge", {})
    ws = data.get("weighted_score", {})

    lines = []
    sep = "=" * 70
    sub = "-" * 70

    lines.append(sep)
    lines.append("视频高光剪辑 — 完整评测报告")
    lines.append(sep)
    lines.append("")

    # ── 一、tIoU 量化评测 ──
    lines.append("## 一、时间戳 IoU 评测")
    lines.append("")
    lines.append(f"  整体 IoU:       {e['overall_iou']:.3f}")
    lines.append(f"  整体 Precision: {e['overall_precision']:.3f} (宏平均)")
    lines.append(f"  整体 Recall:    {e['overall_recall']:.3f} (宏平均)")
    lines.append(f"  整体 F1:        {e['overall_f1']:.3f} (宏平均)")
    lines.append(f"  微平均 Precision: {e['overall_micro_precision']:.3f}")
    lines.append(f"  微平均 Recall:    {e['overall_micro_recall']:.3f}")
    lines.append(f"  微平均 F1:        {e['overall_micro_f1']:.3f}")
    lines.append(f"  Hit Rate @1:    {e['overall_hit_rate_1']:.3f}")
    lines.append(f"  Hit Rate @3:    {e['overall_hit_rate_3']:.3f}")
    lines.append(f"  MAE (时间偏差): {e['overall_mae']:.2f}s")
    lines.append(f"  片段数偏差率:   {e['overall_segment_count_deviation']:.2f}")
    lines.append(f"  集锦时长占比:   {e['overall_total_duration_ratio']:.1%}")
    lines.append(f"  指令时长契合度: {e['overall_instruction_duration_fit']:.2f}")
    lines.append("")
    lines.append("  多 IoU 阈值 mAP (QVHighlights 标准):")
    lines.append(f"    mAP@0.5:  {e['overall_map_50']:.3f}")
    lines.append(f"    mAP@0.75: {e['overall_map_75']:.3f}")
    lines.append(f"    Avg mAP:  {e['overall_avg_map']:.3f}")
    lines.append("")
    lines.append("  排序相关性 (TVSum 标准):")
    kt = e.get("overall_kendall_tau")
    sr = e.get("overall_spearman_rho")
    lines.append(f"    Kendall's tau:  {kt:.3f}" if kt is not None else "    Kendall's tau:  N/A")
    lines.append(f"    Spearman's rho: {sr:.3f}" if sr is not None else "    Spearman's rho: N/A")
    lines.append("")
    dist = e.get("iou_distribution", {})
    lines.append("  tIoU 分布:")
    lines.append(f"    优秀 (>=0.8): {dist.get('excellent', 0)}")
    lines.append(f"    合格 (>=0.5): {dist.get('qualified', 0)}")
    lines.append(f"    不合格 (<0.5): {dist.get('unqualified', 0)}")
    lines.append("")
    lines.append(f"  异常率:    {e['exception_rate']:.1%} ({e['exception_count']}/{e['total_count']})")
    lines.append("")

    # ── 性能 & 成本 ──
    c = e.get("cost", {})
    lines.append("## 性能 & 成本")
    lines.append("")
    lines.append(f"  总 Token:          {c.get('total_tokens', 0):,}")
    lines.append(f"  Prompt Token:      {c.get('prompt_tokens', 0):,}")
    lines.append(f"  Completion Token:  {c.get('completion_tokens', 0):,}")
    lines.append(f"  API 调用次数:      {c.get('api_calls', 0)}")
    lines.append(f"  API 重试次数:      {c.get('api_retries', 0)}")
    lines.append(f"  视频总时长:        {c.get('video_duration', 0):.1f}s")
    lines.append(f"  Token/分钟:        {c.get('tokens_per_minute', 0):,.0f}")
    lines.append(f"  总处理耗时:        {c.get('total_elapsed', 0):.1f}s")
    lines.append(f"  平均耗时/case:     {c.get('avg_elapsed', 0):.1f}s")
    lines.append(f"  处理倍速:          {c.get('processing_ratio', 0):.2f}x")
    lines.append("")
    timing = c.get("timing", {})
    lines.append("  阶段耗时 (平均):")
    lines.append(f"    视频获取:        {timing.get('fetch_avg', 0):.1f}s")
    lines.append(f"    高光检测:        {timing.get('detection_avg', 0):.1f}s")
    lines.append(f"    FFmpeg 拼接:     {timing.get('clip_concat_avg', 0):.1f}s")
    lines.append("")
    if c.get("memory_peak_mb", 0) > 0:
        lines.append(f"  内存峰值:          {c['memory_peak_mb']:.1f} MB")
    if c.get("concurrency", 0) > 1:
        lines.append(f"  并发度:            {c['concurrency']}")
        lines.append(f"  并发吞吐量:        {c.get('concurrent_throughput', 0):.2f} case/s")
    lines.append("")

    # ── 分组统计 ──
    for group_name, group_key in [("按视频类型", "by_category"), ("按难度", "by_difficulty"), ("按来源", "by_source")]:
        grp = e.get(group_key, {})
        if grp:
            lines.append(f"  {group_name}:")
            for k, v in grp.items():
                lines.append(f"    {k}: F1={v['f1']:.3f} (n={v['count']})")
            lines.append("")

    # ── 每用例详情表 ──
    cases = e.get("cases", [])
    seg_cases = seg.get("cases", [])
    vid_cases = vid.get("cases", [])

    lines.append("  各用例详情:")
    header = f"  {'ID':<12} {'类型':<8} {'难度':<10} {'来源':<6} {'F1':<8} {'HR@1':<8} {'MAE':<8} {'时长%':<8} {'指令':<8} {'SegJ':<6} {'VidJ':<6}"
    lines.append(header)
    lines.append("  " + "-" * len(header))
    for i, cs in enumerate(cases):
        if cs.get("error"):
            lines.append(f"  {cs['case_id']:<12} {'-':<8} {'-':<10} {'-':<6} [SKIP] {cs['error'][:60]}")
        else:
            sj = seg_cases[i]["average"] if i < len(seg_cases) and not seg_cases[i].get("error") else "-"
            vj = vid_cases[i]["average"] if i < len(vid_cases) and not vid_cases[i].get("error") else "-"
            sj_str = f"{sj:.1f}" if isinstance(sj, (int, float)) else str(sj)
            vj_str = f"{vj:.1f}" if isinstance(vj, (int, float)) else str(vj)
            lines.append(
                f"  {cs['case_id']:<12} {cs['category']:<8} {cs['difficulty']:<10} "
                f"{cs['source_type']:<6} {cs['f1']:<8.3f} {cs['hit_rate_1']:<8.3f} "
                f"{cs['mae']:<8.2f} {cs['total_duration_ratio']:<8.1%} "
                f"{cs['instruction_duration_fit']:<8.2f} {sj_str:<6} {vj_str:<6}"
            )
    lines.append("")

    # ── 二、LLM Judge ──
    lines.append(sub)
    lines.append("## 二、LLM Judge 主观评测")
    lines.append("")

    if seg.get("degraded", True):
        lines.append("### Segment Judge: [降级] 不可用")
    else:
        lines.append("### Segment Judge (片段质量评测)")
        lines.append(f"  内容完整性: {seg.get('content_completeness', 0):.2f} / 10.0")
        lines.append(f"  片段质量:   {seg.get('segment_quality', 0):.2f} / 10.0")
        lines.append(f"  指令契合度: {seg.get('instruction_fit', 0):.2f} / 10.0")
        lines.append(f"  综合均分:   {seg.get('average', 0):.2f} / 10.0")
        lines.append("")
        lines.append("  各用例评价:")
        for i, sc in enumerate(seg_cases):
            if sc.get("error"):
                lines.append(f"    #{i + 1}: [ERROR] {sc['error'][:80]}")
            else:
                lines.append(f"    #{i + 1}: {sc['average']:.1f}/10.0 — {sc.get('comment', '')}")
        lines.append("")

    if vid.get("degraded", True):
        lines.append("### Video Judge: [降级] 不可用")
    else:
        lines.append("### Video Judge (集锦质量评测)")
        lines.append(f"  节奏感:     {vid.get('rhythm', 0):.2f} / 10.0")
        lines.append(f"  转场质量:   {vid.get('transition_quality', 0):.2f} / 10.0")
        lines.append(f"  音画同步:   {vid.get('audiovisual_sync', 0):.2f} / 10.0")
        lines.append(f"  内容完整性: {vid.get('content_completeness', 0):.2f} / 10.0")
        lines.append(f"  指令契合度: {vid.get('instruction_fit', 0):.2f} / 10.0")
        lines.append(f"  综合均分:   {vid.get('average', 0):.2f} / 10.0")
        lines.append("")
        lines.append("  各用例评价:")
        for i, vc in enumerate(vid_cases):
            if vc.get("error"):
                lines.append(f"    #{i + 1}: [ERROR] {vc['error'][:80]}")
            else:
                lines.append(f"    #{i + 1}: {vc['average']:.1f}/10.0 — {vc.get('comment', '')}")
        lines.append("")

    # ── 三、加权总分 ──
    lines.append(sub)
    lines.append("## 三、加权总分")
    lines.append("")
    if ws.get("degraded"):
        lines.append("  状态: LLM Judge 不可用，总分仅基于量化评测")
        lines.append(f"  加权总分: {ws.get('weighted_score', 0):.4f} / 1.0 (纯量化)")
    else:
        eval_part = ws.get('eval_score', 0) * 0.5
        seg_part = ws.get('segment_judge_score', 0) * 0.25
        vid_part = ws.get('video_judge_score', 0) * 0.25
        lines.append(f"  量化评测分 (F1):   {ws.get('eval_score', 0):.4f} x 0.50 = {eval_part:.4f}")
        lines.append(f"  Segment Judge 分:  {ws.get('segment_judge_score', 0):.4f} x 0.25 = {seg_part:.4f}")
        lines.append(f"  Video Judge 分:    {ws.get('video_judge_score', 0):.4f} x 0.25 = {vid_part:.4f}")
        lines.append(f"  {'-' * 42}")
        lines.append(f"  加权总分:          {ws.get('weighted_score', 0):.4f} / 1.0")
    lines.append("")
    lines.append(sep)

    report = "\n".join(lines)
    with open(REPORT_TXT, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)


if __name__ == "__main__":
    main()
