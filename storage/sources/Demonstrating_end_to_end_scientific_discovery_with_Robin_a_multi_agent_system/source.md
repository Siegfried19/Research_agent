# Demonstrating end-to-end scientific discovery with Robin: a multi-agent system

**AI Research**

Published May 19, 2026

By Sam Rodriques

Full Author List: Michaela Hinks, Ali Ghareeb, Benjamin Chang, Ludovico Mitchener

---

#### **Update May 19, 2026**

This work is now published in Nature. The paper highlights Robin's role as "the first multi-agent system for biological discovery to integrate hypothesis generation, experimental strategy, data analysis, and follow-up insight generation in one continuous workflow."

The research describes how Robin developed experimental strategies for therapeutic hypothesis generation, proposed follow-up experiments, and extracted actionable insights from data, including validation in primary human retinal pigment epithelium (RPE) stem cells.

Robin also proposed a novel mechanism: enhancing RPE phagocytosis by modulating circadian rhythm using KL001, an experimental drug "that has never before been used in humans or proposed for AMD."

#### **Original post from May 20, 2025**

FutureHouse announced the first discovery made by Robin, a multi-agent system for automating scientific research. Robin code is available at: https://github.com/Future-House/robin

The organization previously released specialized agents—Crow, Falcon, and Owl for literature analysis; Phoenix for chemical synthesis; and Finch for data analysis. Robin integrates these agents into a unified workflow that orchestrates the entire scientific process.

## How Robin Made Its First Discovery

Robin discovered ripasudil, a Rho-kinase (ROCK) inhibitor used for glaucoma, as a novel therapeutic candidate for dry age-related macular degeneration through an iterative cycle:

1. **Initial Hypothesis:** Robin conducted literature review and hypothesized that enhancing RPE phagocytosis could benefit dAMD treatment. Falcon evaluated candidate molecules; ten were tested. Finch analyzed results, identifying that Y-27632 augmented RPE phagocytosis.

2. **Mechanism Investigation:** Robin proposed RNA-sequencing experiments to understand Y-27632's effects. Finch identified that Y-27632 upregulated *ABCA1*, "a critical lipid efflux pump in RPE cells."

3. **Discovery of ripasudil:** Using initial drug candidate data, Robin proposed a second set of candidates, identifying ripasudil as "a new top hit: ripasudil, a drug already used in the eye."

All hypotheses, experiment choices, data analyses, and manuscript figures were generated autonomously by Robin.

## A New Paradigm for Scientific Research

The entire process—from conceptualizing Robin to paper submission—was completed in approximately 2.5 months. Robin represents "a powerful new paradigm for AI-driven scientific discovery." The agents are general-purpose and applicable across diverse fields including materials science and climate technology. The code is open-sourced to "inspire others to build their own systems for automated discovery."