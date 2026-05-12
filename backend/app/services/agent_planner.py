from __future__ import annotations


def plan_question(question: str) -> dict:
    policy_markers = [
        "退款",
        "政策",
        "规则",
        "条件",
        "保留周期",
        "流程",
        "售后",
        "refund",
        "policy",
        "condition",
        "process",
    ]
    normalized_question = question.lower()
    resume_identity_markers = ["谁的简历", "是谁的简历", "候选人是谁"]
    extraction_markers = ["教育背景", "联系方式", "工作经历", "项目经历", "经验", "经历"]
    summary_markers = ["总结", "概括", "主要讲什么", "关键规则"]
    if any(marker in normalized_question for marker in resume_identity_markers):
        question_type = "resume_identity"
    elif any(marker in normalized_question for marker in policy_markers):
        question_type = "policy"
    elif any(marker in normalized_question for marker in extraction_markers):
        question_type = "extraction"
    elif any(marker in normalized_question for marker in summary_markers):
        question_type = "summary"
    else:
        question_type = "knowledge"
    return {
        "question_type": question_type,
        "steps": ["识别问题类型", "检索知识库", "生成带引用回答", "整理来源"],
    }
