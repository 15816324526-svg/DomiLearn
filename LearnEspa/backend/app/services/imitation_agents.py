"""Bounded, structured model tasks for textbook imitation.

State changes and evidence calculations stay in ``ImitationService``. These
prompts ask the model for language work, not authority over database facts.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from app.services.import_service import ServiceError


class StructuredGateway(Protocol):
    def generate_structured(
        self, purpose: str, system_prompt: str, user_prompt: str, schema: dict
    ) -> tuple[dict, dict | None]: ...


def _object(properties: dict[str, Any], required: list[str] | None = None) -> dict:
    return {
        "type": "object", "properties": properties,
        "required": required if required is not None else list(properties),
        "additionalProperties": False,
    }


_STRING = {"type": "string"}
_BOOL = {"type": "boolean"}
_STRING_ARRAY = {"type": "array", "items": _STRING}

MEMORY_SCHEMA = _object({"focus": _STRING_ARRAY, "evidence_ids": _STRING_ARRAY})
PLAN_SCHEMA = _object({"items": {"type": "array", "items": _object({
    "source_sentence_id": _STRING,
    "expected_pattern": _STRING,
    "fixed_collocations": _STRING_ARRAY,
    "scene_role": _STRING,
})}})
COMPOSITION_SCHEMA = _object({"background": _STRING, "items": {"type": "array", "items": _object({
    "source_sentence_id": _STRING,
    "speaker": {"type": ["string", "null"]},
    "chinese_text": _STRING,
    "hint": {"type": ["string", "null"]},
})}})
AUDIT_SCHEMA = _object({"approved": _BOOL, "issues": _STRING_ARRAY})
FEEDBACK_SCHEMA = _object({
    "verdict": {"type": "string", "enum": ["rejected", "passed", "alternative"]},
    "meaning_ok": _BOOL, "grammar_ok": _BOOL, "pattern_used": _BOOL,
    "pattern_attempted": _BOOL, "explanation": _STRING,
    "revision": {"type": ["string", "null"]},
})
REFLECTION_SCHEMA = _object({"summary": _STRING, "evidence_ids": _STRING_ARRAY})
REPORT_SCHEMA = _object({
    "summary": _STRING,
    "recurring_issues": _STRING_ARRAY,
    "comparison": {"type": ["string", "null"]},
    "next_suggestions": _STRING_ARRAY,
    "cited_attempt_ids": _STRING_ARRAY,
})


class ImitationAgents:
    def __init__(self, gateway: StructuredGateway, record_usage) -> None:
        self.gateway = gateway
        self.record_usage = record_usage

    def _call(self, purpose: str, system: str, payload: dict, schema: dict, round_id: str | None = None) -> dict:
        result, usage = self.gateway.generate_structured(
            purpose, system, json.dumps(payload, ensure_ascii=False), schema
        )
        if usage:
            try:
                self.record_usage(round_id, purpose, usage)
            except Exception:
                # A usage-log failure must not discard a completed model answer.
                pass
        if not isinstance(result, dict):
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "模型返回格式异常，请重试")
        return result

    def opening_memory(self, source: list[dict], review_words: list[dict], evidence: list[dict]) -> dict:
        result = self._call(
            "memory_open",
            "你是语言学习记忆 Agent。根据提供的真实记录概括本轮关注点；可用的证据 ID 只能从输入中选。没有记录就如实说没有。不要宣称掌握概率。用简短中文回答。",
            {"source": source, "review_words": review_words, "past_evidence": evidence},
            MEMORY_SCHEMA,
        )
        valid_ids = {item["id"] for item in review_words + evidence}
        ids = result.get("evidence_ids")
        if not isinstance(ids, list) or not all(isinstance(value, str) and value in valid_ids for value in ids):
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "记忆引用了不存在的练习记录")
        if not isinstance(result.get("focus"), list) or not all(isinstance(v, str) for v in result["focus"]):
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "记忆结果格式异常")
        return result

    def plan(self, source: list[dict], memory: dict, review_words: list[dict]) -> dict:
        return self._call(
            "imitation_plan",
            "你是西班牙语课文仿写编排 Agent。先规划一一对应的句式迁移。每个原句选一个原文中逐字存在、可以迁移到新情景的核心西语句式短语；人名和偶然出现的普通名词不作为句式。若原句有固定搭配，也只能引用原句真实短语。已固定的 core_pattern 必须照用。保留叙述/对话结构、句子顺序与人物轮次。复习词可以自然融入，不是强制目标。不要逐字复述旧情景。",
            {"source": source, "memory": memory, "review_words": review_words}, PLAN_SCHEMA,
        )

    def compose(self, source: list[dict], plan: dict, memory: dict, repair_issues: list[str] | None = None, previous: dict | None = None) -> dict:
        return self._call(
            "imitation_repair" if repair_issues else "imitation_compose",
            "你是西班牙语教材仿写编排 Agent。依据已给计划写完整、连贯的全篇中文新情景。背景仅一句简短中文；items 与原句一一对应，保留对话/叙述形式和人物轮次，每句给自然中文题及可选的简短场景提示。提示不能直接给完整西语答案。核心句式和固定搭配必须在新情景中有自然使用机会。不要把复习词当强制判分目标。若有审核问题，只修复列出的问题。",
            {"source": source, "plan": plan, "memory": memory, "audit_issues": repair_issues or [], "previous": previous},
            COMPOSITION_SCHEMA,
        )

    def audit(self, source: list[dict], plan: dict, composition: dict) -> dict:
        result = self._call(
            "imitation_audit",
            "你是独立的教材仿写质检 Agent。严格检查中文课文自然度、场景连贯性、原文对话/叙述结构、礼貌称呼关系、每句核心句式及固定搭配能否自然使用。只返回 approved 与具体问题；不修改题目。",
            {"source": source, "plan": plan, "composition": composition}, AUDIT_SCHEMA,
        )
        if type(result.get("approved")) is not bool or not isinstance(result.get("issues"), list):
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "仿写审核结果格式异常")
        return result

    def judge(self, source: dict, planned: dict, answer: str, prior: list[dict], round_id: str) -> dict:
        result = self._call(
            "imitation_feedback",
            "你是西语逐句辅导 Agent。判断学生回答是否正确表达中文题意、语法是否可接受、是否真正用到教材核心句式。接受不同的正确表达；纯标点/不影响理解的自然度问题不能阻止通过。重音改变词义时须修改。若意思及语法正确但没用教材句式，verdict=alternative，告知如何在此情景用教材句式，允许继续。只有实质错误才 rejected。每次给具体原因和可执行改法。pattern_attempted 指回答是否实质尝试使用原文核心句式；不能猜测。不要因没使用复习词扣分。",
            {"source": source, "planned": planned, "answer": answer, "prior_attempts": prior},
            FEEDBACK_SCHEMA, round_id,
        )
        verdict = result.get("verdict")
        if verdict not in ("rejected", "passed", "alternative"):
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "模型判定结果异常，请重试")
        for key in ("meaning_ok", "grammar_ok", "pattern_used", "pattern_attempted"):
            if type(result.get(key)) is not bool:
                raise ServiceError("MODEL_RESPONSE_INVALID", 502, "模型判定字段异常，请重试")
        if not isinstance(result.get("explanation"), str) or not result["explanation"].strip():
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "模型反馈为空，请重试")
        if verdict == "passed" and not (result["meaning_ok"] and result["grammar_ok"] and result["pattern_used"]):
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "模型判定前后矛盾，请重试")
        if verdict == "alternative" and not (result["meaning_ok"] and result["grammar_ok"] and not result["pattern_used"]):
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "模型判定前后矛盾，请重试")
        if verdict in ("alternative", "rejected") and (not isinstance(result.get("revision"), str) or not result["revision"].strip()):
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "模型没有给出可执行的修改示例，请重试")
        if verdict == "rejected" and result["meaning_ok"] and result["grammar_ok"]:
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "模型把正确答案判为错误，请重试")
        return result

    def reflect(self, facts: dict, valid_ids: set[str], round_id: str) -> dict:
        result = self._call(
            "memory_reflect",
            "你是学习记忆 Agent。只依据真实答案、反馈和确定性评分总结本轮表现。引用必须是输入中真实 attempt ID。手动通过和未练到的句式不能算掌握。反思可供下一轮检索，但原始记录优先。",
            facts, REFLECTION_SCHEMA, round_id,
        )
        if not isinstance(result.get("summary"), str) or not isinstance(result.get("evidence_ids"), list):
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "记忆整理格式异常")
        if any(value not in valid_ids for value in result["evidence_ids"]):
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "记忆引用了不存在的答案")
        return result

    def report(self, facts: dict, valid_ids: set[str], round_id: str) -> dict:
        result = self._call(
            "imitation_report",
            "你是学习报告 Agent。依据给定统计、句式证据和真实提交写简短、具体的中文学习报告。不能虚构练习次数、薄弱点或掌握百分比；只引用给出的 attempt ID。完整原文可见时不能说成独立掌握。第一次练习无历史对比时 comparison 为 null。",
            facts, REPORT_SCHEMA, round_id,
        )
        if not isinstance(result.get("summary"), str) or not isinstance(result.get("cited_attempt_ids"), list):
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "学习报告格式异常")
        if any(value not in valid_ids for value in result["cited_attempt_ids"]):
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "报告引用了不存在的答案")
        for field in ("recurring_issues", "next_suggestions"):
            if not isinstance(result.get(field), list) or not all(isinstance(value, str) for value in result[field]):
                raise ServiceError("MODEL_RESPONSE_INVALID", 502, "学习报告格式异常")
        if result["recurring_issues"] and not result["cited_attempt_ids"]:
            raise ServiceError("MODEL_RESPONSE_INVALID", 502, "报告中的反复问题缺少练习记录依据")
        return result
