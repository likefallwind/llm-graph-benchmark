# Evaluation protocol

## Claims this benchmark supports

The protocol is designed to support a bounded claim: one document-to-KG system produces a more
grounded, complete, identity-consistent and useful graph than named comparison systems under frozen
inputs and resources. It does not treat graph size or connectivity as quality by itself.

## Tracks

1. **Module-controlled track**: every system receives the same source units. Use this to compare
   extraction and graph construction without confounding document parsing or chunking.
2. **End-to-end track**: every system receives the same raw document and may parse or chunk it
   independently. Report parsing failures and resource use as part of the system result.

Results from the two tracks must not be mixed in one ranking.

## Evaluation directions

### Graph to source

Blindly sample submitted objects and judge narrow questions against cited source evidence:

- `entity_admission`: stable, referable, substantive, and grounded;
- `assertion_grounding`: full directed claim is supported;
- restrictive scope and polarity are preserved as part of assertion grounding.

This estimates precision-like quality. The production pipeline's internal checker remains part of
the evaluated system; it never substitutes for the common external judge.

### Source to graph

Fact probes are constructed independently from source units and checked against graph candidates
retrieved with one frozen retriever. This detects omissions shared by all compared systems and gives
a recall-like fact-recovery measure without requiring a complete gold graph.

Report retrieval failures separately when possible. A semantic retriever should be validated on a
small human-labelled slice before it is used for headline results.

## Human calibration

LLM judgments are not accepted as ground truth without calibration. Draw a stratified human sample
containing both random tasks and cross-judge disagreements. Report agreement, false acceptance,
false rejection, abstention and judge-family sensitivity. Human effort is used to validate the
evaluator, not to annotate an entire book graph.

## Fairness and reproducibility

- Freeze document hashes, source-unit boundaries, rubric, fact probes, task seed and sample sizes.
- Blind system identity in public tasks and randomize presentation order.
- Use the same external judge and retriever for every submission.
- Record extraction model, prompt/version fingerprint, elapsed time, tokens and cost.
- Never evaluate a live mutable graph database; export a completed immutable submission snapshot.
- Report bootstrap or Wilson confidence intervals and do not collapse dimensions into one total.

## Recommended paper table

| System | Entity admission | Assertion grounding | Fact recovery | Identity errors | Book QA | Cost |
|---|---:|---:|---:|---:|---:|---:|

Structure metrics, error slices, checker ablations and judge calibration belong in separate tables
or appendices so that high graph density cannot hide low semantic quality.
