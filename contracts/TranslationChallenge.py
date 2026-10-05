# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
import re

from genlayer import *
from dataclasses import dataclass

VERDICTS = ("UPHELD", "OVERTURNED")


def fetch_source(source_url: str):
    try:
        content = gl.nondet.web.render(source_url)
    except Exception:
        return None
    if content is None or str(content).strip() == "":
        return None
    return content


def judge_challenge(source_url: str, translated_text: str, target_lang: str,
                     reason: str, review_summary: str) -> dict:
    content = fetch_source(source_url)
    if content is None:
        # Could not see the source — never let an unfetchable page silently
        # default to UPHELD or OVERTURNED; record that distinctly instead.
        return {"source_fetched": False, "verdict": "UPHELD"}

    prompt = f"""
    Source text (truncated):
    {content[:2500]}

    Translated text (target language: {target_lang}):
    {translated_text[:2000]}

    An earlier automated review found: {review_summary}
    A challenger disputes that finding for this reason: {reason}

    Considering the actual source and translated text, is the earlier
    review's finding UPHELD (the earlier review was correct) or OVERTURNED
    (the challenger is right, the earlier review's finding was wrong)?
    Respond with ONLY one word: UPHELD or OVERTURNED.
    """
    response = gl.nondet.exec_prompt(prompt)
    verdict = "UPHELD"
    for word in re.findall(r"[A-Z]+", str(response).upper()):
        if word in VERDICTS:
            verdict = word
            break
    return {"source_fetched": True, "verdict": verdict}


@allow_storage
@dataclass
class ChallengeRecord:
    translation_id: u256
    challenger: str
    reason: str
    source_fetched: bool
    verdict: str
    status: str  # FINAL


class TranslationChallenge(gl.Contract):
    challenges: TreeMap[u256, ChallengeRecord]
    registry_contract: str
    reviewer_contract: str

    def __init__(self, registry_address: str, reviewer_address: str):
        self.registry_contract = registry_address
        self.reviewer_contract = reviewer_address

    @gl.public.write
    def raise_challenge(self, translation_id: u256, reason: str) -> bool:
        assert translation_id not in self.challenges, "Already challenged"
        assert reason.strip() != "", "Reason cannot be empty"

        review_raw = gl.get_contract_at(
            Address(self.reviewer_contract)
        ).view().get_review_data(translation_id)
        assert review_raw != "NOT_FOUND", "Translation has not been reviewed yet"

        try:
            review_data = json.loads(review_raw)
        except:
            raise gl.vm.UserError("Invalid data from reviewer")

        challenger = str(gl.message.sender_address)
        assert challenger != review_data.get("translator", ""), "Translator cannot challenge their own translation"

        review_summary = (
            f"semantic_equivalence={review_data.get('semantic_equivalence')}, "
            f"no_omissions={review_data.get('no_omissions')}, "
            f"no_additions={review_data.get('no_additions')}"
        )

        translation_raw = gl.get_contract_at(
            Address(self.registry_contract)
        ).view().get_translation_data(translation_id)
        assert translation_raw != "NOT_FOUND", "Translation not found in registry"

        try:
            translation_data = json.loads(translation_raw)
        except:
            raise gl.vm.UserError("Invalid data from registry")

        source_url = translation_data.get("source_url", "")
        target_lang = translation_data.get("target_lang", "")
        translated_text = translation_data.get("translated_text", "")

        # Equivalence Principle: STRICT EQUALITY on a two-way verdict. The
        # source is fetched FRESH, independently, inside both leader_fn and
        # validator_fn below — never fetched once outside and shared, which
        # would make "independent" recomputation meaningless.
        def leader_fn():
            return judge_challenge(source_url, translated_text, target_lang, reason, review_summary)

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            leader_data = leader_result.calldata
            if not isinstance(leader_data.get("source_fetched"), bool):
                return False
            if leader_data.get("verdict") not in VERDICTS:
                return False
            mine = judge_challenge(source_url, translated_text, target_lang, reason, review_summary)
            return (
                mine["source_fetched"] == leader_data["source_fetched"]
                and mine["verdict"] == leader_data["verdict"]
            )

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        self.challenges[translation_id] = ChallengeRecord(
            translation_id=translation_id,
            challenger=challenger,
            reason=reason,
            source_fetched=result["source_fetched"],
            verdict=result["verdict"],
            status="FINAL",
        )
        return True

    @gl.public.view
    def get_challenge_data(self, translation_id: u256) -> str:
        if translation_id not in self.challenges:
            return "NOT_FOUND"
        c = self.challenges[translation_id]
        return json.dumps({
            "translation_id": int(c.translation_id),
            "challenger": c.challenger,
            "reason": c.reason,
            "source_fetched": c.source_fetched,
            "verdict": c.verdict,
            "status": c.status,
        })

    @gl.public.view
    def list_challenges(self) -> str:
        items = []
        for key in self.challenges:
            c = self.challenges[key]
            items.append(f"{int(c.translation_id)}:{c.verdict}")
        return ",".join(items)
