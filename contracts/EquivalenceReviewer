# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
import re

from genlayer import *
from dataclasses import dataclass


def ask_yes_no(source_content: str, translated_text: str, target_lang: str, question: str) -> bool:
    prompt = f"""
    Source text (truncated):
    {source_content[:2500]}

    Translated text (target language: {target_lang}):
    {translated_text[:2000]}

    Question: {question}
    Respond with ONLY: YES or NO
    """
    response = gl.nondet.exec_prompt(prompt)
    for word in re.findall(r"[A-Z]+", str(response).upper()):
        if word in ("YES", "NO"):
            return word == "YES"
    return False


def review_translation(source_url: str, translated_text: str, target_lang: str) -> dict:
    try:
        content = gl.nondet.web.render(source_url)
    except:
        content = ""
    if content.strip() == "":
        return {"semantic_equivalence": False, "no_omissions": False, "no_additions": False}

    return {
        "semantic_equivalence": ask_yes_no(
            content, translated_text, target_lang,
            "Does the translated text convey the same meaning as the source text?",
        ),
        "no_omissions": ask_yes_no(
            content, translated_text, target_lang,
            "Does the translated text omit no significant information present in the source text?",
        ),
        "no_additions": ask_yes_no(
            content, translated_text, target_lang,
            "Does the translated text avoid adding information that is not present in the source text?",
        ),
    }


@allow_storage
@dataclass
class ReviewRecord:
    translation_id: u256
    translator: str
    semantic_equivalence: bool
    no_omissions: bool
    no_additions: bool
    status: str  # REVIEWED


class EquivalenceReviewer(gl.Contract):
    reviews: TreeMap[u256, ReviewRecord]
    registry_contract: str

    def __init__(self, registry_address: str):
        self.registry_contract = registry_address

    @gl.public.write
    def review_translation(self, translation_id: u256) -> bool:
        assert translation_id not in self.reviews, "Already reviewed"

        raw = gl.get_contract_at(
            Address(self.registry_contract)
        ).view().get_translation_data(translation_id)
        assert raw != "NOT_FOUND", "Translation not found in registry"

        try:
            data = json.loads(raw)
        except:
            raise gl.vm.UserError("Invalid data from registry")

        translator = data.get("translator", "")
        source_url = data.get("source_url", "")
        target_lang = data.get("target_lang", "")
        translated_text = data.get("translated_text", "")
        assert translator != "", "Translator not found in translation record"

        # Equivalence Principle: COMPARATIVE, multi-field. The contract fetches
        # the actual source page itself; the translation is judged against the
        # real source, not against the translator's own description of it.
        def leader_fn():
            return review_translation(source_url, translated_text, target_lang)

        def validator_fn(leader_result):
            if not isinstance(leader_result, gl.vm.Return):
                return False
            leader_data = leader_result.calldata
            for field in ("semantic_equivalence", "no_omissions", "no_additions"):
                if not isinstance(leader_data.get(field), bool):
                    return False
            mine = review_translation(source_url, translated_text, target_lang)
            return (
                mine["semantic_equivalence"] == leader_data["semantic_equivalence"]
                and mine["no_omissions"] == leader_data["no_omissions"]
                and mine["no_additions"] == leader_data["no_additions"]
            )

        result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

        self.reviews[translation_id] = ReviewRecord(
            translation_id=translation_id,
            translator=translator,
            semantic_equivalence=result["semantic_equivalence"],
            no_omissions=result["no_omissions"],
            no_additions=result["no_additions"],
            status="REVIEWED",
        )
        return True

    @gl.public.view
    def get_review_data(self, translation_id: u256) -> str:
        if translation_id not in self.reviews:
            return "NOT_FOUND"
        r = self.reviews[translation_id]
        return json.dumps({
            "translation_id": int(r.translation_id),
            "translator": r.translator,
            "semantic_equivalence": r.semantic_equivalence,
            "no_omissions": r.no_omissions,
            "no_additions": r.no_additions,
            "status": r.status,
        })

    @gl.public.view
    def list_reviews(self) -> str:
        items = []
        for key in self.reviews:
            r = self.reviews[key]
            items.append(f"{int(r.translation_id)}:{r.status}")
        return ",".join(items)
