import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .evaluator import CaseScore, EvalReport, HighlightEvaluator, TestCaseLoader, compute_weighted_score
from .llm_judge import JudgeReport, LLMJudge
from .report import ReportConfig, ReportGenerator

logger = logging.getLogger(__name__)

CATEGORY_HIGHLIGHT_DEFAULTS: dict[str, str] = {
    "体育": "得分瞬间、关键传球、精彩扑救、庆祝时刻、红黄牌",
    "sports": "得分瞬间、关键传球、精彩扑救、庆祝时刻",
    "游戏": "击杀、团战、翻盘、精彩操作、获胜时刻",
    "gaming": "击杀、团战、翻盘、精彩操作、获胜时刻",
    "新闻": "关键人物发言、新闻重点事件、现场画面",
    "news": "关键人物发言、新闻重点事件、现场画面",
    "vlog": "有趣互动、风景特写、情绪高光、转折事件",
    "娱乐": "笑点、才艺展示、高能互动、名场面",
    "entertainment": "笑点、才艺展示、高能互动、名场面",
    "教育": "核心知识点、操作演示、总结要点",
    "education": "核心知识点、操作演示、总结要点",
    "户外": "精彩瞬间、风景亮点、活动高潮",
    "outdoor": "精彩瞬间、风景亮点、活动高潮",
}


@dataclass
class EvalRunConfig:
    test_cases_root: str = ""
    output_dir: str = ""
    iou_threshold: float = 0.5
    skip_llm_judge: bool = False
    skip_edit: bool = False
    case_filter: list[str] = field(default_factory=list)
    judge_weight: float = 0.5
    judge_max_retries: int = 3
    concurrency: int = 1
    concurrency_warmup: int = 0


class EvalRunner:
    def __init__(self, config: EvalRunConfig | None = None):
        self.config = config or EvalRunConfig()

    def run(self) -> tuple[EvalReport, JudgeReport, str]:
        loader = TestCaseLoader(self.config.test_cases_root)
        cases = loader.load_all()

        if self.config.case_filter:
            cases = [c for c in cases if c["case_id"] in self.config.case_filter]

        logger.info("加载 %d 个评测用例", len(cases))
        if not cases:
            return EvalReport(), JudgeReport(), ""

        if self.config.concurrency > 1:
            results = self._run_concurrent(cases)
        else:
            results: list[dict[str, Any]] = []
            for case in cases:
                logger.info("运行 case: %s", case["case_id"])
                result = self._run_case(case)
                results.append(result)

        # 并行执行量化评测和 LLM Judge
        evaluator = HighlightEvaluator(iou_threshold=self.config.iou_threshold)
        judge_report = JudgeReport()

        if self.config.skip_llm_judge:
            eval_report = evaluator.evaluate_all(results)
            judge_report.degraded = True
        else:
            with ThreadPoolExecutor(max_workers=2) as executor:
                eval_future = executor.submit(evaluator.evaluate_all, results)

                def _run_judge():
                    judge = LLMJudge()
                    judge_cases = self._build_judge_cases(results)
                    if judge_cases:
                        return judge.judge_all(judge_cases, max_retries=self.config.judge_max_retries)
                    jr = JudgeReport()
                    jr.degraded = True
                    return jr

                judge_future = executor.submit(_run_judge)
                eval_report = eval_future.result()
                judge_report = judge_future.result()

        # 计算加权总分
        weighted = compute_weighted_score(
            eval_report, judge_report,
            weight_eval=1.0 - self.config.judge_weight,
            weight_judge=self.config.judge_weight,
        )

        # 保存每 case 独立报告
        if self.config.output_dir:
            self._save_per_case_reports(eval_report, Path(self.config.output_dir))
            # 汇总报告保存到 all/ 子目录
            all_dir = Path(self.config.output_dir) / "all"
            all_dir.mkdir(parents=True, exist_ok=True)
            report_gen = ReportGenerator(
                ReportConfig(output_dir=str(all_dir), save_json=True)
            )
        else:
            report_gen = ReportGenerator(ReportConfig())

        report_text = report_gen.generate(eval_report, judge_report, weighted)
        return eval_report, judge_report, report_text

    def _save_per_case_reports(self, eval_report: EvalReport, out_root: Path) -> None:
        """为每个 case 生成独立 report.json 和 report.txt。"""
        for score in eval_report.scores:
            case_dir = out_root / score.case_id
            case_dir.mkdir(parents=True, exist_ok=True)
            per_case = {
                "case_id": score.case_id,
                "category": score.category,
                "difficulty": score.difficulty,
                "source_type": score.source_type,
                "precision": round(score.precision, 3),
                "recall": round(score.recall, 3),
                "f1": round(score.f1, 3),
                "hit_rate_1": round(score.hit_rate_1, 3),
                "hit_rate_3": round(score.hit_rate_3, 3),
                "mae": round(score.mae, 2),
                "segment_count_deviation": round(score.segment_count_deviation, 2),
                "total_duration_ratio": round(score.total_duration_ratio, 3),
                "instruction_duration_fit": round(score.instruction_duration_fit, 2),
                "map_50": round(score.map_50, 3),
                "map_75": round(score.map_75, 3),
                "avg_map": round(score.avg_map, 3),
                "kendall_tau": round(score.kendall_tau, 3) if score.kendall_tau is not None else None,
                "spearman_rho": round(score.spearman_rho, 3) if score.spearman_rho is not None else None,
                "iou_distribution": score.iou_distribution,
                "error": score.error,
            }
            (case_dir / "report.json").write_text(
                json.dumps(per_case, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            lines = [
                f"case_id: {score.case_id}",
                f"category: {score.category}",
                f"difficulty: {score.difficulty}",
                f"source_type: {score.source_type}",
            ]
            if score.error:
                lines.append(f"error: {score.error}")
            else:
                lines += [
                    f"precision: {score.precision:.3f}",
                    f"recall: {score.recall:.3f}",
                    f"f1: {score.f1:.3f}",
                    f"hit_rate_1: {score.hit_rate_1:.3f}",
                    f"hit_rate_3: {score.hit_rate_3:.3f}",
                    f"mae: {score.mae:.2f}s",
                    f"segment_count_deviation: {score.segment_count_deviation:.2f}",
                    f"total_duration_ratio: {score.total_duration_ratio:.1%}",
                    f"instruction_duration_fit: {score.instruction_duration_fit:.2f}",
                    f"map_50: {score.map_50:.3f}",
                    f"map_75: {score.map_75:.3f}",
                    f"avg_map: {score.avg_map:.3f}",
                ]
            (case_dir / "report.txt").write_text("\n".join(lines), encoding="utf-8")

    def _run_case(self, case: dict[str, Any]) -> dict[str, Any]:
        import tracemalloc

        from src.main import PipelineConfig, VideoHighlightPipeline
        from src.video_editor import EditorConfig
        from src.video_fetcher import LocalFileSource, TosSource, UrlSource

        source_type = case.get("source_type", "local")
        instruction = case.get("instruction", {})
        description = instruction.get("prompt", "")

        editor_config = EditorConfig(keep_clips=True)
        pipeline = VideoHighlightPipeline(
            PipelineConfig(output_dir=self.config.output_dir, editor=editor_config)
        )

        if source_type == "tos":
            tos_path = case.get("tos_path", "")
            source = TosSource(tos_path)
        elif source_type == "remote":
            source_url = case.get("source_url", "")
            source = UrlSource(source_url)
        else:
            video_path = case.get("video_path", "")
            source = LocalFileSource(video_path)

        tracemalloc.start()
        result = pipeline.run(
            source,
            description=description,
            skip_edit=self.config.skip_edit,
        )
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        predicted: list[dict[str, Any]] = []
        judge_segments: list[dict[str, Any]] = []
        if result.edit and result.edit.segments:
            predicted = [
                {
                    "start_time": seg["start_time"],
                    "end_time": seg["end_time"],
                    "score": seg.get("score", 0.5),
                }
                for seg in result.edit.segments
            ]
            judge_segments = [
                {
                    "start_time": seg["start_time"],
                    "end_time": seg["end_time"],
                    "score": seg.get("score", 0.5),
                    "label": seg.get("label", ""),
                    "clip_url": seg.get("clip_path", seg.get("clip_url", "")),
                }
                for seg in result.edit.segments
            ]

        # 收集 token 用量
        pipeline.detector  # ensure initialized
        detector = pipeline._detector
        api_calls = detector.call_count if detector else 0
        api_retries = detector.retry_count if detector else 0
        detection_usage = result.detection_usage.to_dict()
        judge_usage = result.judge_usage.to_dict()

        # 收集阶段耗时
        timing = result.timing.to_dict() if result.timing else {}

        return {
            "case_id": case["case_id"],
            "category": case["category"],
            "difficulty": case["difficulty"],
            "source_type": case["source_type"],
            "instruction": instruction,
            "predicted": predicted,
            "ground_truth": case["ground_truth"],
            "target": description,
            "style": instruction.get("style", ""),
            "core_highlight_definition": instruction.get("core_highlight_definition", ""),
            "detection_usage": detection_usage,
            "judge_usage": judge_usage,
            "video_duration": result.metadata.duration,
            "elapsed_time": result.elapsed_time,
            "api_calls": api_calls,
            "api_retries": api_retries,
            "memory_peak_mb": peak_bytes / (1024 * 1024),
            "memory_avg_mb": 0.0,
            "edit_output_path": result.edit.output_path if result.edit else "",
            "judge_segments": judge_segments,
            "timing": timing,
            "pipeline_error": result.error,
        }

    def _run_concurrent(self, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """并发压测模式：多线程并行执行 case，测量吞吐量。"""
        n = len(cases)
        concurrency = self.config.concurrency
        warmup = self.config.concurrency_warmup

        logger.info("并发压测: %d cases, 并发度=%d, 预热=%d", n, concurrency, warmup)

        results: list[dict[str, Any]] = []
        t0 = time.perf_counter()

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_map = {
                executor.submit(self._run_case, case): case
                for case in cases
            }
            for future in as_completed(future_map):
                try:
                    results.append(future.result())
                except Exception as e:
                    case = future_map[future]
                    logger.error("并发 case %s 异常: %s", case["case_id"], e)
                    results.append({
                        "case_id": case["case_id"],
                        "category": case.get("category", ""),
                        "difficulty": case.get("difficulty", ""),
                        "source_type": case.get("source_type", "local"),
                        "predicted": [],
                        "ground_truth": case.get("ground_truth", []),
                        "target": "",
                        "style": "",
                        "error": str(e),
                    })

        elapsed = time.perf_counter() - t0
        effective = n - warmup
        throughput = effective / elapsed if elapsed > 0 else 0.0

        # 将吞吐量数据注入到每个 result 中，便于 CostStats 汇总
        for r in results:
            r["concurrency"] = concurrency
            r["concurrent_total_elapsed"] = elapsed
            r["concurrent_throughput"] = throughput

        logger.info(
            "并发压测完成: 总耗时=%.1fs, 有效 case=%d, 吞吐量=%.2f case/s (并发度=%d)",
            elapsed, effective, throughput, concurrency,
        )

        return results

    def _default_highlight_definition(self, category: str) -> str:
        return CATEGORY_HIGHLIGHT_DEFAULTS.get(
            category, "视频中最重要的高光时刻和关键场景"
        )

    def _build_judge_cases(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        judge_cases: list[dict[str, Any]] = []
        for r in results:
            if not r.get("predicted"):
                continue
            category = r.get("category", "")
            core_def = r.get("core_highlight_definition", "") or self._default_highlight_definition(category)
            judge_cases.append({
                "category": category,
                "target": r.get("target", ""),
                "style": r.get("style", ""),
                "core_highlight_definition": core_def,
                "segments": r.get("judge_segments", r["predicted"]),
                "video_path": r.get("edit_output_path", ""),
            })
        return judge_cases
