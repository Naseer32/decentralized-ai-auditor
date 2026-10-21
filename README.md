# Decentralized AI Auditor

A [GenLayer](https://www.genlayer.com) Intelligent Contract that audits AI-generated claims against web sources, records each verdict with evidence and a confidence level, and keeps a tamper-evident audit history.

- **Contract:** `contracts/decentralized_ai_auditor.py` (about 19.9 KB, under the 20 KB Bradbury size limit)
- **Deployed address:** `0x65aA3ce55c9Bc1895586021A20F0Be4dAa674096` (GenLayer Bradbury testnet)

## How it works

1. A caller submits a claim and 1-5 public https source URLs.
2. Each validator independently fetches the sources and asks an LLM to judge the claim.
3. Consensus uses `gl.eq_principle.prompt_comparative`: verdicts must match exactly and confidence must be within 15 points.
4. A deterministic policy validates the result, applies caps, and stores a hash-chained record.

Evidence quotes must be exact substrings of the fetched page. Fabricated quotes are dropped and the verdict is downgraded.

## Verdicts

| Verdict | Meaning |
|---|---|
| SUPPORTED | Sources establish the whole claim |
| PARTIALLY_SUPPORTED | Some parts established, others missing or overstated |
| UNSUPPORTED | Sources are relevant but do not establish the claim |
| CONTRADICTED | Sources conflict with the claim |
| INCONCLUSIVE | Sources unavailable, irrelevant or insufficient |

## Record kinds and statuses

- Kinds: `AUDIT`, `REAUDIT`, `DISPUTE_REVIEW`
- Statuses: `ACTIVE`, `SUPERSEDED`, `OVERTURNED`, `DISPUTE_REJECTED`
- Exactly one record per claim is `ACTIVE`. Status lives outside the hashed record, so history is never rewritten.

## Methods

Write methods:

| Method | Purpose |
|---|---|
| `submit_audit(claim, sources, context="")` | First audit of a claim. Returns the audit id |
| `request_reaudit(audit_id, extra_sources, context="")` | New version of the ACTIVE audit, optionally with more sources |
| `file_dispute(audit_id, reason, extra_sources)` | Independent re-evaluation. Returns outcome `UPHELD` or `OVERTURNED` |
| `set_paused(paused)` | Owner: pause or resume writes |
| `set_strict_sources(strict)` | Owner: only allow trusted domains |
| `add_trusted_domain(domain)` | Owner: trust a domain (subdomains included) |
| `remove_trusted_domain(domain)` | Owner: remove a trusted domain |
| `transfer_ownership(new_owner)` | Owner: hand over ownership |

Read methods: `get_audit`, `get_claim_id`, `get_claim_history`, `get_active_audit`, `get_disputes`, `list_audits`, `verify_audit`, `verify_chain`, `get_stats` (includes owner, chain head, verdict counts and config).

## Rules and limits

| Rule | Value |
|---|---|
| Claim length | 10-1000 characters |
| Context length | up to 500 characters |
| Dispute reason | 20-800 characters |
| Sources per audit | 1-5, https only, public DNS names, port 443 |
| Max revisions per claim | 5 |
| Max disputes per audit | 3, and one per address |
| Records per address | 500 |
| Dispute overturns an audit only if | new verdict differs, is not INCONCLUSIVE, confidence >= 60 |

Confidence caps: single evidence item 80; no trusted-domain evidence (when a trust list exists) 70; UNSUPPORTED without quotes 60; verdict downgraded to INCONCLUSIVE because of missing or mismatched evidence 30.

## Integrity

Each record is canonical JSON containing `prev_hash`. `entry_hash = sha256(record)`. Records are never edited or deleted. `verify_audit` and `verify_chain` recompute the chain on demand, and `get_stats().chain_head` shows the latest hash.

## Anti-manipulation

- Strict input validation (types, lengths, URL rules, blocked hosts such as localhost, IP addresses and `.local`/`.internal` names)
- Prompt-injection screening of claims, context and dispute reasons
- Injection phrases inside fetched pages are redacted
- Claim, context and sources are delimited as untrusted data in the prompt
- Evidence must be verbatim from the fetched page
- Verdict and evidence must be consistent, otherwise the verdict is downgraded
- Per-address quotas, revision and dispute limits
- The owner can pause the contract and manage trusted domains but cannot edit or delete records

## Errors

Errors are raised as `UserError("[CODE] message")`. Codes: `PAUSED`, `FORBIDDEN`, `INVALID_INPUT`, `NOT_FOUND`, `CONFLICT`, `LIMIT`, `UNTRUSTED_SOURCE`, `CONSENSUS_FAILED`.

## Tests

```
python -m unittest discover -s tests -v
```

56 tests run against a fake `genlayer` module (`tests/harness.py`) with mocked web and LLM calls. They cover all contract logic but not real validator consensus. For on-chain testing, follow `STUDIO_TEST_GUIDE.md` (written in Hausa).

## Deploy

1. Open GenLayer Studio and add `contracts/decentralized_ai_auditor.py`.
2. Deploy with no constructor arguments.
3. Test using `STUDIO_TEST_GUIDE.md`.

## Notes

- LLM verdicts can vary slightly between runs. Validation errors, statuses and the hash chain are deterministic.
- There is no payment, swapping or trading functionality.
