# Introducing Ai2 ScholarQA

January 21, 2025

Ai2

[Code](https://github.com/allenai/ai2-scholarqa-lib/) | [Try it in Asta](https://scholarqa.allen.ai/)

## Overview

Literature review consumes substantial research time. While AI tools can answer questions about individual papers, researchers frequently need to synthesize insights across multiple documents. Ai2 ScholarQA addresses this need—it handles "scientific questions that require multiple documents to answer." The platform includes table comparisons, expandable subsections, and citations with paper excerpts for verification.

The system uses a retrieval-augmented generation approach with Claude Sonnet 3.5, operating on a corpus of open-access papers.

**March 5th Update:**
- Expanded corpus to 8M+ full-text papers and 108M+ abstracts
- Added Google login functionality to save query history
- Updated backbone model to Claude Sonnet 3.7
- Released open-source code on GitHub

## Corpus and Search Index

The retrieval system uses a Vespa cluster containing approximately 8 million academic papers spanning computer science, medicine, environmental science, and biology. Weekly updates draw from the Open S2ORC dataset, focusing on open-access materials.

The search combines "BM25 and dense embeddings to score snippets" from full-text papers. ScholarQA proves most useful for researchers in fields well-represented on arXiv. Academic users with eligible email addresses can request Semantic Scholar API keys for full-text search access.

## Section Planning and Generation

The answer generation follows a three-step LLM-driven process:

1. **Quote Extraction:** Top passages are filtered to identify the most relevant quotes, reducing context overload.

2. **Answer Outline and Clustering:** Quotes generate section headers with assigned quotes. Sections format as either paragraphs (conveying nuanced relations) or bulleted lists (enumerating related papers, models, datasets).

3. **Report Generation:** Sections generate sequentially with prior context, including TLDR summaries and attribution.

## Paper Comparison Table Generation

For related papers, the system generates literature review tables. The process involves two steps:

**Schema Generation:** Using paper titles, abstracts, user queries, and generated sections, the system creates column headers with definitions.

**Value Generation:** For each cell, the system generates display values and supporting paper snippets, mapping them back to original sentences.

The team created ArXiVDigestable, a gold table dataset, to benchmark this task.

## Learnings and Next Steps

The evidence-first pipeline prioritizes writing answers around evidence rather than finding evidence for pre-written answers. This approach presents tradeoffs—coherence sometimes suffers when integrating evidence, and response times exceed typical models.

The team plans to open-source core functionality and explore enhanced personalization for scientific research support.

*Ai2 ScholarQA is a collaborative project with University of Washington and KAIST students.*