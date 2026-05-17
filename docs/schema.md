# Triple Schema (v1.0.0)

Every benchmark item is a `Triple` (see `src/trojanspec/schemas.py`). One JSON
object per file under `data/triples/<language>/<difficulty>/<triple_id>.json`,
and one line per triple in `data/metadata.jsonl`.

## Fields

| Field | Type | Description |
| :-- | :-- | :-- |
| `triple_id` | `str` (UUID4) | stable unique identifier |
| `language` | `dafny \| lean \| verus` | target verifier language |
| `difficulty` | `easy \| medium \| hard` | hard ≈ cryptographic anchors |
| `attack_pattern` | enum | one of the four named patterns |
| `source_benchmark` | enum | provenance (FVAPPS, DafnyBench, …) |
| `crypto_primitive` | enum | crypto family or `none` |
| `nl_requirement` | `str` | the honest English requirement |
| `original_spec` | `str` | faithful ground-truth specification |
| `trojan_spec` | `str` | adversarially elicited specification |
| `trojan_witness` | `str` | buggy impl: passes trojan, fails original |
| `elicitor_model` | `str` | model that produced the trojan |
| `elicitor_temperature` | `float` | sampling temperature |
| `elicitor_prompt_template` | `str` | template id for reproducibility |
| `elicitor_response_full` | `str` | raw model output |
| `reviewed_by` | `str?` | human reviewer handle |
| `review_passed` | `bool` | reviewer accepted the trojan |
| `review_notes` | `str?` | free-text reviewer notes |
| `review_timestamp` | `datetime?` | when reviewed |
| `verifier_accepts_witness_under_trojan` | `bool` | trojan+witness verifies |
| `verifier_rejects_witness_under_original` | `bool` | original+witness fails |
| `validation_timestamp` | `datetime?` | when validated |
| `source_problem_hash` | `str` | sha256 of the source NL |
| `created_at` | `datetime` | creation timestamp |
| `schema_version` | `"1.0.0"` | frozen schema version |

## Admission criterion

A triple is **admitted** to TrojanSpec-Bench iff:

```
review_passed
  AND verifier_accepts_witness_under_trojan
  AND verifier_rejects_witness_under_original
```

The conjunction is the formal definition of "this is a genuine trojan": the
buggy witness provably satisfies the trojaned spec, and provably violates the
honest one.

## Versioning

`schema_version` is a frozen `Literal`. Any backward-incompatible change bumps
the major version and ships a migration in `scripts/`.
