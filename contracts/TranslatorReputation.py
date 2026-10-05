# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json

from genlayer import *
from dataclasses import dataclass


@allow_storage
@dataclass
class ReputationChange:
    change_id: u256
    translator: str
    translation_id: u256
    final_score: u256
    source: str  # REVIEW, CHALLENGE
    change_type: str  # INCREASE, DECREASE


class TranslatorReputation(gl.Contract):
    changes: TreeMap[u256, ReputationChange]
    finalized: TreeMap[u256, bool]
    reputation: TreeMap[str, u256]
    next_id: u256
    reviewer_contract: str
    challenge_contract: str

    def __init__(self, reviewer_address: str, challenge_address: str):
        self.next_id = u256(0)
        self.reviewer_contract = reviewer_address
        self.challenge_contract = challenge_address
        # No initialize method: reputation.get(translator, u256(50)) below is
        # a lazy default, removing any race to claim a translator's starting
        # reputation.

    @gl.public.write
    def finalize_translation(self, translation_id: u256) -> u256:
        assert translation_id not in self.finalized, "Translation already finalized"

        review_raw = gl.get_contract_at(
            Address(self.reviewer_contract)
        ).view().get_review_data(translation_id)
        assert review_raw != "NOT_FOUND", "Translation has not been reviewed yet"

        try:
            review = json.loads(review_raw)
        except:
            raise gl.vm.UserError("Invalid data from reviewer")

        assert review.get("source_fetched", False), \
            "Source could not be fetched during review — cannot finalize without real evidence"

        translator = review.get("translator", "")
        assert translator != "", "Translator not found in review record"

        approvals = sum([
            review.get("semantic_equivalence", False),
            review.get("no_omissions", False),
            review.get("no_additions", False),
        ])
        review_score = int((approvals / 3) * 100)

        challenge_raw = gl.get_contract_at(
            Address(self.challenge_contract)
        ).view().get_challenge_data(translation_id)

        if challenge_raw != "NOT_FOUND":
            try:
                challenge = json.loads(challenge_raw)
            except:
                raise gl.vm.UserError("Invalid data from challenge contract")
            assert challenge.get("status", "") == "FINAL", "Challenge has not been finalized"
            assert challenge.get("source_fetched", False), \
                "Source could not be fetched during the challenge — cannot finalize without real evidence"

            if challenge.get("verdict", "") == "OVERTURNED":
                # The original review's finding was wrong; a fixed low penalty
                # applies since there is no authenticated corrected score to
                # derive from.
                final_score = 20
            else:
                # UPHELD means the original review's finding stands, so the
                # score comes from that SAME authenticated review data used
                # in the no-challenge path below, never a fabricated constant.
                final_score = review_score
            source = "CHALLENGE"
        else:
            final_score = review_score
            source = "REVIEW"

        current_reputation = self.reputation.get(translator, u256(50))
        new_score = u256(final_score)

        if new_score > current_reputation + u256(10):
            change_type = "INCREASE"
        elif new_score < current_reputation - u256(10):
            change_type = "DECREASE"
        else:
            raise gl.vm.UserError("Change too small to apply")

        self.reputation[translator] = new_score
        self.finalized[translation_id] = True

        cid = self.next_id
        self.next_id += u256(1)
        self.changes[cid] = ReputationChange(
            change_id=cid,
            translator=translator,
            translation_id=translation_id,
            final_score=u256(final_score),
            source=source,
            change_type=change_type,
        )
        return cid

    @gl.public.view
    def get_reputation(self, translator: str) -> str:
        return f"REPUTATION:{int(self.reputation.get(translator, u256(50)))}"

    @gl.public.view
    def get_change_details(self, change_id: u256) -> str:
        if change_id not in self.changes:
            return "NOT_FOUND"
        c = self.changes[change_id]
        return json.dumps({
            "change_id": int(c.change_id),
            "translator": c.translator,
            "translation_id": int(c.translation_id),
            "final_score": int(c.final_score),
            "source": c.source,
            "change_type": c.change_type,
        })

    @gl.public.view
    def list_changes(self) -> str:
        items = []
        for key in self.changes:
            c = self.changes[key]
            items.append(f"{int(c.change_id)}:{c.change_type}")
        return ",".join(items)
