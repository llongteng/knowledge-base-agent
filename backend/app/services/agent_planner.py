from __future__ import annotations


def plan_question(question: str) -> dict:
    policy_markers = ["退款", "政策", "规则", "条件", "保留周期", "流程", "售后"]
    question_type = "policy" if any(marker in question for marker in policy_markers) else "knowledge"
    return {
        "question_type": question_type,
        "steps": ["识别问题类型", "检索知识库", "生成带引用回答", "整理来源"],
    }
