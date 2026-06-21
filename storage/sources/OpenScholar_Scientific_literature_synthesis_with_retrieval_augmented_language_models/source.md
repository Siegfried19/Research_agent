# Scientific literature synthesis with retrieval-augmented language models

November 19, 2024

Akari Asai - Ai2

## Overview

Scientists face a significant challenge navigating the exponential growth of academic publications. The team at the University of Washington and Allen Institute for AI created an open retrieval-augmented system designed to help researchers find and synthesize relevant knowledge from scientific literature.

The system includes an 8-billion parameter language model that demonstrates superior performance compared to larger proprietary models. According to the research, "GPT-4o hallucinated more than 90% of the scientific papers that it cited," whereas their specialized model remains grounded in retrieved papers.

## System Architecture

The platform comprises four main components:

1. **Datastore**: Over 45 million papers from Semantic Scholar with approximately 250 million passage embeddings
2. **Specialized Retrievers and Rerankers**: Custom-trained tools to identify relevant passages
3. **Specialized 8B Language Model**: Fine-tuned version of Llama 3.1 for scientific synthesis
4. **Iterative Self-Feedback Generation**: Refinement mechanism that retrieves additional papers to improve quality

## ScholarQABench Evaluation

Researchers developed a new benchmark comprising seven datasets with open-ended scientific questions requiring multi-paper synthesis. The datasets span biomedical research, neuroscience, computer science, and multidisciplinary questions.

## Key Results

- OS-8B outperformed larger models including GPT-4o
- The system achieved dramatically improved citation accuracy (Citation F1 of 39.5 versus 0.1 for baseline GPT-4o)
- Expert evaluations showed system responses were preferred 70% of the time
- The 8B model operates at 100x lower cost than competing systems

## Limitations

The researchers acknowledge several constraints: potential citation of non-representative papers, occasional unsupported citations, possible parametric knowledge citations, and reliance on open-access papers only, which limits coverage in fields dominated by paywalled research.