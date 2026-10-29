# Decentralized AI Auditor

A [GenLayer](https://www.genlayer.com) Intelligent Contract that audits AI-generated claims against web sources, records each verdict with evidence and a confidence level, and keeps a tamper-evident audit history.

- **Contract:** `contracts/decentralized_ai_auditor.py` (about 19.9 KB; header `py-genlayer:test`, for GenLayer Studio)
- **Studio address (tested):** `0xd3E17a9E243C6A275d652a6c1142eADbf944B0bB`
- **Bradbury address:** `0x65aA3ce55c9Bc1895586021A20F0Be4dAa674096` (deployed earlier; transactions were not processing, so testing was done on Studio)

## How consensus works

The decision is made **before** consensus, so nothing that influences the stored result is applied afterwards.

1. Every validator fetches the sources and asks an LLM for a verdict, confidence and evidence quotes.
2. The deterministic policy (`apply_policy`) runs inside that same non-deterministic block: it drops quotes that are not verbatim on the page, enforces verdict/evidence consistency, applies confidence caps, and maps confidence to a band.
3. The leader returns the final record fields. A custom validator (`gl.vm.run_nondet`) accepts only if:
   - the leader result is exactly what `apply_policy` would produce (no forged or un-banded fields),
   - every evidence quote appears verbatim in the validator's own fetch of that source,
   - `verdict`, `confidence` and `source_status` equal the validator's own final result exactly.
4. The accepted result is stored as-is. No post-consensus step can change the verdict, confidence or dispute outcome.

### Confidence bands

Confidence is stored as a band floor: `0` (low, under 60), `60` (medium, 60-79) or `80` (high, 80-100). The dispute-overturn threshold (60) is a band edge, so validators whose raw confidences fall on opposite sides of it land in different bands and do not reach consensus. Confidence caps (30, 60, 70, 80) are applied deterministically before banding. Evidence quote choice may differ between validators; anything that changes the final verdict or confidence band is bound.

Quote verification ignores case, punctuation and whitespace and matches whole words; HTML tags are stripped and entities (`&nbsp;`, `&#160;`, `&amp;`...) are decoded before judging.

## Verdicts

| Verdict | Meaning |
|---|---|
| SUPPORTED | Sources establish the whole claim |
| PARTIALLY_SUPPORTED | Some parts established, others missing |
| UNSUPPORTED | Sources relevant but do not establish it |
| CONTRADICTED | Sources conflict with the claim |
| INCONCLUSIVE | Sources unavailable, irrelevant or insufficient |

Record kinds: `AUDIT`, `REAUDIT`, `DISPUTE_REVIEW`. Statuses: `ACTIVE`, `SUPERSEDED`, `OVERTURNED`, `DISPUTE_REJECTED`. Exactly one record per claim is `ACTIVE`; status lives outside the hashed record.

## Methods

Write: `submit_audit(claim, sources, context)`, `request_reaudit(audit_id, extra_sources, context)` (pass `""` for an empty context), `file_dispute(audit_id, reason, extra_sources)`, and owner-only `set_paused`, `set_strict_sources`, `add_trusted_domain`, `remove_trusted_domain`, `transfer_ownership`.

Read: `get_audit`, `get_claim_history`, `get_active_audit`, `verify_audit`, `verify_chain`, `get_stats` (includes owner, chain head, verdict counts, config). Iterate `get_audit(1..total_records)` to walk the full history; disputes appear in `get_claim_history` as `DISPUTE_REVIEW` records with a `parent_id`.

## Rules and limits

| Rule | Value |
|---|---|
| Claim / context / dispute reason | 10-1000 / up to 500 / 20-800 characters |
| Sources per audit | 1-5, https only, public DNS names, port 443 |
| Max revisions per claim | 5 |
| Max disputes per audit | 3, one per address |
| Records per address | 500 |
| Dispute overturns only if | new verdict differs, is not INCONCLUSIVE, confidence band >= 60 |

Caps: single evidence 80; no trusted-domain evidence (when a trust list exists) 70; UNSUPPORTED without quotes 60; downgraded to INCONCLUSIVE 30.

## Integrity

Each record is canonical JSON containing `prev_hash`; `entry_hash = sha256(record)`. Records are never edited or deleted. `verify_audit` and `verify_chain` recompute the chain on demand.

## Anti-manipulation

Strict input validation, blocked hosts (localhost, IPs, `.local`/`.internal`), prompt-injection screening of claims, context and reasons, redaction of injection phrases in fetched pages, untrusted-data delimiters in the prompt, verbatim-evidence rule, per-address quotas, revision and dispute limits. The owner can pause and manage trusted domains but cannot edit or delete records.

## Errors

`UserError("[CODE] message")`: `PAUSED`, `FORBIDDEN`, `INVALID_INPUT`, `NOT_FOUND`, `CONFLICT`, `LIMIT`, `UNTRUSTED_SOURCE`, `CONSENSUS_FAILED`.

## Tests

```
python -m unittest discover -s tests -v
```

72 tests run against a fake `genlayer` module (`tests/harness.py`) with mocked web and LLM calls, including a leader/validator simulation that checks forged results, band-boundary disagreement and dispute-threshold disagreement are rejected. They do not exercise real validator networks; use `STUDIO_TEST_GUIDE.md` for on-chain testing.

## Notes

LLM verdicts can vary between runs. Near a band edge, validators may fail to agree and the transaction can be retried. No payment, swapping or trading functionality.
