#!/usr/bin/env python3
"""Run LLM Judge on cached evaluation results — no Pipeline re-run needed."""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    results_dir = Path("evaluation/results/benchmark_20260604_final")
    if not results_dir.exists():
        logger.error("Results dir not found: %s", results_dir)
        sys.exit(1)

    cases = []
    for cache_path in sorted(results_dir.glob("case_bm_*/judge_cache.json")):
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        data["_cache_path"] = str(cache_path)
        cases.append(data)

    if not cases:
        logger.error("No judge_cache.json found")
        sys.exit(1)

    logger.info("加载 %d 个 Judge 候选", len(cases))

    from evaluation.llm_judge import LLMJudge

    judge = LLMJudge()
    judge_report = judge.judge_all(cases, max_retries=2)

    # 保存 Judge 报告
    all_dir = results_dir / "all"
    all_dir.mkdir(parents=True, exist_ok=True)

    from evaluation.llm_judge import format_judge_report
    from evaluation.evaluator import EvalReport, compute_weighted_score

    # 加载已有 tIoU 报告
    iou_path = all_dir / "report.json"
    if iou_path.exists():
        iou_data = json.loads(iou_path.read_text(encoding="utf-8"))
    else:
        iou_data = {}

    # save judge report
    judge_json = {
        "segment_judge": {
            "content_completeness": round(judge_report.segment_content_completeness, 2),
            "segment_quality": round(judge_report.segment_quality, 2),
            "instruction_fit": round(judge_report.segment_instruction_fit, 2),
            "average": round(judge_report.segment_average, 2),
            "degraded": judge_report.segment_degraded,
            "cases": [
                {
                    "content_completeness": s.content_completeness,
                    "segment_quality": s.segment_quality,
                    "instruction_fit": s.instruction_fit,
                    "average": round(s.average, 1),
                    "comment": s.overall_comment,
                    "error": s.error,
                }
                for s in judge_report.segment_scores
            ],
        },
        "video_judge": {
            "rhythm": round(judge_report.video_rhythm, 2),
            "transition_quality": round(judge_report.video_transition_quality, 2),
            "audiovisual_sync": round(judge_report.video_audiovisual_sync, 2),
            "content_completeness": round(judge_report.video_content_completeness, 2),
            "instruction_fit": round(judge_report.video_instruction_fit, 2),
            "average": round(judge_report.video_average, 2),
            "degraded": judge_report.video_degraded,
            "cases": [
                {
                    "rhythm": s.rhythm,
                    "transition_quality": s.transition_quality,
                    "audiovisual_sync": s.audiovisual_sync,
                    "content_completeness": s.content_completeness,
                    "instruction_fit": s.instruction_fit,
                    "average": round(s.average, 1),
                    "comment": s.overall_comment,
                    "error": s.error,
                }
                for s in judge_report.video_scores
            ],
        },
    }
    (all_dir / "judge_report.json").write_text(
        json.dumps(judge_json, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 生成完整报告文本
    txt = format_judge_report(judge_report)

    # 计算加权总分
    eval_f1 = iou_data.get("iou_eval", {}).get("overall_f1", 0.0)
    weighted = compute_weighted_score(
        EvalReport(overall_f1=eval_f1),
        judge_report,
        weight_eval=0.5,
        weight_judge=0.5,
    )
    txt += f"\n\n## 加权总分\n量化 F1={eval_f1:.3f} × 0.5 + Judge × 0.5 = {weighted['weighted_score']:.4f}\n"

    (all_dir / "judge_report.txt").write_text(txt, encoding="utf-8")
    logger.info("Judge 报告已保存: %s", all_dir)

    # 更新每 case 的 report.json，补充 Judge 评分
    for i, case in enumerate(cases):
        cache_path = Path(case["_cache_path"])
        case_dir = cache_path.parent
        per_case_path = case_dir / "report.json"
        if not per_case_path.exists():
            continue
        per_case = json.loads(per_case_path.read_text(encoding="utf-8"))
        if i < len(judge_report.segment_scores):
            ss = judge_report.segment_scores[i]
            per_case["segment_judge"] = {
                "content_completeness": ss.content_completeness,
                "segment_quality": ss.segment_quality,
                "instruction_fit": ss.instruction_fit,
                "average": round(ss.average, 1),
                "comment": ss.overall_comment,
                "error": ss.error,
            }
        if i < len(judge_report.video_scores):
            vs = judge_report.video_scores[i]
            per_case["video_judge"] = {
                "rhythm": vs.rhythm,
                "transition_quality": vs.transition_quality,
                "audiovisual_sync": vs.audiovisual_sync,
                "content_completeness": vs.content_completeness,
                "instruction_fit": vs.instruction_fit,
                "average": round(vs.average, 1),
                "comment": vs.overall_comment,
                "error": vs.error,
            }
        per_case_path.write_text(json.dumps(per_case, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("已更新 %d 个 case 的 Judge 评分", len(cases))

    print(txt)


if __name__ == "__main__":
    main()
