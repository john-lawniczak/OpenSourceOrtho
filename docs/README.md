# Documentation

This directory holds the project docs that should evolve with the product.

## Core Docs

- [SAFETY.md](SAFETY.md) - capability boundary and safety language
- [ARCHITECTURE.md](ARCHITECTURE.md) - plain-language system flow and technical layout
- [MOBILE.md](MOBILE.md) - mobile architecture, STL-only fallback, and browser handoff progress
- [cbct-evaluation.md](cbct-evaluation.md) - CBCT/DICOM safety-review tiers and roadmap
- [UI_DESIGN.md](UI_DESIGN.md) - visualization and interface accuracy contract
- [MAINTAINABILITY.md](MAINTAINABILITY.md) - composability, code hygiene, and file-size guardrails
- [OPEN_SOURCE_REFERENCES.md](OPEN_SOURCE_REFERENCES.md) - open-source dependencies and proprietary reference boundaries
- [LICENSE_AUDIT.md](LICENSE_AUDIT.md) - per-dependency license audit and compatibility
- [SOURCES_AND_RECOMMENDED_SOFTWARE.md](SOURCES_AND_RECOMMENDED_SOFTWARE.md) - source ledger for monitoring upstream references over time
- [OpenAI_Agents.md](OpenAI_Agents.md) - OpenAI agent/provider behavior guidance
- [AI_CHAT_MCP.md](AI_CHAT_MCP.md) - scoped AI chat and MCP connector data model
- [LLM_PROMPTS.md](LLM_PROMPTS.md) - safe optional LLM review prompt templates
- [GLOSSARY.md](GLOSSARY.md) - dental key terms and the FDI tooth-numbering diagram
- [DATA_CONTRIBUTION.md](DATA_CONTRIBUTION.md) - contributing scans and the privacy-safe specimen-id tracking

The user how-to lives at [../HOW_TO.md](../HOW_TO.md), the UI prototype lives at
[../ui/](../ui/README.md), synthetic example plans at [../examples/](../examples/README.md),
and contributor setup in [../CONTRIBUTING.md](../CONTRIBUTING.md).

## Maintenance Rule

When external sources change license terms, recommended usage, model availability, medical-device disclaimers, or project status, update the relevant docs in this directory and summarize the change in your pull request description.
