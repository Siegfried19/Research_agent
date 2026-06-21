# Co-Scientist: A multi-agent AI partner to accelerate research

Every great scientific breakthrough begins with a single, transformative idea. The spark of discovery relies on a researcher's ability to connect disparate facts and formulate the right hypothesis to test. But in an era of information overload and increasingly complex challenges, the search for these needle-in-a-haystack ideas has become a significant bottleneck for progress.

We believe AI can help dramatically accelerate the pace of breakthroughs by serving as a dedicated partner in the generation and refinement of breakthrough scientific hypotheses.

Today, in *Nature* we published our latest Co-Scientist research, introducing a new multi-agent AI system built with Gemini that iteratively generates, debates, and evolves novel hypotheses for complex scientific problems.

We are making the Co-Scientist system available to individual researchers through Hypothesis Generation, a new experimental tool jointly developed across Google DeepMind, Google Research, Google Cloud and Google Labs. We'll begin rolling out in the coming weeks and researchers can register their interest at labs.google/science.

Since sharing our early research last year, we've been developing and testing Co-Scientist together with teams who are leveraging it to tackle challenging problems - from antimicrobial resistance and plant immunity to liver fibrosis. We're excited to share some of the ways it is already being applied across fundamental biology, the natural sciences, and engineering.

## How Co-Scientist works: A multi-agent system built with Gemini

Scientific discovery is rarely a straight line; it is a cycle of ideation and hypothesis generation, critique, and refinement. Scientists often reach their most profound insights only after wrestling with a complex problem for days, months, or even years. The core research question behind Co-Scientist was: *How can an AI system engage in this rigorous structured thinking for scientific discovery?*

The Co-Scientist AI system is made of a collaborative coalition of specialized agents based on the Gemini model, which we can group into three different phases:

**Generate ideas:**

* Generation agent - Proposes initial focus areas and novel hypotheses grounded in scientific literature and data.
* Proximity agent - Maps and clusters generated hypotheses to help ensure a diverse, comprehensive exploration of the research space.

**Debate ideas:**

* Reflection agent - Acts as a "virtual peer reviewer," critically evaluating hypotheses for correctness, quality, and novelty.
* Ranking agent - Orchestrates an "idea tournament", using pairwise comparisons and simulated scientific debates to prioritize the most promising paths and hypotheses.

**Evolve ideas:**

* Evolution agent - Continuously refines, combines, and builds upon the top-ranked hypotheses in the tournament to help iteratively improve their quality.
* Meta-review agent - Synthesizes insights from the debates and idea tournament to continuously optimize the system and generates the final research proposal for the scientist to review.

Orchestrating the agent coalition is a supervisor agent acting as an adaptive planner. Unlike AI models that think linearly, this freeform planner breaks down high-level research goals into executable steps, coordinating agents to run in parallel and explore multiple avenues simultaneously.

## Tournament of ideas: How our system verifies, refines, and ranks hypotheses

Co-Scientist can explore thousands of research directions. To help find the most impactful ones, we developed the 'tournament of ideas'. The approach draws from principles used in AlphaGo and AlphaStar - but instead of playing a game, our AI agents hold scientific debates to generate, refine and rank ideas.

To push the boundaries of novelty while ensuring the hypotheses are robust and testable, the majority of the system's computation is dedicated to *verifying* these hypotheses. By deeply cross-checking claims against scientific literature and data, the system ensures that claims remain grounded, factually accurate, and logically coherent. The system currently integrates web search and specialized databases like ChEMBL and UniProt to incorporate additional knowledge. It can also leverage advanced specialized models as tools like AlphaFold, which we are testing in select research collaborations.

This combination of these capabilities helps make Co-Scientist one of the first examples of a reliable multi-agent system for structured scientific thinking, enabling it to deliver tangible results in novel hypothesis generation for complex scientific problems.

## Validating Co-Scientist in the lab, starting with life sciences

Over the past year, we have collaborated with global experts to evaluate Co-Scientist on complex problems in the life sciences. We have also been previewing an enterprise-grade version with a number of organizations including Daiichi Sankyo, Bayer Crop Science, and the US National Laboratories as part of the Genesis Mission.

### Uncovering repurposed medicines to fight liver fibrosis

Co-Scientist helped accelerate Gary Peltz's search for liver fibrosis treatments. The multi-agent system highlighted overlooked drug-repurposing candidates, including one that successfully blocked 91% of a scarring-linked response in lab tests. The results, published in Advanced Science, point toward new gene-regulating approaches to treat chronic liver disease.

> "Co-Scientist feels like a collaborator that's read everything available about biomedical science, with reasoning to find missing connections."
>
> — Professor Gary Peltz, Stanford University School of Medicine

### Uniting biological toolkits for a new approach to ALS

Co-Scientist helped unite Ritu Raman and Ryan Flynn's labs around the degenerative disease, ALS. The system helped Ritu quickly digest complex literature, propose testable ideas, and spot where complementary expertise could strengthen the best leads, sparking collaboration with Ryan on potential RNA-based approaches to ALS.

> "Science is a team sport. Co-Scientist can't do science by itself, and I can't do it all by myself either."
>
> — Associate Professor Ritu Raman, MIT

### Fast-tracking genetic leads to reverse cellular aging

Biologists Omar Abudayyeh and Jonathan Gootenberg are using Co‑Scientist to speed up research on reversing cellular aging. The system synthesises decades of literature to propose novel genetic leads that in lab tests have been shown to rejuvenate cells. It also slashes the time needed to analyse huge screening datasets, from months to days.

> "Using Co-Scientist feels like having a team of 50 people at your disposal, doing work within a day."
>
> — Omar Abudayyeh, Principal Investigator, The Abudayyeh–Gootenberg Lab

### Accelerating discovery of liver disease mechanisms

For Filippo Menolascina, Co-Scientist helped turn biomedical literature overload into high-quality hypotheses for metabolic liver disease. The system highlighted promising disease mechanisms and drug combinations, and helped explain why an existing drug benefits only some patients – an idea later supported by Menolascina's lab tests.

> "Co‑Scientist feels like a jetpack for scientists, powering up our ability to identify promising mechanisms."
>
> — Filippo Menolascina, University of Edinburgh

### Finding the molecular switches behind new infectious diseases

Clare Bryant is using Co-Scientist to help identify the proteins that cause severe disease when pathogens like flu and COVID-19 leap from animals to humans. Iterating with the AI system, she rapidly narrowed the hunt to specific amino acids her lab will test — potentially cutting years of experimental work down to months.

> "Co-Scientist pulls together the entire published literature and online resources to help me ask better questions."
>
> — Clare Bryant, University of Cambridge

### Opening new paths in aging research

At Calico Life Sciences, Matt Onsum and Katherine Labbé are using Co-Scientist to tackle one of medicine's hardest problems: the biology of aging. The AI system has impressed Calico's experts with its scientific discernment, including by generating an exciting novel hypothesis about the integrated stress response that was later confirmed in the lab.

> "What I found both exciting and surprising about using Co-Scientist is how much it thinks like a scientist."
>
> — Dr Matt Onsum, Head of AI/ML, Calico Life Sciences

## Developing agentic tools with the scientific community

Co-Scientist was developed in collaboration with researchers from over 100 institutions to test its capabilities and ensure it is a high-quality, useful tool for the scientific community.

As part of our responsible AI approach, Co-Scientist underwent extensive internal and external safety evaluations. Given Co-Scientist's demonstrated proficiency in life and physical sciences, we also conducted independent evaluations for misuse in Chemical, Biological, Radiological and Nuclear (CBRN) domains. From these findings, we developed custom safety classifiers to flag unethical research goals and mitigate the surfacing of unsafe information.

We will continue to iterate and develop the tool alongside feedback and collaboration with the scientific community and are excited to be making Co-Scientist available to individual researchers through Gemini for Science. We also look forward to expanding access to more Google Cloud enterprise partners soon.

We have been deeply inspired by the scientists who have built up our understanding of the world today. And we hope that AI can help researchers to usher in and accelerate a new era of scientific progress.

**Note: Co-Scientist is intended to be a partner in research, not a replacement for scientific or clinical expertise, and users are responsible for any decisions they make using the outputs as they continue their scientific journey.**