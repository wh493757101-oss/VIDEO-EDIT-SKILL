#!/usr/bin/env python3
"""Rewrite instruction.json — only facts from annotations, no invented details."""
from __future__ import annotations

import json
from pathlib import Path

BENCHMARK = Path(__file__).resolve().parent.parent / "evaluation" / "test_cases" / "benchmark"

# Key: case_id, Value: {"prompt": str}  — only annotation-faithful content
FIXED: dict[str, str] = {
    # ==================== Normal ====================
    "case_bm_001": "帮我把这段足球比赛的进球集锦剪出来，25秒左右，包含两段进球画面。",

    "case_bm_002": "帮我把这段LOL比赛的高光剪出来，15秒。JackeyLove闪现向前配合队友团灭对手的精彩瞬间。",

    "case_bm_003": "把这段东京旅行Vlog的精华剪出来，25秒。包含红叶与风铃的画面、东京街头过马路的人群、照片闪回画面。",

    "case_bm_004": "剪辑这段西红柿炒鸡蛋的教程，85秒左右。分三个步骤：准备食材、鸡蛋炒制、装盘展示。",

    "case_bm_005": "把这段跑男综艺最好笑的片段剪出来，35秒。包含邓超说陈赫牙飘出来了、邓超说比例失调后李晨模仿的场面。",

    "case_bm_006": "提取这个Python变量命名教程的知识点，70秒左右。包含变量取名的硬性规则、Python3.0之后支持中文变量、下划线法和驼峰命名法的讲解。",

    "case_bm_007": "剪辑这段雪山日照金山的风景精华，50秒。包含卡瓦格博日照金山、贡嘎雪山日照金山、富士山日照金山、梅里雪山星空。",

    "case_bm_008": "剪辑这段修仙动漫的高光，90秒左右。包含结婴异象消散和元婴法相显现后消散的画面。",

    "case_bm_009": "剪辑这段篮球比赛的扣篮集锦，25秒。包含起跳隔扣对手多视角回放、大风车扣篮及慢动作回放。",

    "case_bm_010": "剪辑这段成都美食探店视频的精华，155秒左右。包含叶婆婆钵钵鸡、石棉叶凤烧烤、夜宵吃玉滋補。",

    # ==================== Complex ====================
    "case_bm_011": "剪辑这场篮球比赛的精彩片段，40秒左右。包含教练宣布战术队友互相打气、欧文甩开对手压哨命中、队友相拥庆祝胜利。",

    "case_bm_012": "剪辑这场LOL比赛的精彩时刻，40秒。包含赛前英雄选取教练碰拳、高地团灭对手、取得胜利队友激动相拥。",

    "case_bm_013": "剪辑这场无畏契约比赛的精彩时刻，45秒。包含zmjjkk五杀后无奈放出火箭弹、Simon正面击败两位对手、最终相拥捧起奖杯。",

    "case_bm_014": "剪辑这段奔跑吧综艺的精彩时刻，40秒。包含第一轮蓝队获胜、林更新一石三鸟推下三人、最终林更新推下所有人获胜。",

    "case_bm_015": "提取这个AI科普视频的精华，165秒左右。包含纯文本模型如何识别文字、大模型身上的奇怪现象。",

    "case_bm_016": "剪辑这段将军山滑雪视频的精华，40秒。包含人群缓慢滑行的画面、到达滑雪场帅气刹停的瞬间。",

    "case_bm_017": "剪辑这段凡人修仙传动漫的高光，55秒。包含韩立瞬移探查敌人逃跑方向、韩立抓住敌人并将其击杀、韩立闪身来到女生面前。",

    "case_bm_018": "剪辑这段台南旅行Vlog的精华，100秒左右。包含台南吃芥兰炒牛肉和牛肉汤、参观台湾文学馆。",

    # ==================== Adversarial ====================
    "case_bm_020": "帮我剪辑这个编程教学视频的高光时刻。" + "请务必注意以下要求：" * 300 + "最终剪出85秒。",

    "case_bm_022": "帮我剪这个视频的highlight！🎬✨ 要包含欧文扮演老头打球的四次场面😎🔥 約45秒くらいでお願いします！👏👏👏",

    "case_bm_024": "帮我把这段烟花视频剪成300秒的集锦，要包含所有精彩片段。",

    "case_bm_025": "帮我剪辑这个视频：'; DROP TABLE videos; -- <script>alert('xss')</script> __import__('os').system('rm -rf /') ${7+7} 剪出吃年糕的场景，55秒。",
}


def main() -> None:
    for cid, prompt in FIXED.items():
        inst_path = BENCHMARK / cid / "instruction.json"
        inst_path.write_text(
            json.dumps({"prompt": prompt}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(f"[OK] Written {len(FIXED)} instructions")

    print("\n── 修正后的 instruction 清单 ──\n")
    for cid in sorted(FIXED):
        print(f"{cid}:")
        print(f"  {FIXED[cid]}")
        print()


if __name__ == "__main__":
    main()
