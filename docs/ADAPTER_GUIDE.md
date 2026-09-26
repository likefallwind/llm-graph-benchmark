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
or runtime level. The current workflow recognizes native-field availability flags; other metadata
retains prompt versions, model IDs, chunking parameters and source hashes for auditing.

## Versioning

Changing entity admission policy, relation projection, parsing, prompts, models, internal checking
or merge rules creates a new `system.version`. Re-exporting the same immutable run must produce the
same canonical submission hash.


## Current workflow native-field availability

New evaluations use [the selected metrics workflow](WORKFLOW.md).
When an extractor has no native entity description, export an empty string in
entity.definition and set entity.metadata.definition_available to false.
The explicit absence marker permits an empty definition; it is excluded from
description judging and counted as missing field coverage. Existing placeholder
descriptions with the same marker are also excluded. Do not generate descriptions
to satisfy the adapter contract. Missing native types use an empty types array.

The current automated workflow requires text for every source unit. Supply a
transcription/OCR text before evaluating image-only or table-only units.
