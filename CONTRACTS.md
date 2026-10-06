# Contracts

## 1. TranslationRegistry

**Pattern:** fully deterministic — no LLM, no consensus needed.

**Purpose:** the entry gate for every translation. Binds it to the real
transaction sender and requires a genuinely well-formed, fetchable source
URL.

**Public methods**
- `submit_translation(source_url, target_lang, translated_text) -> u256`
- `get_translation_status(translation_id) -> str`
- `get_translation_data(translation_id) -> str` (JSON)
- `list_translations() -> str`
- `get_translator_submissions(translator) -> str`

**Safety properties**
- `translator` is always `gl.message.sender_address`; never a caller-supplied
  parameter.
- An unparseable `source_url`, an empty `target_lang`, or empty
  `translated_text` always reverts before any state is written.

---

## 2. EquivalenceReviewer

**Pattern:** non-deterministic, Equivalence-Principle consensus
(`gl.vm.run_nondet_unsafe`), comparative, 3-field, web-grounded.

**Purpose:** fetches the real source page and judges the submitted
translation against it on three dimensions: does it mean the same thing
(`semantic_equivalence`), does it omit anything significant
(`no_omissions`), and does it add anything not present in the source
(`no_additions`).

**Public methods**
- `review_translation(translation_id) -> bool` — reads the translation from
  `TranslationRegistry` on-chain; can only be called once per translation.
- `get_review_data(translation_id) -> str` (JSON, includes `translator` and
  `source_fetched`)
- `list_reviews() -> str`

**Safety properties**
- The contract fetches `source_url` itself via `gl.nondet.web.render`; the
  translation is judged against the real source, never against the
  translator's own description of it.
- `source_fetched` is reported explicitly: `false` when the source could
  not be loaded (all three judgment fields default to a conservative
  `false` in that case), `true` when it was — making a fetch failure
  visibly different from a genuine negative finding on content that was
  actually read.
- Every validator independently re-fetches the source and re-answers all
  three questions; a mismatch on any single field rejects the leader's
  result outright.
- `review_translation` can only be called once per translation; the record
  is only written after consensus succeeds.

---

## 3. TranslationChallenge

**Pattern:** non-deterministic, Equivalence-Principle consensus, strict
equality on a two-way verdict (`UPHELD` / `OVERTURNED`) — deliberately a
different, narrower pattern than `EquivalenceReviewer`'s multi-field
comparison.

**Purpose:** lets a third party dispute an existing review. The prompt is
grounded in the review's actual recorded fields (never an assumed
"approved"/"rejected" framing), and the contract re-fetches the source
itself rather than trusting the challenger's stated reason.

**Public methods**
- `raise_challenge(translation_id, reason) -> bool`
- `get_challenge_data(translation_id) -> str` (JSON, includes
  `source_fetched`)
- `list_challenges() -> str`

**Safety properties**
- The translator can never challenge their own translation.
- A translation must already be reviewed before it can be challenged; a
  translation can only be challenged once.
- The contract fetches the source page itself, independently of
  `EquivalenceReviewer`'s earlier fetch — a fresh, re-confirmed grounding,
  not a reuse of stored claims.
- `source_fetched` is reported the same way as in `EquivalenceReviewer`.
- Every validator independently re-fetches and re-judges; a mismatch
  rejects the leader's result.

---

## 4. TranslatorReputation

**Pattern:** fully deterministic — combining an already-authenticated
review (or challenge) result into a reputation change is bookkeeping, not
judgment.

**Purpose:** reads the translation's review, and its challenge if one
exists, and adjusts the translator's on-chain reputation.

**Public methods**
- `finalize_translation(translation_id) -> u256`
- `get_reputation(translator) -> str`
- `get_change_details(change_id) -> str` (JSON)
- `list_changes() -> str`

**Safety properties**
- `translator` is read from the review record, never supplied by the caller
  of `finalize_translation`.
- **Refuses to finalize on unfetched evidence:** if the review's (or the
  challenge's) `source_fetched` is `false`, `finalize_translation` reverts
  outright with a clear message rather than silently applying a
  reputation penalty derived from content nobody actually read. This was
  added specifically after a transient Studio fetch outage produced
  all-false reviews indistinguishable from genuine negative findings — see
  [DECISIONS.md](./DECISIONS.md) and [TEST.md](./TEST.md).
- When no challenge exists, the score comes from the review's own three
  fields: `(approvals / 3) * 100`. When a challenge exists and its verdict
  is `UPHELD`, the score still comes from that same formula — never a
  fabricated constant. Only `OVERTURNED` applies a fixed penalty (20),
  since there is no authenticated corrected score to derive from in that
  case.
- `finalize_translation` can only be called once per translation.
- There is no `initialize` method: `self.reputation.get(translator,
  u256(50))` supplies a lazy default of 50 the first time a translator is
  touched, removing any race to claim a translator's starting reputation.
- A change smaller than 10 points reverts (`"Change too small to apply"`)
  rather than being silently applied.
