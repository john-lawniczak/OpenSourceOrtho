# Safety Boundary

OpenSource Ortho is a research and development toolkit for geometric planning workflows. It is not distributed as medical device software and is not intended to provide diagnosis, treatment approval, or autonomous clinical decision-making.

## Capability Boundary

OpenSource Ortho may describe:

- what data was provided
- what proposed movement values exist in a plan
- whether those values exceed user-configured caps
- whether stages are internally inconsistent
- what clinically relevant data is unavailable
- what questions a clinician may need to answer

OpenSource Ortho must not state or imply:

- a plan is safe, approved, cleared, clinically acceptable, or ready for treatment
- a patient is a good candidate for aligners
- roots, bone, periodontal structures, pathology, or airway status are acceptable when those data are unavailable
- a movement threshold is authoritative unless it is either user-configured or cited

## LLM Boundary

Model-generated findings are untrusted advisory text. They must pass the same linting path as deterministic findings before being displayed or exported.

Every model-sourced finding must:

- carry model provenance
- remain observational and conditional
- include data gaps when relevant
- avoid verdict language
- avoid invented thresholds

Warnings must include both a data gap and a clinician question.

## Regulatory Note

This document is not legal advice. Anyone using or modifying this project for clinical workflows is responsible for professional, legal, privacy, and regulatory obligations in their jurisdiction.

