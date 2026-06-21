# GraphRAG: New tool for complex data discovery now on GitHub

Published July 2, 2024

By Darren Edge, Senior Director; Ha Trinh, Senior Data Scientist; Steven Truitt, Principal Program Manager; Jonathan Larson, Partner Data Architect

## Overview

Microsoft Research has released GraphRAG, a graph-based retrieval-augmented generation tool now available on GitHub. The system enables question-answering capabilities over private or previously unseen datasets with "more structured information retrieval and comprehensive response generation than naive RAG approaches."

## How GraphRAG Works

The tool leverages large language models to automatically extract knowledge graphs from unstructured text documents. A distinctive feature involves detecting communities within the graph hierarchy—"partitioning the graph at multiple levels from high-level themes to low-level topics." Each community receives an LLM-generated summary describing entities and their relationships.

## Advantages for Global Questions

GraphRAG excels at answering global questions addressing entire datasets, where traditional vector-search RAG approaches struggle. For instance, questions like "What are the main themes in the dataset?" require considering all input texts, not just top-k similar chunks. The system uses a map-reduce approach: grouping community reports, mapping questions across groups, then reducing answers into comprehensive final responses.

## Evaluation Results

Testing against naive RAG and hierarchical summarization showed GraphRAG outperformed on three metrics: comprehensiveness, diversity, and empowerment. Results indicated "~70–80% win rate" for comprehensiveness and diversity across community hierarchy levels, while using significantly fewer tokens than alternative approaches.

## Future Development

Researchers are exploring methods to reduce upfront indexing costs while maintaining quality. Ongoing work includes automatically tuning LLM extraction prompts to problem domains and investigating NLP-based approaches for approximating knowledge graphs.