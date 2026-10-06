# GenLayer Translation Equivalence Network

A 4-contract GenLayer Intelligent Contract suite that reviews translation
quality through decentralized validator consensus, grounded in the real
source page rather than caller-supplied claims. Deployed and tested on both
GenLayer Studio (Studionet) and the public Bradbury testnet.

## Why this exists

A translation review is only trustworthy if it's checked against the actual
source, not against the translator's own description of what the source
says. This suite has every judgment made by GenLayer's decentralized
validators independently fetch the real source page and reach consensus on
it, rather than trusting free text.

Every safety lesson learned across earlier submissions on this account is
applied here: identity is always bound to `gl.message.sender_address`, never
a caller-supplied parameter; no contract ever accepts a JSON blob describing
another contract's result — every downstream read goes to the upstream
contract's own on-chain state; every non-deterministic validator
independently recomputes its judgment from scratch; every stateful action is
guarded against double-application; no contract uses `gl.block.timestamp`;
and no contract holds or transfers real funds. See
[DECISIONS.md](./DECISIONS.md) for the full rationale, including the
`source_fetched` field added specifically to make a fetch failure
distinguishable from a genuine negative finding.

## Architecture

```
TranslationRegistry      deterministic — binds the translator to the real
                          sender, requires a genuinely fetchable source URL
        │
        ▼
EquivalenceReviewer       non-deterministic, comparative, 3-field — fetches
                          the real source page itself and has validators
                          independently agree on semantic_equivalence,
                          no_omissions, and no_additions
        │
        ▼
TranslationChallenge       non-deterministic, strict equality — a third
                          party (never the translator) can dispute a review;
                          re-fetches the source and reaches a two-way
                          verdict: UPHELD or OVERTURNED
        │
        ▼
TranslatorReputation       deterministic — reads either the original review
                          or, if a challenge exists, its final verdict
                          instead, and adjusts the translator's on-chain
                          reputation past a threshold
```

Each contract reads its upstream contract's state directly via
`gl.get_contract_at(Address(...)).view().method(...)`; nothing is ever
passed as a caller-supplied JSON blob standing in for another contract's
result.

## The `source_fetched` safeguard

`EquivalenceReviewer` and `TranslationChallenge` both report a
`source_fetched` boolean alongside their judgment. If the real source page
could not be loaded, this is `false` and every other field defaults to a
conservative negative — this is visibly different from a genuine negative
finding on content that *was* read. `TranslatorReputation.finalize_translation`
refuses to run at all when the review (or the challenge, if one exists) has
`source_fetched: false`, so a fetch outage can never silently produce a
reputation penalty. See [TEST.md](./TEST.md) for the transient Studio fetch
outage that motivated this and how it was resolved.

## Contracts and addresses

Deployed identically on two networks: GenLayer Studio (the primary
functional-testing environment, 21 tests) and the public Bradbury testnet
(live-deployment proof, 3 sanity calls). See [TEST.md](./TEST.md) for every
transaction.

### GenLayer Studio (Studionet)

| # | Contract | Address |
|---|---|---|
| 1 | TranslationRegistry | `0x381f31CFA75a4A81D791fDEb32B928847E0D0c02` |
| 2 | EquivalenceReviewer | `0xd46F053d1B6d521c905CcC21B3aCD7BE689Db31A` |
| 3 | TranslationChallenge | `0x49e619D87E43348C9081d8c6760A6A559e6A6b7C` |
| 4 | TranslatorReputation | `0xFEc4Bb4E4EbD25789D23FA0248C99c16634Ca9bF` |

### Bradbury testnet (via Shipyard)

| # | Contract | Address |
|---|---|---|
| 1 | TranslationRegistry | `0xfad64168266112e2D4E0BBe3a36ab0D3D3890217` |
| 2 | EquivalenceReviewer | `0x130b20878dFfB42d81AaE4b0a0AF44f187655f32` |
| 3 | TranslationChallenge | `0xeb55634E3e20D9438AAB1111f15bA5E78dDB5DBA` |
| 4 | TranslatorReputation | `0x1316F5b0d53455c2A48B500132AF1563ef7776E8` |

See [CONTRACTS.md](./CONTRACTS.md) for per-contract detail and safety
properties, [DECISIONS.md](./DECISIONS.md) for design rationale, and
[tests/](./tests) for integration tests against the Studio addresses above.

## Repo structure

```
contracts/   (4 files)
tests/       (4 files)
README.md
CONTRACTS.md
DECISIONS.md
TEST.md       — full report: 21 Studio tests + 3 Bradbury sanity calls
LICENSE
```
