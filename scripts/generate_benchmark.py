#!/usr/bin/env python3
"""Generate 25 benchmark test cases (normal/complex/adversarial) for evaluation."""

import json
from pathlib import Path

import yaml

BENCHMARK_DIR = Path(__file__).resolve().parent.parent / "evaluation" / "test_cases" / "benchmark"

CASES_YAML = {
    "cases": [
        # ===== Normal (10 组) =====
        {"id": "case_bm_001", "category": "体育", "difficulty": "normal", "description": "足球比赛进球集锦", "video_file": "video.mp4"},
        {"id": "case_bm_002", "category": "游戏", "difficulty": "normal", "description": "MOBA团战高光", "video_file": "video.mp4"},
        {"id": "case_bm_003", "category": "旅行", "difficulty": "normal", "description": "城市Vlog景点精华", "video_file": "video.mp4"},
        {"id": "case_bm_004", "category": "生活", "difficulty": "normal", "description": "美食制作关键步骤", "video_file": "video.mp4"},
        {"id": "case_bm_005", "category": "娱乐", "difficulty": "normal", "description": "综艺笑点合集", "video_file": "video.mp4"},
        {"id": "case_bm_006", "category": "教育", "difficulty": "normal", "description": "Python课程知识点", "video_file": "video.mp4"},
        {"id": "case_bm_007", "category": "户外", "difficulty": "normal", "description": "登山风景精华", "video_file": "video.mp4"},
        {"id": "case_bm_008", "category": "动漫", "difficulty": "normal", "description": "战斗场景高光", "video_file": "video.mp4"},
        {"id": "case_bm_009", "category": "体育", "difficulty": "normal", "description": "篮球扣篮集锦", "video_file": "video.mp4"},
        {"id": "case_bm_010", "category": "旅行", "difficulty": "normal", "description": "美食探店精华", "video_file": "video.mp4"},
        # ===== Complex (8 组) =====
        {"id": "case_bm_011", "category": "体育", "difficulty": "complex", "description": "多维度要求（对抗+温情+观众）", "video_file": "video.mp4"},
        {"id": "case_bm_012", "category": "游戏", "difficulty": "complex", "description": "快节奏但保留情感时刻", "video_file": "video.mp4"},
        {"id": "case_bm_013", "category": "旅行", "difficulty": "complex", "description": "多目的地模糊指令", "video_file": "video.mp4"},
        {"id": "case_bm_014", "category": "娱乐", "difficulty": "complex", "description": "多人综艺复杂场景", "video_file": "video.mp4"},
        {"id": "case_bm_015", "category": "教育", "difficulty": "complex", "description": "ML教程理论与实践混合", "video_file": "video.mp4"},
        {"id": "case_bm_016", "category": "户外", "difficulty": "complex", "description": "滑雪快慢节奏混合", "video_file": "video.mp4"},
        {"id": "case_bm_017", "category": "动漫", "difficulty": "complex", "description": "多集混剪（战斗+日常+搞笑）", "video_file": "video.mp4"},
        {"id": "case_bm_018", "category": "生活", "difficulty": "complex", "description": "日常Vlog模糊高光定义", "video_file": "video.mp4"},
        # ===== Adversarial (7 组) =====
        {"id": "case_bm_019", "category": "体育", "difficulty": "adversarial", "description": "空指令测试", "video_file": "video.mp4"},
        {"id": "case_bm_020", "category": "游戏", "difficulty": "adversarial", "description": "超长指令 3000+ 字符", "video_file": "video.mp4"},
        {"id": "case_bm_021", "category": "生活", "difficulty": "adversarial", "description": "静态图片视频", "video_file": "video.mp4"},
        {"id": "case_bm_022", "category": "娱乐", "difficulty": "adversarial", "description": "中英日+emoji混合指令", "video_file": "video.mp4"},
        {"id": "case_bm_023", "category": "户外", "difficulty": "adversarial", "description": "监控录像无高光", "video_file": "video.mp4"},
        {"id": "case_bm_024", "category": "旅行", "difficulty": "adversarial", "description": "请求时长超视频总长", "video_file": "video.mp4"},
        {"id": "case_bm_025", "category": "教育", "difficulty": "adversarial", "description": "SQL注入/XSS/特殊字符", "video_file": "video.mp4"},
        # ===== 新增：文件完整性 + 格式校验 (4 组) =====
        {"id": "case_bm_026", "category": "体育", "difficulty": "adversarial", "description": "空 video.mp4（0字节）", "video_file": "video.mp4"},
        {"id": "case_bm_027", "category": "体育", "difficulty": "adversarial", "description": "文本文件伪装 mp4", "video_file": "video.mp4"},
        {"id": "case_bm_028", "category": "体育", "difficulty": "adversarial", "description": "图片文件伪装 mp4", "video_file": "video.mp4"},
        {"id": "case_bm_029", "category": "体育", "difficulty": "adversarial", "description": "乱码 instruction.json", "video_file": "video.mp4"},
        {"id": "case_bm_030", "category": "评测", "difficulty": "adversarial", "description": "空 ground_truth.json", "video_file": "video.mp4"},
    ],
}


MINIMAL_PNG = (
    b'\x89PNG\r\n\x1a\n'
    b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
    b'\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N'
    b'\x00\x00\x00\x00IEND\xaeB`\x82'
)
# 每组用例的 instruction.json / ground_truth.json / metadata.yaml 内容定义
CASE_CONTENT = {
    # ==================== Normal ====================
    "case_bm_001": {
        "instruction": {"prompt": "帮我把这个足球视频的进球瞬间剪成60秒集锦，节奏要快，包含射门、庆祝、解说高潮"},
        "ground_truth": {"highlights": [{"start_time": 5.0, "end_time": 12.0, "label": "进球1", "score": 0.95}, {"start_time": 30.0, "end_time": 38.0, "label": "进球2", "score": 0.92}, {"start_time": 55.0, "end_time": 60.0, "label": "庆祝", "score": 0.85}]},
        "metadata": {"source": "benchmark", "duration": 120, "fps": 30, "resolution": "1920x1080", "scene_type": "体育赛事"},
    },
    "case_bm_002": {
        "instruction": {"prompt": "把这场MOBA比赛的团战高光剪出来，30秒，包含击杀、推塔、团灭"},
        "ground_truth": {"highlights": [{"start_time": 10.0, "end_time": 18.0, "label": "团战1", "score": 0.94}, {"start_time": 45.0, "end_time": 52.0, "label": "推塔", "score": 0.88}, {"start_time": 70.0, "end_time": 75.0, "label": "团灭", "score": 0.96}]},
        "metadata": {"source": "benchmark", "duration": 90, "fps": 60, "resolution": "1920x1080", "scene_type": "游戏"},
    },
    "case_bm_003": {
        "instruction": {"prompt": "把这次东京旅行Vlog的精华景点剪成45秒，包含涉谷、浅草、秋叶原"},
        "ground_truth": {"highlights": [{"start_time": 5.0, "end_time": 20.0, "label": "涉谷", "score": 0.87}, {"start_time": 40.0, "end_time": 55.0, "label": "浅草寺", "score": 0.90}, {"start_time": 75.0, "end_time": 85.0, "label": "秋叶原", "score": 0.85}]},
        "metadata": {"source": "benchmark", "duration": 150, "fps": 30, "resolution": "1920x1080", "scene_type": "旅行"},
    },
    "case_bm_004": {
        "instruction": {"prompt": "剪辑这段红烧肉教程的关键步骤，30秒，突出炒糖色、炖煮、收汁"},
        "ground_truth": {"highlights": [{"start_time": 8.0, "end_time": 18.0, "label": "炒糖色", "score": 0.93}, {"start_time": 40.0, "end_time": 55.0, "label": "炖煮", "score": 0.85}, {"start_time": 80.0, "end_time": 88.0, "label": "收汁出锅", "score": 0.91}]},
        "metadata": {"source": "benchmark", "duration": 100, "fps": 30, "resolution": "1920x1080", "scene_type": "美食"},
    },
    "case_bm_005": {
        "instruction": {"prompt": "把这段综艺最好笑的片段剪出来，40秒，包含即兴表演、互怼、翻车"},
        "ground_truth": {"highlights": [{"start_time": 12.0, "end_time": 25.0, "label": "即兴表演", "score": 0.90}, {"start_time": 50.0, "end_time": 62.0, "label": "互怼", "score": 0.88}, {"start_time": 90.0, "end_time": 95.0, "label": "翻车", "score": 0.92}]},
        "metadata": {"source": "benchmark", "duration": 120, "fps": 30, "resolution": "1920x1080", "scene_type": "综艺"},
    },
    "case_bm_006": {
        "instruction": {"prompt": "提取这个Python教程的知识点，20秒，包含变量、循环、函数讲解"},
        "ground_truth": {"highlights": [{"start_time": 10.0, "end_time": 16.0, "label": "变量", "score": 0.82}, {"start_time": 30.0, "end_time": 36.0, "label": "循环", "score": 0.85}, {"start_time": 50.0, "end_time": 54.0, "label": "函数", "score": 0.84}]},
        "metadata": {"source": "benchmark", "duration": 80, "fps": 30, "resolution": "1920x1080", "scene_type": "教育"},
    },
    "case_bm_007": {
        "instruction": {"prompt": "剪辑这段登山视频的风景精华，35秒，包含日出、云海、登顶"},
        "ground_truth": {"highlights": [{"start_time": 15.0, "end_time": 28.0, "label": "日出", "score": 0.95}, {"start_time": 55.0, "end_time": 65.0, "label": "云海", "score": 0.93}, {"start_time": 100.0, "end_time": 108.0, "label": "登顶", "score": 0.97}]},
        "metadata": {"source": "benchmark", "duration": 140, "fps": 30, "resolution": "3840x2160", "scene_type": "户外"},
    },
    "case_bm_008": {
        "instruction": {"prompt": "剪辑这段动漫的战斗高光，25秒，包含大招、连击、变身"},
        "ground_truth": {"highlights": [{"start_time": 5.0, "end_time": 12.0, "label": "变身", "score": 0.96}, {"start_time": 20.0, "end_time": 28.0, "label": "大招", "score": 0.94}, {"start_time": 40.0, "end_time": 45.0, "label": "连击", "score": 0.90}]},
        "metadata": {"source": "benchmark", "duration": 60, "fps": 24, "resolution": "1920x1080", "scene_type": "动漫"},
    },
    "case_bm_009": {
        "instruction": {"prompt": "剪辑这段篮球比赛的扣篮集锦，20秒，包含暴扣、快攻、隔人"},
        "ground_truth": {"highlights": [{"start_time": 8.0, "end_time": 12.0, "label": "暴扣1", "score": 0.94}, {"start_time": 28.0, "end_time": 31.0, "label": "快攻扣篮", "score": 0.91}, {"start_time": 45.0, "end_time": 48.0, "label": "隔人暴扣", "score": 0.93}]},
        "metadata": {"source": "benchmark", "duration": 60, "fps": 30, "resolution": "1920x1080", "scene_type": "体育赛事"},
    },
    "case_bm_010": {
        "instruction": {"prompt": "剪辑这条美食探店视频的精华，30秒，包含环境、菜品特写、试吃评价"},
        "ground_truth": {"highlights": [{"start_time": 5.0, "end_time": 12.0, "label": "环境", "score": 0.80}, {"start_time": 20.0, "end_time": 30.0, "label": "菜品特写", "score": 0.88}, {"start_time": 45.0, "end_time": 55.0, "label": "试吃评价", "score": 0.85}]},
        "metadata": {"source": "benchmark", "duration": 90, "fps": 30, "resolution": "1920x1080", "scene_type": "美食"},
    },
    # ==================== Complex ====================
    "case_bm_011": {
        "instruction": {"prompt": "剪辑这场足球比赛的精彩片段，40秒。需要包含三个维度：1）对抗激烈的进球和扑救 2）球员之间的温情握手和拥抱 3）观众席的欢呼反应。请平衡这三个方面，不要只聚焦于进球"},
        "ground_truth": {"highlights": [{"start_time": 10.0, "end_time": 17.0, "label": "进球", "score": 0.93}, {"start_time": 35.0, "end_time": 40.0, "label": "扑救", "score": 0.88}, {"start_time": 60.0, "end_time": 65.0, "label": "拥抱", "score": 0.75}, {"start_time": 85.0, "end_time": 90.0, "label": "观众欢呼", "score": 0.80}]},
        "metadata": {"source": "benchmark", "duration": 120, "fps": 30, "resolution": "1920x1080", "scene_type": "体育赛事"},
    },
    "case_bm_012": {
        "instruction": {"prompt": "剪辑这场FPS比赛的精彩时刻，35秒。整体节奏要快，但需要在击杀之间保留一些情感时刻——比如队友的默契配合和胜利拥抱。不要只做成击杀集锦"},
        "ground_truth": {"highlights": [{"start_time": 5.0, "end_time": 10.0, "label": "击杀1", "score": 0.92}, {"start_time": 20.0, "end_time": 28.0, "label": "团队配合", "score": 0.88}, {"start_time": 40.0, "end_time": 45.0, "label": "击杀2", "score": 0.90}, {"start_time": 55.0, "end_time": 60.0, "label": "胜利拥抱", "score": 0.78}]},
        "metadata": {"source": "benchmark", "duration": 100, "fps": 60, "resolution": "1920x1080", "scene_type": "游戏"},
    },
    "case_bm_013": {
        "instruction": {"prompt": "我去年去了日本、泰国和新西兰旅行，帮我把这三个国家最漂亮的风景剪成一个混剪视频，50秒左右。要体现每个国家的特色"},
        "ground_truth": {"highlights": [{"start_time": 5.0, "end_time": 20.0, "label": "日本风景", "score": 0.88}, {"start_time": 35.0, "end_time": 50.0, "label": "泰国风景", "score": 0.85}, {"start_time": 65.0, "end_time": 80.0, "label": "新西兰风景", "score": 0.90}]},
        "metadata": {"source": "benchmark", "duration": 100, "fps": 30, "resolution": "3840x2160", "scene_type": "旅行"},
    },
    "case_bm_014": {
        "instruction": {"prompt": "这段综艺有5位常驻和3位嘉宾，帮我剪出每个人的高光时刻，60秒。要保证每个人的镜头时长差不多，特别是嘉宾要多给镜头，包含互动的场景"},
        "ground_truth": {"highlights": [{"start_time": 8.0, "end_time": 15.0, "label": "常驻A", "score": 0.85}, {"start_time": 22.0, "end_time": 28.0, "label": "嘉宾1", "score": 0.87}, {"start_time": 35.0, "end_time": 42.0, "label": "常驻B", "score": 0.82}, {"start_time": 50.0, "end_time": 58.0, "label": "嘉宾2", "score": 0.88}, {"start_time": 70.0, "end_time": 76.0, "label": "互动", "score": 0.84}, {"start_time": 85.0, "end_time": 90.0, "label": "嘉宾3", "score": 0.86}]},
        "metadata": {"source": "benchmark", "duration": 150, "fps": 30, "resolution": "1920x1080", "scene_type": "综艺"},
    },
    "case_bm_015": {
        "instruction": {"prompt": "帮我剪辑这个机器学习教程，55秒。既要包含理论讲解的重点公式，也要包含代码实战部分的模型训练过程。重点突出数据预处理、模型训练和结果评估三个环节及其关联"},
        "ground_truth": {"highlights": [{"start_time": 12.0, "end_time": 22.0, "label": "理论公式", "score": 0.80}, {"start_time": 40.0, "end_time": 48.0, "label": "数据预处理", "score": 0.85}, {"start_time": 65.0, "end_time": 78.0, "label": "模型训练", "score": 0.88}, {"start_time": 90.0, "end_time": 98.0, "label": "结果评估", "score": 0.86}]},
        "metadata": {"source": "benchmark", "duration": 130, "fps": 30, "resolution": "1920x1080", "scene_type": "教育"},
    },
    "case_bm_016": {
        "instruction": {"prompt": "剪辑这段滑雪视频，40秒。要混合快节奏的滑降片段和慢节奏的风景治愈片段，形成节奏对比。整体要有从紧张到放松的叙事感"},
        "ground_truth": {"highlights": [{"start_time": 5.0, "end_time": 12.0, "label": "快速滑降1", "score": 0.92}, {"start_time": 25.0, "end_time": 32.0, "label": "快速滑降2", "score": 0.90}, {"start_time": 50.0, "end_time": 62.0, "label": "山顶风景", "score": 0.88}, {"start_time": 80.0, "end_time": 88.0, "label": "日落", "score": 0.85}]},
        "metadata": {"source": "benchmark", "duration": 120, "fps": 60, "resolution": "3840x2160", "scene_type": "户外"},
    },
    "case_bm_017": {
        "instruction": {"prompt": "我追的这部番有三集，帮我混剪出每集的精华：第一集的热血战斗、第二集的温馨日常、第三集的搞笑片段。最终做成一个45秒的多风格混剪"},
        "ground_truth": {"highlights": [{"start_time": 8.0, "end_time": 18.0, "label": "战斗", "score": 0.94}, {"start_time": 35.0, "end_time": 45.0, "label": "日常", "score": 0.82}, {"start_time": 60.0, "end_time": 68.0, "label": "搞笑", "score": 0.88}]},
        "metadata": {"source": "benchmark", "duration": 90, "fps": 24, "resolution": "1920x1080", "scene_type": "动漫"},
    },
    "case_bm_018": {
        "instruction": {"prompt": "帮我剪一个这周日常Vlog的精华，你觉得什么有意思就剪什么，时长你定"},
        "ground_truth": {"highlights": [{"start_time": 5.0, "end_time": 15.0, "label": "咖啡店", "score": 0.75}, {"start_time": 30.0, "end_time": 42.0, "label": "公园散步", "score": 0.72}, {"start_time": 55.0, "end_time": 62.0, "label": "夕阳", "score": 0.80}, {"start_time": 80.0, "end_time": 85.0, "label": "宠物", "score": 0.85}]},
        "metadata": {"source": "benchmark", "duration": 120, "fps": 30, "resolution": "1920x1080", "scene_type": "日常"},
    },
    # ==================== Adversarial ====================
    "case_bm_019": {
        "instruction": {"prompt": ""},
        "ground_truth": {"highlights": []},
        "metadata": {"source": "benchmark", "duration": 60, "fps": 30, "resolution": "1920x1080", "scene_type": "对抗测试", "adversarial_type": "空指令"},
    },
    "case_bm_020": {
        "instruction": {"prompt": "帮我剪辑这个游戏视频的高光时刻。" + "请务必注意以下要求：" * 300 + "最终剪出30秒。"},
        "ground_truth": {"highlights": [{"start_time": 10.0, "end_time": 20.0, "label": "高光1", "score": 0.90}, {"start_time": 40.0, "end_time": 50.0, "label": "高光2", "score": 0.88}]},
        "metadata": {"source": "benchmark", "duration": 90, "fps": 60, "resolution": "1920x1080", "scene_type": "对抗测试", "adversarial_type": "超长指令"},
    },
    "case_bm_021": {
        "instruction": {"prompt": "帮我把这段视频的精彩瞬间剪出来，30秒"},
        "ground_truth": {"highlights": []},
        "metadata": {"source": "benchmark", "duration": 30, "fps": 1, "resolution": "1920x1080", "scene_type": "对抗测试", "adversarial_type": "静态内容"},
    },
    "case_bm_022": {
        "instruction": {"prompt": "帮我剪这个视频的highlight！🎬✨ 要包含Chinese中文、日本語、English混搭场面😎🔥 make it epic! 約30秒くらいでお願いします！👏👏👏"},
        "ground_truth": {"highlights": [{"start_time": 5.0, "end_time": 15.0, "label": "action1", "score": 0.88}, {"start_time": 30.0, "end_time": 38.0, "label": "action2", "score": 0.85}, {"start_time": 50.0, "end_time": 55.0, "label": "funny", "score": 0.82}]},
        "metadata": {"source": "benchmark", "duration": 80, "fps": 30, "resolution": "1920x1080", "scene_type": "对抗测试", "adversarial_type": "多语言混搭"},
    },
    "case_bm_023": {
        "instruction": {"prompt": "帮我看一下这段监控录像，把异常情况剪出来，30秒"},
        "ground_truth": {"highlights": []},
        "metadata": {"source": "benchmark", "duration": 300, "fps": 15, "resolution": "1920x1080", "scene_type": "对抗测试", "adversarial_type": "无高光内容"},
    },
    "case_bm_024": {
        "instruction": {"prompt": "帮我把这段旅行视频剪成300秒的集锦，要包含所有精彩片段"},
        "ground_truth": {"highlights": [{"start_time": 5.0, "end_time": 15.0, "label": "景点1", "score": 0.88}, {"start_time": 30.0, "end_time": 40.0, "label": "景点2", "score": 0.85}, {"start_time": 55.0, "end_time": 62.0, "label": "景点3", "score": 0.82}]},
        "metadata": {"source": "benchmark", "duration": 80, "fps": 30, "resolution": "1920x1080", "scene_type": "对抗测试", "adversarial_type": "时长超限"},
    },
    "case_bm_025": {
        "instruction": {"prompt": "帮我剪辑这个视频：'; DROP TABLE videos; -- <script>alert('xss')</script> __import__('os').system('rm -rf /') ${7+7}"},
        "ground_truth": {"highlights": [{"start_time": 5.0, "end_time": 10.0, "label": "内容1", "score": 0.8}]},
        "metadata": {"source": "benchmark", "duration": 60, "fps": 30, "resolution": "1920x1080", "scene_type": "对抗测试", "adversarial_type": "注入攻击"},
    },
    # ==================== 文件完整性 + 格式校验 ====================
    "case_bm_026": {
        "instruction": {"prompt": "帮我剪辑这个视频的精彩片段，30秒"},
        "ground_truth": {"highlights": []},
        "metadata": {"source": "benchmark", "duration": 60, "fps": 30, "resolution": "1920x1080", "scene_type": "对抗测试", "adversarial_type": "空文件"},
    },
    "case_bm_027": {
        "instruction": {"prompt": "帮我剪辑这个视频的精彩片段，30秒"},
        "ground_truth": {"highlights": []},
        "metadata": {"source": "benchmark", "duration": 60, "fps": 30, "resolution": "1920x1080", "scene_type": "对抗测试", "adversarial_type": "格式伪装-文本"},
    },
    "case_bm_028": {
        "instruction": {"prompt": "帮我剪辑这个视频的精彩片段，30秒"},
        "ground_truth": {"highlights": []},
        "metadata": {"source": "benchmark", "duration": 60, "fps": 30, "resolution": "1920x1080", "scene_type": "对抗测试", "adversarial_type": "格式伪装-图片"},
    },
    "case_bm_029": {
        "instruction": {"prompt": "这不是有效的 JSON！%$#@!\\n<broken>\\n{\\n  \"invalid\": true,  "},
        "ground_truth": {"highlights": []},
        "metadata": {"source": "benchmark", "duration": 60, "fps": 30, "resolution": "1920x1080", "scene_type": "对抗测试", "adversarial_type": "乱码指令"},
    },
    "case_bm_030": {
        "instruction": {"prompt": "帮我剪辑这个视频的精彩片段，30秒"},
        "ground_truth": {"highlights": []},
        "metadata": {"source": "benchmark", "duration": 60, "fps": 30, "resolution": "1920x1080", "scene_type": "对抗测试", "adversarial_type": "空 ground_truth"},
    },
}


def main():
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)

    # cases.yaml
    with open(BENCHMARK_DIR / "cases.yaml", "w", encoding="utf-8") as f:
        yaml.dump(CASES_YAML, f, allow_unicode=True, sort_keys=False)

    # 每组用例
    for entry in CASES_YAML["cases"]:
        cid = entry["id"]
        case_dir = BENCHMARK_DIR / cid
        case_dir.mkdir(exist_ok=True)

        content = CASE_CONTENT.get(cid, {})
        # video.mp4 — 已有非空文件则跳过，不覆盖
        video_path = case_dir / "video.mp4"
        if video_path.exists() and video_path.stat().st_size > 0:
            pass  # 保留用户放入的真实视频
        elif cid == "case_bm_027":
            video_path.write_text("这不是一个视频文件", encoding="utf-8")
        elif cid == "case_bm_028":
            video_path.write_bytes(MINIMAL_PNG)
        else:
            video_path.write_bytes(b"")
        # instruction.json
        if cid == "case_bm_029":
            # 写入无效 JSON 测试乱码容错
            (case_dir / "instruction.json").write_text(
                '这不是有效的 JSON 内容！！！\n{"broken": true,\n', encoding="utf-8"
            )
        else:
            with open(case_dir / "instruction.json", "w", encoding="utf-8") as f:
                json.dump(content.get("instruction", {}), f, ensure_ascii=False, indent=2)
        # ground_truth.json
        with open(case_dir / "ground_truth.json", "w", encoding="utf-8") as f:
            json.dump(content.get("ground_truth", {"highlights": []}), f, ensure_ascii=False, indent=2)
        # metadata.yaml
        meta = content.get("metadata", {"source": "benchmark", "duration": 60, "fps": 30, "resolution": "1920x1080"})
        with open(case_dir / "metadata.yaml", "w", encoding="utf-8") as f:
            yaml.dump(meta, f, allow_unicode=True, sort_keys=False)

    print(f"[OK] 已生成 {len(CASES_YAML['cases'])} 组 benchmark 数据集 -> {BENCHMARK_DIR}")
    print(f"    目录: {BENCHMARK_DIR}")


if __name__ == "__main__":
    main()
