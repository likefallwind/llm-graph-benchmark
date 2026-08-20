# Submission adapter guide

An extractor adapter has one responsibility: convert one immutable extraction run into a valid
`submission.json`. It must not call benchmark judges or modify the graph while exporting.

## Required mapping

| Benchmark field | Extractor responsibility |
|---|---|
| `document_id` | Match the frozen benchmark document ID exactly. |
| `entity.id` | Stable only inside this submission and document. |
| `entity.name` | Canonical display name selected by the extractor. |
| `entity.definition` | Meaning represented by this node, not an evaluator-written definition. |
| `entity.evidence` | Source units that caused or support the node. |
| `assertion.subject_id/object_id` | Refer to entities in the same submitted document graph. |
| `assertion.text` | Complete natural-language proposition represented by the edge. |
| `assertion.scope` | Conditions, population, context or qualification that restrict the claim. |
| `assertion.evidence` | Source units supporting the full directed assertion. |
| `runtime` | End-to-end observed resources for the declared evaluation track. |

Do not synthesize missing evidence during export. An empty evidence list is valid input data and is
reported as missing coverage; a reference to a nonexistent unit is invalid.

## Method-specific details

Store method-specific metadata under an optional `metadata` object at the system, entity, assertion
or runtime level. The benchmark core ignores it for common metrics, but retaining prompt versions,
model IDs, chunking parameters and source hashes makes the run auditable.

## Versioning

Changing entity admission policy, relation projection, parsing, prompts, models, internal checking
or merge rules creates a new `system.version`. Re-exporting the same immutable run must produce the
same canonical submission hash.
