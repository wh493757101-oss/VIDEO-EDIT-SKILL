# 视频高光剪辑 — 评测方案

> **⚠️ 核心原则：所有量化指标必须由评测代码计算，禁止手动估算、禁止目测、禁止编造。**
>
> 评测流程：
> 1. 先运行 `python -m evaluation.runner`，让 `HighlightEvaluator` 用 tIoU 算法对 predicted vs ground_truth 做贪心匹配，自动算出 Precision/Recall/F1/mAP/Kendall's τ 等全部数值
> 2. 再让 `LLMJudge` 观看实际视频片段做主观评分
> 3. 最后 `compute_weighted_score()` 自动算加权总分
> 4. **你不能跳过代码自己猜 IoU 或 F1 值，必须读取 `report.json` 或 `report.txt` 中的实际计算结果。**

## 一、评测目标

评估多模态大模型 + FFmpeg 视频高光剪辑 Pipeline 的剪辑质量：给定一段长视频 + 自然语言剪辑指令，多模态模型识别的高光片段是否准确、完整、精彩。

评测体系分三层：**tIoU 量化评测**（客观，有 GT 标注）→ **双 LLM Judge**（主观，片段级 + 集锦级）→ **加权融合**。

---

## 二、评测规则（必须严格遵守）

评测时 Runner 必须按以下规则读取每个用例文件，不得省略或自行推断：

**① instruction.json → 剪辑指令**
- 必须读取 `instruction["prompt"]` 作为 Pipeline 的 `description` 参数
- 不要修改、不要摘要、不要翻译
- 指令中已包含场景描述 + 目标时长 + 段数预期，LLM 应严格按此识别高光

**② metadata.yaml → 视频元信息**
- 必须读取 `metadata["duration"]` 作为该用例的视频时长参考
- `metadata["scene_type"]` 在报告分组统计时使用（按类别/难度/来源分组）
- `fps` 和 `resolution` 可能为 null（无法从标注确定），Runner 不要依赖这两个字段
- 实际 fps/resolution 由 ffprobe 在运行时动态检测

**③ ground_truth.json → 评测真值**
- 必须读取 `ground_truth["highlights"]` 作为 tIoU 量化评测的唯一真值
- 每个 highlight 包含 start_time/end_time/label/score，全部字段都要加载
- 即使 `highlights` 为空数组 `[]`，也要正常跑评测（对抗用例预期输出为空）
- 评测时做贪心匹配：每个预测片段找 IoU 最大的未使用 GT，IoU ≥ 0.5 算命中

**④ video.mp4 → 原始视频**
- 通过 `LocalFileSource` 加载，传给 Pipeline
- 视频文件可能为空（0 字节）、文本伪装、PNG 伪装（对抗用例），Pipeline 应能报错而非崩溃

### LLM Judge 规则

- 只有 1 个片段也必须评测，不要因为 predicted segments 数量少就跳过
- Segment Judge 和 Video Judge 并行执行，互不依赖
- 任何一个 Judge 失败不影响另一个，降级策略按权重重新分配
- Judge 看不到 ground_truth，只能看到 predicted segments + 剪辑指令 + 视频

---

## 三、数据流转

```
video.mp4 + instruction.json + ground_truth.json + metadata.yaml
         │
         ▼
   EvalRunner._run_case()
   ├── 读取 instruction["prompt"] → 传给 Pipeline.run() 作为 description
   ├── 读取 metadata["duration"] / scene_type → 用于分组统计和时长校验
   ├── 读取 video.mp4 → LocalFileSource → Pipeline
   ├── Pipeline.run() → 多模态 LLM 识别高光 → FFmpeg 拼接 → 返回 segments
   └── 收集 predicted + ground_truth + token/timing 数据
         │
         ▼
   并行执行（ThreadPoolExecutor）：
   ├── HighlightEvaluator.evaluate_all()
   │   ├── 逐 case 做 tIoU 贪心匹配（predicted vs ground_truth["highlights"]）
   │   └── 输出: CaseScore
   └── LLMJudge.judge_all()
       ├── Segment Judge（逐片段观看，评内容完整性/片段质量/指令契合度）
       └── Video Judge（观看拼接后集锦，评节奏/转场/音画同步/内容完整性/指令契合度）
         │
         ▼
   compute_weighted_score(F1×0.5 + Segment Judge×0.25 + Video Judge×0.25)
         │
         ▼
   ReportGenerator.generate() → report.txt + report.json
```

---

## 四、评测指标体系

### 4.1 量化评测（tIoU 时间轴匹配）

将 Pipeline 输出的片段与人工标注的 ground truth 做时间轴匹配。

| 指标 | 公式 | 判断标准 | 说明 |
|------|------|----------|------|
| **IoU** | 交集时长 / 并集时长 | ≥0.8 优秀 / ≥0.5 合格 / <0.5 不合格 | 单片段与 GT 的重叠度 |
| **Precision** | hit_count / len(predicted) | 越高越好 | 预测片段中命中 GT 的比例 |
| **Recall** | hit_count / len(ground_truth) | 越高越好 | GT 片段中被找到的比例 |
| **F1** | 2 × P × R / (P + R) | 越高越好，核心指标 | Precision 和 Recall 的调和均值 |
| **Hit Rate @1** | Top-1 是否命中任意 GT | 越高越好 | 最优片段是否命中 |
| **Hit Rate @3** | Top-3 命中率 | 越高越好 | 前三片段覆盖能力 |
| **MAE** | 命中片段起止时间平均偏差（秒） | 越小越好 | IoU 之外的精细时间偏差 |
| **mAP@0.5** | 单阈值 Average Precision | 越高越好 | 对标 QVHighlights，IoU≥0.5 匹配 |
| **mAP@0.75** | 严格阈值 Average Precision | 越高越好 | 对标 QVHighlights，IoU≥0.75 匹配 |
| **Avg mAP** | [0.5:0.05:0.95] 10 个阈值均值 | 越高越好 | 对标 QVHighlights 多阈值标准 |
| **Kendall's τ** | 预测 score 排序 vs GT score 排序的秩相关性 | [-1, 1]，越高越好 | 对标 TVSum 标准 |
| **Spearman's ρ** | 同上，单调关系度量 | [-1, 1]，越高越好 | 对标 TVSum 标准 |

**匹配规则**：贪心匹配，每个预测片段找 IoU 最大的未使用 GT，IoU ≥ 0.5 算命中。

### 4.2 主观评测（双 LLM Judge）

#### Segment Judge（片段质量评测）— 权重 25%

逐个观看每个高光片段视频，判断片段本身的质量。看不到原始视频，不评测"检出率"。

| 维度 | 评估内容 | 评分范围 |
|------|----------|----------|
| 内容完整性 | 每个片段是否完整保留了关键动作/事件，有无截断 | 1-10 分 |
| 片段质量 | 画面质量、内容精彩程度、是否混入空镜头/静止画面/重复内容 | 1-10 分 |
| 指令契合度 | 每个片段是否符合剪辑目标和风格要求 | 1-10 分 |

#### Video Judge（集锦质量评测）— 权重 25%

观看拼接后的完整集锦视频，判断整体观感质量。看不到原始视频，不评测"检出率"和"冗余控制"。

| 维度 | 评估内容 | 评分范围 |
|------|----------|----------|
| 节奏感 | 整体剪辑节奏是否流畅、符合风格要求 | 1-10 分 |
| 转场质量 | 片段间过渡是否自然，有无黑屏/卡顿/跳帧 | 1-10 分 |
| 音画同步 | 音频与画面是否同步，BGM 是否匹配 | 1-10 分 |
| 内容完整性 | 集锦中各片段是否有截断，关键内容是否完整 | 1-10 分 |
| 指令契合度 | 集锦整体是否符合剪辑目标和风格要求 | 1-10 分 |

#### 设计原则

- 信息充分性：每个 Judge 只评测自己能看到的、信息充分的东西
- 互补不重叠：Segment Judge 管"每个片段好不好"，Video Judge 管"拼在一起好不好"
- 检出率归量化：遗漏/多余由 tIoU 量化评测覆盖（有 GT 标注，客观准确）

### 4.3 加权总分

```
加权总分 = tIoU F1 × 0.5 + Segment Judge 归一化分 × 0.25 + Video Judge 归一化分 × 0.25
```

Segment Judge 归一化分 = segment_average / 10.0，Video Judge 归一化分 = video_average / 10.0。

降级策略：两个 Judge 都不可用 → 总分仅基于 F1；仅一个可用 → 该 Judge 占满 50% 权重。

### 4.4 微平均指标

| 指标 | 公式 | 说明 |
|------|------|------|
| 微平均 Precision | sum(hit_count) / sum(len(predicted)) | 全局命中率，片段多的 case 权重更大 |
| 微平均 Recall | sum(hit_count) / sum(len(GT)) | 全局召回率 |
| 微平均 F1 | 2 × mP × mR / (mP + mR) | 微平均的调和均值 |

### 4.5 片段质量指标

| 指标 | 公式 | 判断标准 |
|------|------|----------|
| 片段数偏差率 | \|len(pred) - len(GT)\| / len(GT) | 越接近 0 越好 |
| 集锦时长占比 | sum(pred 时长) / 视频总时长 | 合理范围 5%-30% |
| 指令时长契合度 | 1.0 - \|实际时长 - 目标时长\| / 目标时长 | 1.0 完全契合，clamp 到 [0,1] |

### 4.6 成本 & 性能指标

| 指标 | 说明 |
|------|------|
| Token 消耗 | 总 Token / Prompt Token / Completion Token / Token/分钟视频 |
| API 调用统计 | API 调用次数 / 重试次数 |
| 阶段耗时 | 视频获取 / 高光检测 / FFmpeg 拼接 各阶段平均耗时 |
| 处理倍速 | 总处理耗时 / 视频总时长 |
| 内存峰值 | 单 case 最大/平均内存占用 |
| 并发吞吐量 | 并发压测模式下的 case/s |
| 异常率 | 执行失败 case 占比 |
| tIoU 分布 | 优秀(≥0.8)/合格(≥0.5)/不合格(<0.5) 三档分布 |

---

## 五、评测流程

```
1. TestCaseLoader 加载用例（cases.yaml + instruction.json + ground_truth.json + metadata.yaml）
2. EvalRunner 遍历用例，调用 Pipeline.run(source, description, skip_edit=False)
3. 从 PipelineResult.edit.segments 提取 predicted 片段
4. 并行执行（ThreadPoolExecutor）：
   a. HighlightEvaluator.evaluate_all() 做 tIoU 匹配，计算所有量化指标
   b. LLMJudge.judge_all() 并行运行 Segment Judge + Video Judge
5. compute_weighted_score() 计算三层加权总分
6. ReportGenerator.generate() 生成 report.txt + report.json
```

---

## 六、评测模块

| 模块 | 文件 | 职责 |
|------|------|------|
| 用例加载 | `evaluation/evaluator.py` — `TestCaseLoader` | 读取 cases.yaml + instruction.json + ground_truth.json，聚合多数据源 |
| 量化评测 | `evaluation/evaluator.py` — `HighlightEvaluator` | tIoU 贪心匹配，计算全部量化指标 |
| LLM Judge | `evaluation/llm_judge.py` — `LLMJudge` | 双 Judge 并行评测（Segment + Video） |
| 评测编排 | `evaluation/runner.py` — `EvalRunner` | 加载用例 → 逐 case 跑 Pipeline → 并行评测 → 加权融合 |
| 报告生成 | `evaluation/report.py` — `ReportGenerator` | 文本报告 + 结构化 JSON |

---

## 七、评测用例集

### 7.1 数据来源

30 组自建 benchmark 数据集（`evaluation/test_cases/benchmark/`），涵盖三类难度：

| 难度 | 数量 | 说明 |
|------|------|------|
| normal | 10 组 | 明确主题 + 清晰指令 |
| complex | 8 组 | 多维度要求 / 模糊指令 / 混合节奏 |
| adversarial | 12 组 | 空指令 / 超长指令 / 静态画面 / 注入攻击 / 文件伪装 / 格式校验 |

场景覆盖：体育、电竞、篮球、旅行、美食、综艺、编程教育、AI 科普、户外、修仙动漫、旅行美食。

### 7.2 用例结构

```
case_bm_XXX/
├── video.mp4              # 原始视频
├── instruction.json       # 剪辑指令 {"prompt": "帮我把精彩片段剪成60秒集锦"}
├── ground_truth.json      # 人工标注 {"highlights": [{"start_time": 10.0, "end_time": 25.0, "label": "精彩动作", "score": 0.8}]}
└── metadata.yaml          # 视频元数据（duration/fps/resolution/scene_type）
```

在 `benchmark/cases.yaml` 中注册：

```yaml
cases:
  - id: case_bm_001
    category: 体育
    difficulty: normal
    description: "足球比赛进球集锦"
    video_file: "video.mp4"
```

---

## 八、评测配置

```python
from evaluation.runner import EvalRunner, EvalRunConfig

config = EvalRunConfig(
    test_cases_root="evaluation/test_cases",
    output_dir="reports",
    iou_threshold=0.5,       # IoU 命中阈值
    skip_llm_judge=False,    # 是否跳过 LLM Judge（跳过则总分仅基于 F1）
    skip_edit=False,         # 是否跳过 FFmpeg 剪辑（必须 False）
    judge_weight=0.5,        # LLM Judge 在总分中的权重
    judge_max_retries=3,     # LLM Judge 失败重试次数
    concurrency=1,           # 并发数（>1 开启压测模式）
)
runner = EvalRunner(config)
eval_report, judge_report, report_text = runner.run()
print(report_text)
```

---

## 九、输出产物

### report.txt

两部分：整体汇总 + 每用例详情。

**整体汇总：**

| 指标组 | 包含字段 |
|--------|---------|
| tIoU 整体 | overall_iou, overall_precision, overall_recall, overall_f1（均为宏平均） |
| 微平均 | overall_micro_precision, overall_micro_recall, overall_micro_f1 |
| 检出率 | overall_hit_rate_1, overall_hit_rate_3 |
| 时间精度 | overall_mae（秒） |
| 片段质量 | overall_segment_count_deviation, overall_total_duration_ratio, overall_instruction_duration_fit |
| 多阈值 mAP | mAP@0.5, mAP@0.75, Avg mAP |
| 排序相关性 | Kendall's τ, Spearman's ρ（若 scipy 不可用显示 N/A） |
| tIoU 分布 | 优秀(≥0.8) / 合格(≥0.5) / 不合格(<0.5) 三档计数 |
| 异常统计 | exception_rate, exception_count, total_count |
| 性能 & 成本 | total_tokens, prompt_tokens, completion_tokens, api_calls, api_retries, video_duration, tokens_per_minute, total_elapsed, avg_elapsed, processing_ratio, timing_fetch_avg, timing_detection_avg, timing_clip_concat_avg, memory_peak_mb, memory_avg_mb |
| 分组统计 | 按 category / difficulty / source_type 分组的 F1 + 样本数 |
| Segment Judge | content_completeness, segment_quality, instruction_fit, average（均为 /10.0） |
| Video Judge | rhythm, transition_quality, audiovisual_sync, content_completeness, instruction_fit, average（均为 /10.0） |
| 加权总分 | 量化 F1×0.5 + Segment Judge×0.25 + Video Judge×0.25，总分 / 1.0 |

**每用例详情表**（每个 case 一行，含：case_id, category, difficulty, source_type, precision, recall, f1, hit_rate_1, hit_rate_3, mae, segment_count_deviation, total_duration_ratio, instruction_duration_fit, map_50, map_75, avg_map, kendall_tau, spearman_rho, iou_distribution, error）。执行失败时 error 非空，量化指标填 0。

LLM Judge 逐条：每 case 的 Segment Judge 评分 + 评语、Video Judge 评分 + 评语。

### report.json

```json
{
  "iou_eval": {
    "overall_iou": 0.0, "overall_precision": 0.0, "overall_recall": 0.0, "overall_f1": 0.0,
    "overall_micro_precision": 0.0, "overall_micro_recall": 0.0, "overall_micro_f1": 0.0,
    "overall_hit_rate_1": 0.0, "overall_hit_rate_3": 0.0, "overall_mae": 0.0,
    "overall_segment_count_deviation": 0.0, "overall_total_duration_ratio": 0.0,
    "overall_instruction_duration_fit": 0.0,
    "overall_map_50": 0.0, "overall_map_75": 0.0, "overall_avg_map": 0.0,
    "overall_kendall_tau": null, "overall_spearman_rho": null,
    "iou_distribution": { "excellent": 0, "qualified": 0, "unqualified": 0 },
    "exception_rate": 0.0, "exception_count": 0, "total_count": 0,
    "cost": {
      "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0,
      "video_duration": 0.0, "tokens_per_minute": 0.0,
      "api_calls": 0, "api_retries": 0,
      "total_elapsed": 0.0, "avg_elapsed": 0.0, "processing_ratio": 0.0,
      "memory_peak_mb": 0.0, "memory_avg_mb": 0.0,
      "concurrency": 0, "concurrent_throughput": 0.0,
      "timing": { "fetch_avg": 0.0, "detection_avg": 0.0, "clip_concat_avg": 0.0 }
    },
    "by_category": { "体育": { "f1": 0.0, "count": 0 } },
    "by_difficulty": { "normal": { "f1": 0.0, "count": 0 } },
    "by_source": { "benchmark": { "f1": 0.0, "count": 0 } },
    "cases": [{
      "case_id": "case_bm_001", "category": "体育", "difficulty": "normal", "source_type": "benchmark",
      "precision": 0.0, "recall": 0.0, "f1": 0.0,
      "hit_rate_1": 0.0, "hit_rate_3": 0.0, "mae": 0.0,
      "segment_count_deviation": 0.0, "total_duration_ratio": 0.0, "instruction_duration_fit": 0.0,
      "map_50": 0.0, "map_75": 0.0, "avg_map": 0.0,
      "kendall_tau": null, "spearman_rho": null,
      "iou_distribution": { "excellent": 0, "qualified": 0, "unqualified": 0 },
      "error": null
    }]
  },
  "segment_judge": {
    "content_completeness": 0.0, "segment_quality": 0.0, "instruction_fit": 0.0,
    "average": 0.0, "degraded": false,
    "cases": [{ "content_completeness": 0, "segment_quality": 0, "instruction_fit": 0, "average": 0, "comment": "", "error": null }]
  },
  "video_judge": {
    "rhythm": 0.0, "transition_quality": 0.0, "audiovisual_sync": 0.0,
    "content_completeness": 0.0, "instruction_fit": 0.0, "average": 0.0,
    "degraded": false,
    "cases": [{ "rhythm": 0, "transition_quality": 0, "audiovisual_sync": 0, "content_completeness": 0, "instruction_fit": 0, "average": 0, "comment": "", "error": null }]
  },
  "weighted_score": {
    "eval_score": 0.0, "segment_judge_score": 0.0, "video_judge_score": 0.0,
    "judge_score": 0.0, "weighted_score": 0.0, "degraded": false
  }
}
```

**重要规则：**
- `iou_eval.cases` 数组长度 = 总评测用例数，每个 case 必定有一条记录（成功或失败）
- 用例执行失败时 `error` 字段非空，量化指标全部填 0
- `segment_judge.cases` 和 `video_judge.cases` 只包含有 predicted 片段的 case
- 任何 Judge 不可用时 `degraded: true`，对应评分置 0
- 浮点数保留 3 位小数（成本类保留 1 位）

---

## 十、典型分析模板（待实现）

评测完成后，针对以下维度做 case-level 分析：

1. **Top-3 最佳案例**：分析为什么多模态模型能精准命中，什么类型的视频/指令效果最好
2. **Top-3 最差案例**：分析失败原因——是 GT 标注偏差、多模态模型理解错误、还是视频本身不适合
3. **指令敏感性**：同一视频不同指令的结果差异
4. **视频类型对比**：不同类别的 F1 差异及原因
5. **双 Judge 分歧分析**：Segment Judge 高分但 Video Judge 低分的 case（片段好但拼得差），反之亦然
