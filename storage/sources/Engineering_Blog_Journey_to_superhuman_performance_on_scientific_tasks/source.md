# Engineering Blog: Journey to superhuman performance on scientific tasks

**Published:** September 19, 2024  
**By:** Andrew White and Sam Rodriques  
**Full Author List:** Michael Skarlinski, Sam Cox, James Braza, Andrew White, Sam Rodriques

---

## Overview

FutureHouse has developed PaperQA2, a retrieval-augmented generation (RAG) system designed to achieve superhuman performance on scientific tasks. Rather than optimizing for cost or speed, the team focused exclusively on accuracy, resulting in a fundamentally different architecture from commercial RAG systems.

## Key Design Principles

**Important for RAG accuracy:**
- Agentic approach enabling iterative query refinement
- LLM re-ranking and contextual summarization (RCS) trading computation for precision
- Document citation traversal expanding retrieval beyond keyword matching

**Unimportant for RAG accuracy:**
- Embedding model selection (when using RCS)
- Hybrid keyword-embedding combinations
- Chunk size variations

The system was evaluated using LitQA2, a benchmark comprising 200 expert-crafted multiple-choice questions requiring comprehension of scientific paper content.

---

## Agentic Advantage: PaperQA2

Traditional RAG systems follow a linear retrieval-then-generation pipeline. PaperQA2 breaks components into modular tools, allowing an agent to dynamically decide which tools to apply and in what sequence.

The system employs four configurable tools, including a novel citation traversal component. Results show agent-driven orchestration substantially outperforms fixed tool ordering:

- Accuracy improved from baseline approaches
- Answer recall increased significantly
- Average 4+ tool calls per question indicates non-deterministic decision-making
- Citation traversal used in approximately 46% of queries
- Self-correction capability evidenced by averaging 1.26 searches per question

Query expansion exemplifies this advantage. For a complex question about protein structure, the agent initially searched "mSandy2 chromophore p-hydroxybenzylidene Leucine 63 rotamer" (yielding minimal results), then broadened to "mSandy2 chromophore structure and rotamers" (doubling relevant evidence).

---

## LLM Re-ranking and Contextual Summarization (RCS)

The "Gather Evidence" phase operates in two stages:

1. **Embedding ranking:** Initial similarity-based ranking of document chunks
2. **RCS phase:** LLM re-evaluates and summarizes top-k chunks with relevance scoring (1-10 scale)

### Benefits:
- Token efficiency: 5.6x average compression of summarized chunks
- Error correction: LLM can override embedding ranking shortcomings
- Reasoning opportunity: Complex queries decomposed into single-chunk evaluations

### Performance Trade-offs:

RCS effectiveness depends on model capability. Simpler models (GPT-3.5-Turbo) performed worse than skipping RCS entirely, while sophisticated models showed consistent improvement. Performance saturated at top-k depths of 20-30 for source-specific QA.

### Ranking Depth Analysis:

Investigating optimal parameters revealed:
- **Chunk size:** 7-11k characters optimal; beyond 20-depth cutoff, size differences negligible
- **Embedding models:** text-embedding-3-large performed best, but convergence occurred at depth 20
- **Hybrid embeddings:** Combining dense embeddings with keyword vectors showed marginal improvement
- **Parsing approach:** PyMuPDF vs. Grobid differences minimal at deep ranking cutoffs

The RCS step dramatically improved key passage ranking, saturating around depth 5 after initial re-ranking.

---

## Citation Traversal: Improving Recall

Analysis revealed strong correlation between source paper retrieval and answer accuracy. The citation traversal tool leverages scientific literature's citation network, traversing one degree in both directions (backward references and forward citations).

### Algorithm:
1. Start from papers with high RCS scores (≥8/10)
2. Retrieve citations via Semantic Scholar and Crossref APIs
3. De-duplicate using case-folded titles and DOIs
4. Filter by overlap threshold (default: citations appearing in ≥1/3 of source papers)

### Impact:
- Accuracy improved compared to baseline
- Precision unaffected
- Substantially increased relevant paper discovery, especially early in retrieval pipeline
- Effective hierarchical indexing beyond keyword search

---

## Parsing: Structure and Metadata

Initial gene article evaluations identified recurring failures: gene name conflation between summarization and answer generation (6/40 samples) and parsing errors with tables/reference sections.

### Solutions Implemented:

**Enhanced metadata:** JSON key-value pairs in structured summaries preserved context through downstream tools, enabling the model to maintain accurate entity references.

**Structured parsing:** Integration of Grobid (deep-learning PDF parser) provided:
- Separate section-based chunks (abstract, methods, results, etc.)
- XML-formatted tables with unambiguous cell boundaries
- Citation attribution per sentence

### Token Efficiency:
- Grobid "section" chunking: 44% fewer characters than PyMuPDF
- Trade-off: added metadata inflates character count ~52%
- No LitQA2 accuracy difference observed between parsers

### Results:
External evaluation of regenerated gene articles showed dramatic improvement: gene name conflation reduced from 6/40 (15%) to 2/171 (1.2%, p < 0.001). No instances of table parsing or reference section mishandling caused hallucinations in final evaluation set.

---

## Conclusions

PaperQA2 achieves superhuman performance through deliberate design choices prioritizing accuracy:

- **Agentic workflows** enable adaptive query strategies and self-correction
- **RCS optimization** couples compute with accuracy gains, providing resilience to model choices
- **Citation traversal** enhances recall through structured literature navigation
- **Structured parsing** improves token efficiency without sacrificing accuracy

These architectural decisions increase computational cost and latency but yield substantially higher accuracy for scientific tasks including question-answering, review article generation, and contradiction detection.