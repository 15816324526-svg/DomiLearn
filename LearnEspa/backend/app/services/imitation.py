from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    ConversionVersion, ImitationAttempt, ImitationCallUsage, ImitationMemory,
    ImitationPreference, ImitationReport, ImitationRound, Lesson, Passage,
    PassageSentence, PlannedSentence, Textbook, VocabularyAttempt, VocabularyEntry,
)
from app.services.import_service import ServiceError
from app.services.imitation_agents import ImitationAgents, StructuredGateway
from app.services.sentence_preparation import prepare_passage


SOURCE_MODES = {"normal", "masked", "hidden"}


def _json(value: str | None, fallback=None):
    return json.loads(value) if value else fallback


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


class ImitationService:
    def __init__(self, factory: sessionmaker[Session], gateway: StructuredGateway) -> None:
        self.factory = factory
        self.gateway = gateway
        self.agents = ImitationAgents(gateway, self._record_usage)

    def _record_usage(self, round_id: str | None, purpose: str, usage: dict) -> None:
        with self.factory.begin() as db:
            db.add(ImitationCallUsage(
                id=str(uuid4()), round_id=round_id, purpose=purpose,
                input_tokens=usage.get("input_tokens"), output_tokens=usage.get("output_tokens"),
                total_tokens=usage.get("total_tokens"),
            ))

    def _confirmed_version(self, db: Session) -> str:
        textbook = db.get(Textbook, "modern-spanish-1")
        version = db.get(ConversionVersion, textbook.current_version_id) if textbook and textbook.current_version_id else None
        if version is None or version.confirmed_at is None:
            raise ServiceError("TEXTBOOK_NOT_CONFIRMED", 409, "请先确认教材解析结果")
        return version.id

    def _passage(self, db: Session, passage_id: str, *, require_current: bool = True) -> tuple[Passage, Lesson]:
        passage = db.get(Passage, passage_id)
        lesson = db.get(Lesson, passage.lesson_id) if passage else None
        if passage is None or lesson is None:
            raise ServiceError("PASSAGE_NOT_FOUND", 404, "没有找到课文")
        if require_current and lesson.conversion_version_id != self._confirmed_version(db):
            raise ServiceError("PASSAGE_NOT_FOUND", 404, "没有找到当前教材版本的课文")
        return passage, lesson

    def _round(self, db: Session, round_id: str) -> ImitationRound:
        practice = db.get(ImitationRound, round_id)
        if practice is None:
            raise ServiceError("ROUND_NOT_FOUND", 404, "没有找到仿写记录")
        self._passage(db, practice.passage_id, require_current=False)
        return practice

    def get_passages(self) -> list[dict]:
        with self.factory.begin() as db:
            version_id = self._confirmed_version(db)
            pairs = list(db.execute(select(Passage, Lesson).join(Lesson, Passage.lesson_id == Lesson.id).where(
                Lesson.conversion_version_id == version_id,
            ).order_by(Lesson.lesson_number, Passage.ordinal)))
            result = []
            for passage, lesson in pairs:
                units, issues = prepare_passage(db, passage)
                active = db.scalar(select(ImitationRound).where(
                    ImitationRound.passage_id == passage.id,
                    ImitationRound.status == "active",
                ).order_by(ImitationRound.created_at.desc()))
                result.append({
                    "id": passage.id, "lesson_number": lesson.lesson_number,
                    "title": passage.title, "source_text": passage.content,
                    "ready": bool(units) and not issues, "issue": "；".join(issues) if issues else None,
                    "active_round_id": active.id if active else None, "sentence_count": len(units),
                })
            return result

    def get_preferences(self) -> dict:
        with self.factory() as db:
            preference = db.get(ImitationPreference, 1)
            return {"default_source_mode": preference.default_source_mode if preference else "masked"}

    def set_preferences(self, mode: str) -> dict:
        self._validate_mode(mode)
        with self.factory.begin() as db:
            preference = db.get(ImitationPreference, 1)
            if preference is None:
                preference = ImitationPreference(id=1, default_source_mode=mode)
                db.add(preference)
            else:
                preference.default_source_mode = mode
        return {"default_source_mode": mode}

    @staticmethod
    def _validate_mode(mode: str) -> None:
        if mode not in SOURCE_MODES:
            raise ServiceError("INVALID_SOURCE_MODE", 400, "原文遮挡方式无效")

    def _source_rows(self, db: Session, sentences: list[PassageSentence]) -> list[dict]:
        return [{
            "id": item.id, "ordinal": item.ordinal, "speaker": item.speaker,
            "source_text": item.source_text, "core_pattern": item.core_pattern,
            "fixed_collocations": _json(item.fixed_collocations_json, []),
        } for item in sentences]

    def _opening_context(self, db: Session, lesson_id: str, passage_id: str) -> tuple[list[dict], list[dict]]:
        wrong = list(db.execute(select(VocabularyAttempt, VocabularyEntry).join(
            VocabularyEntry, VocabularyAttempt.word_id == VocabularyEntry.id
        ).where(VocabularyEntry.lesson_id == lesson_id, VocabularyAttempt.is_correct.is_(False)).order_by(
            VocabularyAttempt.created_at.desc()
        ).limit(30)))
        review_words = [{
            "id": attempt.id, "headword": word.headword, "meaning": word.meaning,
            "stage": attempt.stage,
        } for attempt, word in wrong]
        recent = list(db.execute(select(ImitationAttempt, ImitationRound).join(
            ImitationRound, ImitationAttempt.round_id == ImitationRound.id
        ).where(ImitationRound.passage_id == passage_id, ImitationAttempt.status == "complete").order_by(
            ImitationAttempt.created_at.desc()
        ).limit(40)))
        evidence = [{
            "id": attempt.id, "answer": attempt.submitted_text,
            "feedback": _json(attempt.feedback_json, {}),
            "source_mode": attempt.source_mode, "hint_viewed": attempt.hint_viewed,
        } for attempt, _practice in recent]
        summaries = list(db.execute(select(ImitationMemory, ImitationRound).join(
            ImitationRound, ImitationMemory.round_id == ImitationRound.id
        ).where(ImitationRound.passage_id == passage_id).order_by(
            ImitationRound.created_at.desc()
        ).limit(3)))
        evidence.extend({
            "id": memory.id, "kind": "derived_memory",
            "summary": _json(memory.summary_json, {}),
        } for memory, _practice in summaries)
        return review_words, evidence

    @staticmethod
    def _plan_issues(source: list[dict], plan: dict) -> list[str]:
        items = plan.get("items")
        if not isinstance(items, list) or len(items) != len(source):
            return ["句式规划与原文句数不一致"]
        issues: list[str] = []
        for index, (original, item) in enumerate(zip(source, items), 1):
            if not isinstance(item, dict) or item.get("source_sentence_id") != original["id"]:
                issues.append(f"第{index}句未按原文顺序映射")
                continue
            pattern = item.get("expected_pattern")
            if not isinstance(pattern, str) or not pattern.strip() or len(pattern) > 80 or _norm(pattern) not in _norm(original["source_text"]):
                issues.append(f"第{index}句核心句式不在原文中")
            elif original.get("core_pattern") and _norm(pattern) != _norm(original["core_pattern"]):
                issues.append(f"第{index}句更改了已固定的核心句式")
            collocations = item.get("fixed_collocations")
            if not isinstance(collocations, list) or any(
                not isinstance(value, str) or not value.strip() or _norm(value) not in _norm(original["source_text"])
                for value in collocations
            ):
                issues.append(f"第{index}句固定搭配没有原文依据")
            if not isinstance(item.get("scene_role"), str) or not item["scene_role"].strip():
                issues.append(f"第{index}句缺少情景作用")
        return issues

    @staticmethod
    def _composition_issues(source: list[dict], composition: dict) -> list[str]:
        items = composition.get("items")
        background = composition.get("background")
        issues: list[str] = []
        if not isinstance(background, str) or not background.strip() or len(background) > 160:
            issues.append("情景背景应是一句简短提示")
        if not isinstance(items, list) or len(items) != len(source):
            return issues + ["新课文与原文句数不一致"]
        speaker_map: dict[str, str] = {}
        for index, (original, item) in enumerate(zip(source, items), 1):
            if not isinstance(item, dict) or item.get("source_sentence_id") != original["id"]:
                issues.append(f"第{index}句映射或顺序错误")
                continue
            if not isinstance(item.get("chinese_text"), str) or not item["chinese_text"].strip():
                issues.append(f"第{index}句中文题为空")
            elif not re.search(r"[\u4e00-\u9fff]", item["chinese_text"]):
                issues.append(f"第{index}句没有中文题目")
            old_speaker, new_speaker = original.get("speaker"), item.get("speaker")
            if old_speaker:
                if not isinstance(new_speaker, str) or not new_speaker.strip():
                    issues.append(f"第{index}句丢失对话说话者")
                elif old_speaker in speaker_map and speaker_map[old_speaker] != new_speaker:
                    issues.append(f"第{index}句说话者映射不一致")
                else:
                    speaker_map[old_speaker] = new_speaker
            elif new_speaker not in (None, ""):
                issues.append(f"第{index}句把叙述改成了对话")
            if item.get("hint") is not None and not isinstance(item["hint"], str):
                issues.append(f"第{index}句情境提示格式异常")
        return issues

    def start_or_resume(self, passage_id: str) -> dict:
        with self.factory.begin() as db:
            passage, lesson = self._passage(db, passage_id)
            active = db.scalar(select(ImitationRound).where(
                ImitationRound.passage_id == passage_id, ImitationRound.status == "active",
            ).order_by(ImitationRound.created_at.desc()))
            if active:
                return self._present(db, active)
            sentences, issues = prepare_passage(db, passage)
            if not sentences or issues:
                raise ServiceError("PASSAGE_NOT_READY", 409, "课文逐句准备尚需核查：" + "；".join(issues))
            source = self._source_rows(db, sentences)
            review_words, evidence = self._opening_context(db, lesson.id, passage_id)
            preference = db.get(ImitationPreference, 1)
            mode = preference.default_source_mode if preference else "masked"

        opening_usage_ids: list[str] = []

        def record_opening_usage(_round_id: str | None, purpose: str, usage: dict) -> None:
            row_id = str(uuid4())
            with self.factory.begin() as db:
                db.add(ImitationCallUsage(
                    id=row_id, round_id=None, purpose=purpose,
                    input_tokens=usage.get("input_tokens"), output_tokens=usage.get("output_tokens"),
                    total_tokens=usage.get("total_tokens"),
                ))
            opening_usage_ids.append(row_id)

        opening_agents = ImitationAgents(self.gateway, record_opening_usage)
        memory = opening_agents.opening_memory(source, review_words, evidence)
        plan = opening_agents.plan(source, memory, review_words)
        issues = self._plan_issues(source, plan)
        if issues:
            raise ServiceError("PLAN_AUDIT_FAILED", 502, "编排前检查未通过：" + "；".join(issues[:3]))
        composition = opening_agents.compose(source, plan, memory)
        issues = self._composition_issues(source, composition)
        if not issues:
            audit = opening_agents.audit(source, plan, composition)
            if not audit["approved"]:
                issues = [str(item) for item in audit["issues"]] or ["语义审核未通过"]
        if issues:
            repaired = opening_agents.compose(source, plan, memory, issues, composition)
            issues = self._composition_issues(source, repaired)
            if not issues:
                audit = opening_agents.audit(source, plan, repaired)
                if not audit["approved"]:
                    issues = [str(item) for item in audit["issues"]] or ["修复后的语义审核未通过"]
            composition = repaired
        if issues:
            raise ServiceError("COMPOSITION_AUDIT_FAILED", 502, "新课文生成审核未通过：" + "；".join(issues[:3]))

        with self.factory.begin() as db:
            passage, _lesson = self._passage(db, passage_id)
            active = db.scalar(select(ImitationRound).where(
                ImitationRound.passage_id == passage_id, ImitationRound.status == "active",
            ).order_by(ImitationRound.created_at.desc()))
            if active:
                for usage in db.scalars(select(ImitationCallUsage).where(ImitationCallUsage.id.in_(opening_usage_ids))):
                    usage.round_id = active.id
                return self._present(db, active)
            practice = ImitationRound(
                id=str(uuid4()), passage_id=passage.id, status="active",
                background=composition["background"].strip(), current_index=0,
                draft="", source_mode=mode,
                plan_json=json.dumps({"memory": memory, "plan": plan, "composition": composition}, ensure_ascii=False),
            )
            db.add(practice)
            for usage in db.scalars(select(ImitationCallUsage).where(ImitationCallUsage.id.in_(opening_usage_ids))):
                usage.round_id = practice.id
            for index, (source_item, plan_item, composed_item) in enumerate(zip(source, plan["items"], composition["items"])):
                sentence = db.get(PassageSentence, source_item["id"])
                assert sentence is not None
                if not sentence.core_pattern:
                    sentence.core_pattern = plan_item["expected_pattern"].strip()
                    sentence.fixed_collocations_json = json.dumps(plan_item["fixed_collocations"], ensure_ascii=False)
                db.add(PlannedSentence(
                    id=str(uuid4()), round_id=practice.id, source_sentence_id=sentence.id,
                    ordinal=index, speaker=composed_item.get("speaker"),
                    chinese_text=composed_item["chinese_text"].strip(),
                    hint=composed_item.get("hint"), expected_pattern=sentence.core_pattern,
                    fixed_collocations_json=sentence.fixed_collocations_json,
                ))
            db.flush()
            return self._present(db, practice)

    def get_round(self, round_id: str) -> dict:
        with self.factory() as db:
            return self._present(db, self._round(db, round_id))

    def save_draft(self, round_id: str, text: str) -> dict:
        if len(text) > 5000:
            raise ServiceError("DRAFT_TOO_LONG", 400, "当前句子超过字数限制")
        with self.factory.begin() as db:
            practice = self._round(db, round_id)
            if practice.status != "active":
                raise ServiceError("ROUND_COMPLETED", 409, "本轮已完成")
            practice.draft = text
            return self._present(db, practice)

    def _planned(self, db: Session, round_id: str) -> list[PlannedSentence]:
        return list(db.scalars(select(PlannedSentence).where(
            PlannedSentence.round_id == round_id,
        ).order_by(PlannedSentence.ordinal)))

    def _attempts(self, db: Session, planned_id: str) -> list[ImitationAttempt]:
        return list(db.scalars(select(ImitationAttempt).where(
            ImitationAttempt.planned_sentence_id == planned_id,
        ).order_by(ImitationAttempt.created_at, ImitationAttempt.id)))

    def _display_source(self, db: Session, passage: Passage) -> str:
        sentences = list(db.scalars(select(PassageSentence).where(
            PassageSentence.passage_id == passage.id,
        ).order_by(PassageSentence.ordinal)))
        if not sentences:
            return passage.content
        lines: list[str] = []
        last_line = None
        for sentence in sentences:
            if sentence.source_line != last_line:
                prefix = f"{sentence.speaker}: " if sentence.speaker else ""
                lines.append(prefix + sentence.source_text)
                last_line = sentence.source_line
            else:
                lines[-1] += " " + sentence.source_text
        return "\n".join(lines)

    @staticmethod
    def _feedback(attempt: ImitationAttempt) -> dict | None:
        return _json(attempt.feedback_json)

    def _present(self, db: Session, practice: ImitationRound) -> dict:
        passage, lesson = self._passage(db, practice.passage_id, require_current=False)
        planned = self._planned(db, practice.id)
        current = planned[practice.current_index] if practice.status == "active" and practice.current_index < len(planned) else None
        attempts = self._attempts(db, current.id) if current else []
        finished = [item for item in attempts if item.status == "complete"]
        accepted = any((self._feedback(item) or {}).get("verdict") in ("passed", "alternative") for item in finished)
        rejection_count = sum((self._feedback(item) or {}).get("verdict") == "rejected" for item in finished)
        last_feedback = next((self._feedback(item) for item in reversed(finished) if self._feedback(item)), None)
        preference = db.get(ImitationPreference, 1)
        return {
            "id": practice.id, "passage_id": passage.id, "status": practice.status,
            "title": passage.title, "lesson_number": lesson.lesson_number,
            "source_text": self._display_source(db, passage),
            "source_highlights": [item.expected_pattern for item in planned],
            "background": practice.background, "current_index": practice.current_index,
            "total": len(planned),
            "current_sentence": {
                "id": current.id, "speaker": current.speaker,
                "chinese_text": current.chinese_text, "hint": current.hint,
            } if current else None,
            "draft": practice.draft, "feedback": last_feedback,
            "rejection_count": rejection_count, "can_next": accepted,
            "can_manual_pass": rejection_count >= 3 and not accepted,
            "attempts": [self._attempt_view(item) for item in attempts],
            "default_source_mode": preference.default_source_mode if preference else "masked",
        }

    def _attempt_view(self, attempt: ImitationAttempt) -> dict:
        return {
            "id": attempt.id, "answer": attempt.submitted_text, "status": attempt.status,
            "request_id": attempt.request_id,
            "feedback": self._feedback(attempt), "source_mode": attempt.source_mode,
            "hint_viewed": attempt.hint_viewed, "created_at": attempt.created_at.isoformat(),
        }

    def submit_answer(self, round_id: str, request_id: str, answer: str, source_mode: str, hint_viewed: bool) -> dict:
        self._validate_mode(source_mode)
        if not answer.strip():
            raise ServiceError("EMPTY_ANSWER", 400, "请先写一句西语答案")
        if len(answer) > 5000 or not request_id.strip() or len(request_id) > 100:
            raise ServiceError("INVALID_ANSWER", 400, "答案或请求标识无效")
        with self.factory.begin() as db:
            practice = self._round(db, round_id)
            if practice.status != "active":
                raise ServiceError("ROUND_COMPLETED", 409, "本轮已完成")
            planned = self._planned(db, practice.id)[practice.current_index]
            attempt = db.scalar(select(ImitationAttempt).where(
                ImitationAttempt.round_id == practice.id,
                ImitationAttempt.request_id == request_id,
            ))
            if attempt:
                if attempt.planned_sentence_id != planned.id or attempt.submitted_text != answer:
                    raise ServiceError("REQUEST_ID_REUSED", 409, "请求标识已用于另一份答案")
                if attempt.status == "complete":
                    return self._present(db, practice)
            else:
                prior = self._attempts(db, planned.id)
                accepted = [item for item in prior if item.status == "complete" and
                            (self._feedback(item) or {}).get("verdict") in ("passed", "alternative")]
                if accepted and any((self._feedback(item) or {}).get("verdict") == "passed" for item in accepted):
                    raise ServiceError("SENTENCE_ALREADY_PASSED", 409, "这句已通过，请点击下一句")
                attempt = ImitationAttempt(
                    id=str(uuid4()), round_id=practice.id, planned_sentence_id=planned.id,
                    request_id=request_id, submitted_text=answer,
                    source_mode=source_mode, hint_viewed=hint_viewed,
                    status="pending", feedback_json=None,
                )
                db.add(attempt)
                practice.draft = answer
                db.flush()
            attempt_id = attempt.id
            source_sentence = db.get(PassageSentence, planned.source_sentence_id)
            assert source_sentence is not None
            source = {"text": source_sentence.source_text, "speaker": source_sentence.speaker}
            planned_data = {
                "chinese_text": planned.chinese_text, "speaker": planned.speaker,
                "expected_pattern": planned.expected_pattern,
                "fixed_collocations": _json(planned.fixed_collocations_json, []),
                "background": practice.background,
            }
            prior_data = [self._attempt_view(item) for item in self._attempts(db, planned.id) if item.id != attempt_id]

        # The pending raw answer is committed before any model request.
        feedback = self.agents.judge(source, planned_data, answer, prior_data, round_id)
        with self.factory.begin() as db:
            practice = self._round(db, round_id)
            attempt = db.get(ImitationAttempt, attempt_id)
            assert attempt is not None
            if attempt.status == "pending":
                attempt.feedback_json = json.dumps(feedback, ensure_ascii=False)
                attempt.status = "complete"
            return self._present(db, practice)

    def advance(self, round_id: str, manual_pass: bool = False) -> dict:
        completed = False
        with self.factory.begin() as db:
            practice = self._round(db, round_id)
            if practice.status != "active":
                return self._present(db, practice)
            planned = self._planned(db, practice.id)
            current = planned[practice.current_index]
            attempts = self._attempts(db, current.id)
            verdicts = [(self._feedback(item) or {}).get("verdict") for item in attempts if item.status == "complete"]
            accepted = any(value in ("passed", "alternative") for value in verdicts)
            rejected = sum(value == "rejected" for value in verdicts)
            if manual_pass:
                if accepted or rejected < 3:
                    raise ServiceError("MANUAL_PASS_NOT_AVAILABLE", 409, "三次未通过后才能手动通过")
                db.add(ImitationAttempt(
                    id=str(uuid4()), round_id=round_id, planned_sentence_id=current.id,
                    request_id=str(uuid4()), submitted_text="", source_mode=attempts[-1].source_mode if attempts else practice.source_mode,
                    hint_viewed=False, status="manual",
                    feedback_json=json.dumps({"verdict": "manual", "explanation": "用户手动通过；掌握情况未确定"}, ensure_ascii=False),
                ))
            elif not accepted:
                raise ServiceError("SENTENCE_NOT_PASSED", 409, "请先让当前句通过，再进入下一句")
            practice.current_index += 1
            practice.draft = ""
            if practice.current_index >= len(planned):
                practice.status = "completed"
                practice.completed_at = datetime.now(timezone.utc)
                completed = True
                db.add(ImitationReport(id=str(uuid4()), round_id=practice.id, status="pending"))
            db.flush()
            view = self._present(db, practice)
        if completed:
            try:
                self.retry_report(round_id)
            except Exception:
                # The finished practice remains committed even if post-processing fails.
                pass
        return view

    @staticmethod
    def _evidence_for_plan(attempts: list[ImitationAttempt]) -> float | None:
        if any(item.status == "manual" for item in attempts):
            return None
        completed = [item for item in attempts if item.status == "complete"]
        for index, item in enumerate(completed):
            feedback = _json(item.feedback_json, {})
            if feedback.get("verdict") == "passed" and feedback.get("pattern_used"):
                return 1.0 if index == 0 and not item.hint_viewed else 0.5
        if any(_json(item.feedback_json, {}).get("pattern_attempted") for item in completed):
            return 0.0
        return None

    def _pattern_history(self, db: Session, sentence_id: str) -> dict:
        rows = list(db.execute(select(PlannedSentence, ImitationRound).join(
            ImitationRound, PlannedSentence.round_id == ImitationRound.id
        ).where(
            PlannedSentence.source_sentence_id == sentence_id,
            ImitationRound.status == "completed",
        ).order_by(ImitationRound.created_at, ImitationRound.id)))
        observed = []
        for planned, practice in rows:
            attempts = self._attempts(db, planned.id)
            score = self._evidence_for_plan(attempts)
            if score is not None:
                used = next((item for item in attempts if item.status == "complete" and
                             (_json(item.feedback_json, {})).get("verdict") == "passed"), None)
                observed.append({
                    "round_id": practice.id, "score": score,
                    "source_mode": used.source_mode if used else None,
                    "hint_viewed": used.hint_viewed if used else None,
                })
        recent = observed[-3:]
        weighted = sum((index + 1) * item["score"] for index, item in enumerate(recent)) / sum(range(1, len(recent) + 1)) if recent else None
        familiar = len(observed) >= 2 and all(item["score"] == 1.0 for item in observed[-2:])
        label = "较熟悉" if familiar else "初步会用" if observed and observed[-1]["score"] > 0 else "需再练" if observed else "未观察到"
        return {"score": weighted, "label": label, "recent": recent}

    def _round_facts(self, db: Session, practice: ImitationRound) -> dict:
        passage, lesson = self._passage(db, practice.passage_id, require_current=False)
        planned = self._planned(db, practice.id)
        counts = {"first_pass": 0, "revised": 0, "alternative": 0, "manual_pass": 0}
        used_patterns: list[str] = []
        unobserved_patterns: list[str] = []
        weak_patterns: list[str] = []
        details: list[dict] = []
        valid_ids: set[str] = set()
        pattern_evidence = []
        for item in planned:
            attempts = self._attempts(db, item.id)
            valid_ids.update(attempt.id for attempt in attempts if attempt.status in ("complete", "manual"))
            completed = [attempt for attempt in attempts if attempt.status == "complete"]
            first_accepted = next((index for index, attempt in enumerate(completed) if
                                   (_json(attempt.feedback_json, {})).get("verdict") in ("passed", "alternative")), None)
            if any(attempt.status == "manual" for attempt in attempts):
                counts["manual_pass"] += 1
            elif first_accepted is not None:
                verdict = _json(completed[first_accepted].feedback_json, {}).get("verdict")
                counts["alternative" if verdict == "alternative" else "first_pass" if first_accepted == 0 else "revised"] += 1
            score = self._evidence_for_plan(attempts)
            if score is None:
                unobserved_patterns.append(item.expected_pattern)
            elif score > 0:
                used_patterns.append(item.expected_pattern)
            else:
                weak_patterns.append(item.expected_pattern)
            details.append({
                "sentence_id": item.id, "speaker": item.speaker,
                "chinese_text": item.chinese_text, "expected_pattern": item.expected_pattern,
                "attempts": [self._attempt_view(attempt) for attempt in attempts],
            })
            pattern_evidence.append({
                "source_sentence_id": item.source_sentence_id, "pattern": item.expected_pattern,
                "this_round": score, "history": self._pattern_history(db, item.source_sentence_id),
            })
        previous_round = db.scalar(select(ImitationRound).where(
            ImitationRound.passage_id == practice.passage_id,
            ImitationRound.status == "completed",
            ImitationRound.id != practice.id,
            ImitationRound.completed_at < practice.completed_at,
        ).order_by(ImitationRound.completed_at.desc()))
        previous_summary = None
        if previous_round:
            previous_counts = {"first_pass": 0, "revised": 0, "alternative": 0, "manual_pass": 0}
            for old_plan in self._planned(db, previous_round.id):
                old_attempts = self._attempts(db, old_plan.id)
                if any(attempt.status == "manual" for attempt in old_attempts):
                    previous_counts["manual_pass"] += 1
                    continue
                completed_attempts = [attempt for attempt in old_attempts if attempt.status == "complete"]
                first_accepted = next((index for index, attempt in enumerate(completed_attempts) if
                    (_json(attempt.feedback_json, {})).get("verdict") in ("passed", "alternative")), None)
                if first_accepted is not None:
                    verdict = _json(completed_attempts[first_accepted].feedback_json, {}).get("verdict")
                    previous_counts["alternative" if verdict == "alternative" else "first_pass" if first_accepted == 0 else "revised"] += 1
            previous_summary = {
                "id": previous_round.id,
                "completed_at": previous_round.completed_at.isoformat(),
                "counts": previous_counts,
            }
        return {
            "round_id": practice.id, "passage_title": passage.title,
            "lesson_number": lesson.lesson_number, "completed_count": len(planned),
            "counts": counts, "used_patterns": used_patterns,
            "unobserved_patterns": unobserved_patterns,
            "weak_patterns": weak_patterns,
            "pattern_evidence": pattern_evidence,
            "attempts_by_sentence": details,
            "has_previous_round": previous_round is not None,
            "previous_round": previous_summary,
            "valid_attempt_ids": valid_ids,
        }

    def history(self, passage_id: str) -> list[dict]:
        with self.factory() as db:
            self._passage(db, passage_id, require_current=False)
            rounds = list(db.scalars(select(ImitationRound).where(
                ImitationRound.passage_id == passage_id,
            ).order_by(ImitationRound.created_at.desc())))
            return [{
                "id": item.id, "created_at": item.created_at.isoformat(),
                "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                "status": item.status, "completed_count": item.current_index,
                "total": len(self._planned(db, item.id)),
            } for item in rounds]

    def all_history(self) -> list[dict]:
        with self.factory() as db:
            rounds = list(db.scalars(select(ImitationRound).order_by(ImitationRound.created_at.desc())))
            result = []
            for item in rounds:
                passage, lesson = self._passage(db, item.passage_id, require_current=False)
                result.append({
                    "id": item.id, "passage_id": passage.id, "title": passage.title,
                    "lesson_number": lesson.lesson_number, "version_id": lesson.conversion_version_id,
                    "created_at": item.created_at.isoformat(),
                    "completed_at": item.completed_at.isoformat() if item.completed_at else None,
                    "status": item.status, "completed_count": item.current_index,
                    "total": len(self._planned(db, item.id)),
                })
            return result

    def _report_view(self, db: Session, practice: ImitationRound) -> dict:
        facts = self._round_facts(db, practice)
        report = db.scalar(select(ImitationReport).where(ImitationReport.round_id == practice.id))
        memory = db.scalar(select(ImitationMemory).where(ImitationMemory.round_id == practice.id))
        explanation = _json(report.summary_json, {}) if report else {}
        calls = list(db.scalars(select(ImitationCallUsage).where(ImitationCallUsage.round_id == practice.id)))
        usage = {
            "input_tokens": sum(item.input_tokens or 0 for item in calls),
            "output_tokens": sum(item.output_tokens or 0 for item in calls),
            "total_tokens": sum(item.total_tokens or 0 for item in calls),
            "calls": len(calls),
        }
        return {
            "status": report.status if report else "pending",
            "memory_status": "ready" if memory else "pending",
            "summary": explanation.get("summary"), "counts": facts["counts"],
            "used_patterns": facts["used_patterns"],
            "unobserved_patterns": facts["unobserved_patterns"],
            "weak_patterns": facts["weak_patterns"],
            "recurring_issues": explanation.get("recurring_issues", []),
            "comparison": explanation.get("comparison"),
            "next_suggestions": explanation.get("next_suggestions", []),
            "attempts_by_sentence": facts["attempts_by_sentence"],
            "error": report.error if report else None,
            "pattern_evidence": facts["pattern_evidence"],
            "model_usage": usage,
        }

    def get_report(self, round_id: str) -> dict:
        with self.factory() as db:
            practice = self._round(db, round_id)
            if practice.status != "completed":
                raise ServiceError("ROUND_NOT_COMPLETED", 409, "练完所有句子后才能查看报告")
            return self._report_view(db, practice)

    def retry_report(self, round_id: str) -> dict:
        with self.factory() as db:
            practice = self._round(db, round_id)
            if practice.status != "completed":
                raise ServiceError("ROUND_NOT_COMPLETED", 409, "练完所有句子后才能生成报告")
            facts = self._round_facts(db, practice)
            memory = db.scalar(select(ImitationMemory).where(ImitationMemory.round_id == round_id))
            existing_report = db.scalar(select(ImitationReport).where(ImitationReport.round_id == round_id))
            if existing_report and existing_report.status == "ready" and memory:
                return self._report_view(db, practice)
        valid_ids = facts.pop("valid_attempt_ids")
        memory_error = None
        if memory is None:
            try:
                reflection = self.agents.reflect(facts, valid_ids, round_id)
                with self.factory.begin() as db:
                    if not db.scalar(select(ImitationMemory).where(ImitationMemory.round_id == round_id)):
                        db.add(ImitationMemory(
                            id=str(uuid4()), round_id=round_id,
                            summary_json=json.dumps(reflection, ensure_ascii=False),
                        ))
            except Exception as exc:
                memory_error = exc.message if isinstance(exc, ServiceError) else "记忆整理失败，可稍后重试"
        if existing_report and existing_report.status == "ready":
            with self.factory.begin() as db:
                report = db.scalar(select(ImitationReport).where(ImitationReport.round_id == round_id))
                if report:
                    report.error = memory_error
            return self.get_report(round_id)
        try:
            explanation = self.agents.report(facts, valid_ids, round_id)
            if not facts["has_previous_round"]:
                explanation["comparison"] = None
        except Exception as exc:
            with self.factory.begin() as db:
                report = db.scalar(select(ImitationReport).where(ImitationReport.round_id == round_id))
                if report is None:
                    report = ImitationReport(id=str(uuid4()), round_id=round_id, status="failed")
                    db.add(report)
                report.status = "failed"
                report.error = exc.message if isinstance(exc, ServiceError) else "报告生成失败，可稍后重试"
            return self.get_report(round_id)
        with self.factory.begin() as db:
            report = db.scalar(select(ImitationReport).where(ImitationReport.round_id == round_id))
            if report is None:
                report = ImitationReport(id=str(uuid4()), round_id=round_id, status="ready")
                db.add(report)
            report.status = "ready"
            report.summary_json = json.dumps(explanation, ensure_ascii=False)
            report.error = memory_error
        return self.get_report(round_id)
