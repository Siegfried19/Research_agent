# Introducing Ai2 Paper Finder

**March 26, 2025**

Today Ai2 released [Paper Finder](https://paperfinder.allen.ai/), an LLM-powered literature search system designed to mimic how human researchers actually search for academic papers.

## The Research Process Approach

Rather than requiring simplified keyword queries, Paper Finder accepts complex, natural language requests. For example, a researcher can enter: "papers that introduce a dataset of an unscripted dialogue between 2 speakers (written or transcription) in English where there is an annotation of some property (emotion, age, gender, etc.) of one of the speakers."

The system works by breaking down queries into components, searching iteratively, following citations, evaluating relevance, and running follow-up queries—mirroring "a multi-step process that involves learning and iterating as you go."

## How It Works

The system operates through several key stages:

**Query Analysis & Planning**: A query analyzer breaks down user requests into intents, metadata criteria, and semantic components. A query planner then routes to appropriate sub-flows.

**Multiple Search Strategies**: The system employs parallel approaches including semantic search across dense indices, keyword-based queries, and citation tracking (both forward and backward).

**Relevance Judgment**: An LLM evaluates candidate papers by decomposing semantic criteria into sub-criteria, "judging adherence to each separately before combining into a final score."

**Efficient Sampling**: The system uses batched multi-armed bandit algorithms to learn which search sources work best for different query types, reducing unnecessary LLM calls.

**Fast Mode**: A faster default mode returns results quickly, with an option to invoke exhaustive searching for comprehensive coverage.

## Performance

Testing on the LitSearch benchmark shows strong performance: "89% of queries found perfectly relevant papers (85% in fast mode), with 98% finding highly relevant results."

## Future Directions

The roadmap includes:
- Improved metadata handling (authors, years, venues)
- Better support for complex queries (numeric ranges, negation)
- Multi-turn interactions and query refinement
- More dynamic, LLM-controlled workflows
- Integration into a broader scientific research assistant

An open-source snapshot was released on GitHub, with plans to share additional components as they mature.