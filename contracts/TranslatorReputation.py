# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
import datetime as _dt

from genlayer import *
from dataclasses import dataclass

CHANGE_MARGIN = 10


def now_ts() -> int:
    """Block time of the current transaction in whole seconds."""
    raw = None
    try:
        raw = gl.message.datetime
    except Exception:
        raw = None
    if raw is None:
        try:
            raw = gl.message_raw["datetime"]
        except Exception:
            raw = None
    assert raw is not None, "Block time is not available"
    if isinstance(raw, str):
        parsed = _dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    else:
        parsed = raw
    return int(parsed.timestamp())


def score_from_fields(a: bool, b: bool, c: bool) -> int:
    """0, 33, 66 or 100 from three yes/no checks. Integer math only."""
    approvals = (1 if a else 0) + (1 if b else 0) + (1 if c else 0)
    return (approvals * 100) // 3


def classify_change(current: int, new_score: int) -> str:
    """Compares using only additions, never a subtraction, so it is safe for
    any current value (for example 5) with no unsigned underflow."""
    if new_score > current + CHANGE_MARGIN:
        return "INCREASE"
    if new_score + CHANGE_MARGIN < current:
        return "DECREASE"
    return "UNCHANGED"


@allow_storage
@dataclass
class ReputationChange:
    change_id: u256
    translator: str
    translation_id: u256
    final_score: u256
    previous_reputation: u256
    new_reputation: u256
    source: str       # REVIEW, CHALLENGE
    outcome: str      # REVIEW_UNCHALLENGED, CHALLENGE_UPHELD, CHALLENGE_OVERTURNED
    change_type: str  # INCREASE, DECREASE, UNCHANGED
    finalized_at: u256


class TranslatorReputation(gl.Contract):
    changes: TreeMap[u256, ReputationChange]
    finalized: TreeMap[u256, bool]
    reputation: TreeMap[str, u256]
    next_id: u256
    reviewer_contract: str
    challenge_contract: str
    start_score: u256

    def __init__(self, reviewer_address: str, challenge_address: str, start_score: u256):
        assert int(start_score) <= 100, "Start score above 100"
        self.next_id = u256(0)
        self.reviewer_contract = reviewer_address
        self.challenge_contract = challenge_address
        self.start_score = start_score

    @gl.public.write
    def finalize_translation(self, translation_id: u256) -> u256:
        assert translation_id not in self.finalized, "Translation already finalized"

        review_raw = gl.get_contract_at(
            Address(self.reviewer_contract)
        ).view().get_review_data(translation_id)
        assert review_raw != "NOT_FOUND", "Translation has not been reviewed yet"

        try:
            review = json.loads(review_raw)
        except Exception:
            raise gl.vm.UserError("Invalid data from reviewer")

        translator = review.get("translator", "")
        assert translator != "", "Translator not found in review record"

        challenge_raw = gl.get_contract_at(
            Address(self.challenge_contract)
        ).view().get_challenge_data(translation_id)

        now = now_ts()

        if challenge_raw == "NOT_FOUND":
            # No challenge exists. The review result only becomes final after
            # the challenge window has fully closed, so finalizing early can
            # never skip a challenge. A challenge cannot be opened after the
            # deadline, so the two ranges never overlap.
            assert now > int(review.get("challenge_deadline", 0)), \
                "Challenge window is still open - result is not final yet"
            # An unreadable source at review time is not evidence. The
            # translation can still be rescued by a challenge, whose
            # independent judgment needs a readable source.
            assert review.get("source_fetched", False), \
                "Source could not be fetched during review - cannot finalize without real evidence"
            final_score = score_from_fields(
                bool(review.get("semantic_equivalence", False)),
                bool(review.get("no_omissions", False)),
                bool(review.get("no_additions", False)),
            )
            source = "REVIEW"
            outcome = "REVIEW_UNCHALLENGED"
        else:
            try:
                challenge = json.loads(challenge_raw)
            except Exception:
                raise gl.vm.UserError("Invalid data from challenge contract")
            assert challenge.get("status", "") == "FINAL", "Challenge has not been finalized"
            assert challenge.get("source_fetched", False), \
                "Source could not be fetched during the challenge - cannot finalize without real evidence"

            # The independently validated corrected fields replace the
            # original review in BOTH cases. An overturn can therefore raise
            # or lower the score depending on which way the review was wrong.
            final_score = score_from_fields(
                bool(challenge.get("corrected_semantic_equivalence", False)),
                bool(challenge.get("corrected_no_omissions", False)),
                bool(challenge.get("corrected_no_additions", False)),
            )
            source = "CHALLENGE"
            outcome = "CHALLENGE_" + str(challenge.get("verdict", ""))

        # Lazy default: a translator with no record starts at start_score.
        if translator in self.reputation:
            current = int(self.reputation[translator])
        else:
            current = int(self.start_score)
        change_type = classify_change(current, final_score)

        # Reputation only moves when the change is larger than the margin.
        # A small change is recorded as UNCHANGED instead of reverting, so a
        # translation can always be finalized.
        new_reputation = final_score if change_type != "UNCHANGED" else current

        self.reputation[translator] = u256(new_reputation)
        self.finalized[translation_id] = True

        cid = self.next_id
        self.next_id += u256(1)
        self.changes[cid] = ReputationChange(
            change_id=cid,
            translator=translator,
            translation_id=translation_id,
            final_score=u256(final_score),
            previous_reputation=u256(current),
            new_reputation=u256(new_reputation),
            source=source,
            outcome=outcome,
            change_type=change_type,
            finalized_at=u256(now),
        )
        return cid

    @gl.public.view
    def get_reputation(self, translator: str) -> str:
        if translator in self.reputation:
            current = int(self.reputation[translator])
        else:
            current = int(self.start_score)
        return f"REPUTATION:{current}"

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
            "previous_reputation": int(c.previous_reputation),
            "new_reputation": int(c.new_reputation),
            "source": c.source,
            "outcome": c.outcome,
            "change_type": c.change_type,
            "finalized_at": int(c.finalized_at),
        })

    @gl.public.view
    def get_lifecycle(self, translation_id: u256) -> str:
        """Current stage. Compare challenge_deadline with the current time:
        challengeable until the deadline, finalizable without a challenge
        only after it."""
        if translation_id in self.finalized:
            return json.dumps({"stage": "FINALIZED"})

        review_raw = gl.get_contract_at(
            Address(self.reviewer_contract)
        ).view().get_review_data(translation_id)
        if review_raw == "NOT_FOUND":
            return json.dumps({"stage": "NOT_REVIEWED"})
        review = json.loads(review_raw)

        challenge_raw = gl.get_contract_at(
            Address(self.challenge_contract)
        ).view().get_challenge_data(translation_id)
        if challenge_raw == "NOT_FOUND":
            return json.dumps({
                "stage": "REVIEWED_CHALLENGEABLE_UNTIL_DEADLINE",
                "challenge_deadline": int(review["challenge_deadline"]),
            })
        challenge = json.loads(challenge_raw)
        return json.dumps({
            "stage": "CHALLENGE_FINAL_READY_TO_FINALIZE",
            "verdict": challenge["verdict"],
        })

    @gl.public.view
    def list_changes(self) -> str:
        items = []
        for key in self.changes:
            c = self.changes[key]
            items.append(f"{int(c.change_id)}:{c.change_type}")
        return ",".join(items)
