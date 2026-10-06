# Design Decisions

## Why translations are judged against a fetched source, never caller text

An earlier submission on this account was rejected partly because a
judgment was derived only from a caller-supplied description rather than
evidence the contract acquired itself. `EquivalenceReviewer` and
`TranslationChallenge` both fetch the real source page via
`gl.nondet.web.render` and judge the translation against that fetched
content — never against a translator's own claim about what the source
says.

## Why review and challenge use three fixed yes/no fields and a two-way verdict, not a continuous score

A separate earlier rejection was specifically about a continuous 0-100
score with a tolerance band: the same real contribution could validly
cross an approval threshold in either direction depending on which
in-tolerance value a leader happened to report. Every judgment in this
suite is either a fixed yes/no field (`EquivalenceReviewer`) or a two-way
verdict (`TranslationChallenge`) — both matched by strict equality across
independent validators, with no window of "close enough" values. There is
no threshold that the same real translation could cross differently
depending on which valid-looking number came back.

## Why TranslationChallenge's OVERTURNED penalty is a fixed constant, not derived

When a challenge is `UPHELD`, `TranslatorReputation` uses the exact same
score formula as the no-challenge path, computed from the review's own
authenticated fields — never a fabricated number. `OVERTURNED` is the one
case where there is no authenticated "corrected" score to derive from (the
original review's finding was wrong, but nothing re-measured the
translation on a 0-3 scale), so a fixed, conservative penalty (20) applies
instead. This is a deliberate, narrow exception — not a general pattern of
inventing scores — and it still can't be used to inflate a score, only to
penalize an overturned review.

## Why `source_fetched` was added

During Studio testing, `gl.nondet.web.render` returned empty content on
every attempt across five different, previously-reliable source URLs
(python.org, wikipedia.org, example.com), and every independent validator
agreed on the same empty result — a transient infrastructure condition on
Studionet at that time, not a contract defect or a domain-specific issue
(the same domains had fetched successfully in earlier, separate
submissions on this account). Before this field existed, that outage was
indistinguishable from a genuinely bad translation: both produced
`semantic_equivalence: false`. `source_fetched` makes the two cases
visibly different, and `TranslatorReputation` now refuses to finalize at
all when it's `false` on the review or the challenge — so a fetch outage
can never silently produce a reputation penalty again. See
[TEST.md](./TEST.md) for the full sequence: the outage, the fix, and its
empirical verification on both Studio and Bradbury.

## Why the suite was deployed on both Studio and Bradbury

GenLayer's own documentation lists a live deployment and a Shipyard
deployment as evidence that specifically earns additional points on top of
the base contribution, separate from functional testing in Studio.
Deploying identically on the public Bradbury testnet also happened to
directly re-verify the `source_fetched` fix on a second, independent
network — `source_fetched: true` on Bradbury's very first review call
confirms the fetch capability (and the fix) both work outside the Studio
sandbox, not just within it.

## Why downstream contracts read on-chain state instead of accepting JSON

An earlier submission was rejected specifically because downstream
contracts trusted a JSON string supplied by the caller instead of the
verifying contract's own authenticated output. Every read here goes
directly to the upstream contract's own state via
`gl.get_contract_at(Address(...)).view().method(...)`. No contract in this
suite ever accepts a JSON blob describing another contract's result from a
caller.

## Why `translator`/`challenger` are always `gl.message.sender_address`

A related earlier gap: even after contracts started reading real on-chain
data, an identity field was still sometimes accepted as a caller-supplied
parameter. Here, `translator` is captured once, in
`TranslationRegistry.submit_translation`, and threaded through every
downstream read from there; `challenger` is captured the same way in
`TranslationChallenge.raise_challenge`. Neither is ever taken as a
parameter further down the chain.

## Why every stateful action is guarded against double-application

`review_translation`, `raise_challenge`, and `finalize_translation` each
check a membership map before doing any consensus or state work, and only
mark that map after a fully successful run — so a translation can be
reviewed, challenged, and finalized exactly once, and a reverted attempt
never "consumes" the record it was processing.

## Why helper logic lives in module-level functions, not undecorated instance methods

GenLayer Studio fails to load a contract's schema if a `gl.Contract`
subclass has any plain instance method without a `@gl.public.write` or
`@gl.public.view` decorator. All shared logic (`clean_url`,
`is_valid_url`, `ask_yes_no`, `review_translation`, `ask_verdict`) is
implemented as a module-level function instead of a method on `self`.

## Why no contract uses `gl.block.timestamp`

This attribute does not exist in the GenLayer SDK version used across
every contract on this account. No time-based logic is used anywhere in
this suite.

## Why no contract holds or transfers funds

This suite never needed to; avoiding fund custody entirely removes a whole
class of risk (locked deposits, untested value-transfer APIs) that caused
repeated rejection cycles on an earlier escrow-style project on this
account.
