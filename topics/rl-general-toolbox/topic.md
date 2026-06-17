# 主题：RL 通用工具箱与诊断箱：reward设计、训练trick、算法谱系与安全增强

> **研究思路**：训练强化学习策略（目前主要用 SAC 和 PPO）时经常遇到训不出来的瓶颈，怀疑是 reward 设计或算法超参的问题。需要一批实战导向的论文来构建'RL 训练工具箱'：(1) reward 设计与 shaping 的原则、常见坑（reward hacking/specification gaming）；(2) 训练稳定性 trick、实现细节与超参敏感性的 empirical study；(3) 稀疏奖励下的探索、课程学习；(4) SAC/PPO 之外更丰富的算法（off-policy 改进、模型基方法、约束优化等）及横向比较；(5) control barrier function 等安全增强方法与 RL 的结合（非常重要）；(6) 具体任务（人形/全身控制/数字人/locomotion）上的 reward 工程实例。偏好可操作、有实验对比、给出 do/don't 的论文，而非纯理论。

- 命中论文：100　已总结：39　最近更新：2026-06-10
- 检索词：`reward shaping deep reinforcement learning continuous control`、`reward design reinforcement learning robotics locomotion`、`deep reinforcement learning training stability tricks implementation details`、`PPO implementation details hyperparameters empirical study`、`on-policy reinforcement learning what matters empirical study`、`sparse reward exploration intrinsic motivation reinforcement learning`、`reward hacking specification gaming reinforcement learning`、`curriculum learning reinforcement learning robot control`、`control barrier function reinforcement learning safe control`、`safe reinforcement learning constrained policy optimization`、`off-policy actor critic continuous control TD3 SAC improvements`、`model-based reinforcement learning continuous control sample efficiency`、`reinforcement learning humanoid whole-body control reward design`、`deep reinforcement learning continuous control benchmark algorithms comparison`

## 命中清单（按相关性排序）

| # | 相关性 | 论文 | 年份 | 引用 | 状态 | 总结 |
|--:|--:|---|--:|--:|---|---|
| 1 | 95.0 | Soft Actor-Critic: Off-Policy Maximum Entropy Deep Reinforcement Learning with a Stochastic Actor | 2018 | 11346 | ✅ 已总结 | [v1](../../store/summaries/Soft_Actor_Critic_Off_Policy_Maximum_Entropy_Deep_Reinforcement_Learning_with_a/v1.md) |
| 2 | 94.0 | End-to-End Safe Reinforcement Learning through Barrier Functions for Safety-Critical Continuous Control Tasks | 2019 | 528 | ✅ 已总结 | [v1](../../store/summaries/End_to_End_Safe_Reinforcement_Learning_through_Barrier_Functions_for_Safety_Critical/v1.md) |
| 3 | 94.0 | Safe Reinforcement Learning Using Robust Control Barrier Functions | 2022 | 52 | ✅ 已总结 | [v1](../../store/summaries/Safe_Reinforcement_Learning_Using_Robust_Control_Barrier_Functions/v1.md) |
| 4 | 93.0 | Deep Reinforcement Learning That Matters | 2018 | 1499 | ✅ 已总结 | [v1](../../store/summaries/Deep_Reinforcement_Learning_That_Matters/v1.md) |
| 5 | 93.0 | What Matters In On-Policy Reinforcement Learning? A Large-Scale Empirical Study | 2020 | 278 | ✅ 已总结 | [v1](../../store/summaries/What_Matters_In_On_Policy_Reinforcement_Learning_A_Large_Scale_Empirical_Study/v1.md) |
| 6 | 93.0 | What Matters for On-Policy Deep Actor-Critic Methods? A Large-Scale Study | 2021 | 242 | ✅ 已总结 | [v1](../../store/summaries/What_Matters_for_On_Policy_Deep_Actor_Critic_Methods_A_Large_Scale_Study/v1.md) |
| 7 | 92.0 | Temporal Logic Guided Safe Reinforcement Learning Using Control Barrier Functions | 2019 | 31 | ✅ 已总结 | [v1](../../store/summaries/Temporal_Logic_Guided_Safe_Reinforcement_Learning_Using_Control_Barrier_Functions/v1.md) |
| 8 | 91.0 | Reproducibility of Benchmarked Deep Reinforcement Learning Tasks for Continuous Control | 2017 | 187 | ✅ 已总结 | [v1](../../store/summaries/Reproducibility_of_Benchmarked_Deep_Reinforcement_Learning_Tasks_for_Continuous_Control/v1.md) |
| 9 | 90.0 | Reward-Adaptive Reinforcement Learning: Dynamic Policy Gradient Optimization for Bipedal Locomotion | 2022 | 38 | ✅ 已总结 | [v1](../../store/summaries/Reward_Adaptive_Reinforcement_Learning_Dynamic_Policy_Gradient_Optimization_for_Bipedal/v1.md) |
| 10 | 90.0 | STRIDE: Automating Reward Design, Deep Reinforcement Learning Training and Feedback Optimization in Humanoid Robotics Locomotion 🪨 | 2025 | 0 | ✅ 已总结 | [v1](../../store/summaries/STRIDE_Automating_Reward_Design_Deep_Reinforcement_Learning_Training_and_Feedback/v1.md) |
| 11 | 88.0 | Safe Learning in Robotics: From Learning-Based Control to Safe Reinforcement Learning | 2022 | 654 | ✅ 已总结 | [v1](../../store/summaries/Safe_Learning_in_Robotics_From_Learning_Based_Control_to_Safe_Reinforcement_Learning/v1.md) |
| 12 | 88.0 | Learning to Walk Via Deep Reinforcement Learning | 2019 | 434 | ✅ 已总结 | [v1](../../store/summaries/Learning_to_Walk_Via_Deep_Reinforcement_Learning/v1.md) |
| 13 | 88.0 | Addressing Function Approximation Error in Actor-Critic Methods | 2018 | 414 | ✅ 已总结 | [v1](../../store/summaries/Addressing_Function_Approximation_Error_in_Actor_Critic_Methods/v1.md) |
| 14 | 86.0 | High-Dimensional Continuous Control Using Generalized Advantage Estimation | 2015 | 1750 | ✅ 已总结 | [v1](../../store/summaries/High_Dimensional_Continuous_Control_Using_Generalized_Advantage_Estimation/v1.md) |
| 15 | 86.0 | Safe reinforcement learning: A control barrier function optimization approach | 2020 | 229 | ✅ 已总结 | [v1](../../store/summaries/Safe_reinforcement_learning_A_control_barrier_function_optimization_approach/v1.md) |
| 16 | 86.0 | Penalized Proximal Policy Optimization for Safe Reinforcement Learning | 2022 | 122 | ✅ 已总结 | [v1](../../store/summaries/Penalized_Proximal_Policy_Optimization_for_Safe_Reinforcement_Learning/v1.md) |
| 17 | 86.0 | Automatic Intrinsic Reward Shaping for Exploration in Deep Reinforcement Learning | 2023 | 18 | ✅ 已总结 | [v1](../../store/summaries/Automatic_Intrinsic_Reward_Shaping_for_Exploration_in_Deep_Reinforcement_Learning/v1.md) |
| 18 | 85.0 | Safe Reinforcement Learning via Shielding | 2018 | 617 | ✅ 已总结 | [v1](../../store/summaries/Safe_Reinforcement_Learning_via_Shielding/v1.md) |
| 19 | 85.0 | Challenges of real-world reinforcement learning: definitions, benchmarks and analysis | 2021 | 563 | ✅ 已总结 | [v1](../../store/summaries/Challenges_of_real_world_reinforcement_learning_definitions_benchmarks_and_analysis/v1.md) |
| 20 | 85.0 | End-To-End Robotic Reinforcement Learning without Reward Engineering | 2019 | 208 | ✅ 已总结 | [v1](../../store/summaries/End_To_End_Robotic_Reinforcement_Learning_without_Reward_Engineering/v1.md) |
| 21 | 85.0 | Safe exploration in model-based reinforcement learning using control barrier functions | 2022 | 83 | ✅ 已总结 | [v1](../../store/summaries/Safe_exploration_in_model_based_reinforcement_learning_using_control_barrier_functions/v1.md) |
| 22 | 85.0 | Regularization Matters in Policy Optimization - An Empirical Study on Continuous Control | 2020 | 59 | ✅ 已总结 | [v1](../../store/summaries/Regularization_Matters_in_Policy_Optimization_An_Empirical_Study_on_Continuous_Control/v1.md) |
| 23 | 85.0 | PPG Reloaded: An Empirical Study on What Matters in Phasic Policy Gradient 🪨 | 2023 | 1 | ✅ 已总结 | [v1](../../store/summaries/PPG_Reloaded_An_Empirical_Study_on_What_Matters_in_Phasic_Policy_Gradient/v1.md) |
| 24 | 85.0 | Tiered Reward: Designing Rewards for Specification and Fast Learning of Desired Behavior 🪨 | 2022 | 0 | ✅ 已总结 | [v1](../../store/summaries/Tiered_Reward_Designing_Rewards_for_Specification_and_Fast_Learning_of_Desired_Behavior/v1.md) |
| 25 | 85.0 | SafeAdapt: Provably Safe Policy Updates in Deep Reinforcement Learning 🪨 | 2026 | 0 | ✅ 已总结 | [v1](../../store/summaries/SafeAdapt_Provably_Safe_Policy_Updates_in_Deep_Reinforcement_Learning/v1.md) |
| 26 | 84.0 | Augmented Proximal Policy Optimization for Safe Reinforcement Learning | 2023 | 32 | 📄 有全文 | — |
| 27 | 84.0 | Constraint-Conditioned Policy Optimization for Versatile Safe Reinforcement Learning | 2023 | 22 | ✅ 已总结 | [v1](../../store/summaries/Constraint_Conditioned_Policy_Optimization_for_Versatile_Safe_Reinforcement_Learning/v1.md) |
| 28 | 83.0 | Value Improved Actor Critic Algorithms 🪨 | 2024 | 3 | ✅ 已总结 | [v1](../../store/summaries/Value_Improved_Actor_Critic_Algorithms/v1.md) |
| 29 | 82.0 | From Sparse to Dense: Toddler-inspired Reward Transition in Goal-Oriented Reinforcement Learning 🪨 | 2025 | 0 | ✅ 已总结 | [v1](../../store/summaries/From_Sparse_to_Dense_Toddler_inspired_Reward_Transition_in_Goal_Oriented_Reinforcement/v1.md) |
| 30 | 80.0 | #Exploration: A Study of Count-Based Exploration for Deep Reinforcement Learning | 2016 | 344 | ✅ 已总结 | [v1](../../store/summaries/Exploration_A_Study_of_Count_Based_Exploration_for_Deep_Reinforcement_Learning/v1.md) |
| 31 | 80.0 | Distributional Soft Actor-Critic with Three Refinements | 2023 | 55 | ✅ 已总结 | [v1](../../store/summaries/Distributional_Soft_Actor_Critic_with_Three_Refinements/v1.md) |
| 32 | 80.0 | On the Emergence of Whole-Body Strategies From Humanoid Robot Push-Recovery Learning | 2021 | 22 | ✅ 已总结 | [v1](../../store/summaries/On_the_Emergence_of_Whole_Body_Strategies_From_Humanoid_Robot_Push_Recovery_Learning/v1.md) |
| 33 | 80.0 | Secrets of RLHF in Large Language Models Part I: PPO | 2023 | 19 | ✅ 已总结 | [v1](../../store/summaries/Secrets_of_RLHF_in_Large_Language_Models_Part_I_PPO/v1.md) |
| 34 | 80.0 | What Matters for Batch Online Reinforcement Learning in Robotics? | 2025 | 11 | ✅ 已总结 | [v1](../../store/summaries/What_Matters_for_Batch_Online_Reinforcement_Learning_in_Robotics/v1.md) |
| 35 | 80.0 | Multimodal bipedal locomotion generation with passive dynamics via deep reinforcement learning | 2023 | 11 | ✅ 已总结 | [v1](../../store/summaries/Multimodal_bipedal_locomotion_generation_with_passive_dynamics_via_deep_reinforcement/v1.md) |
| 36 | 80.0 | No More Hand-Tuning Rewards: Masked Constrained Policy Optimization for Safe Reinforcement Learning 🪨 | 2021 | 4 | ✅ 已总结 | [v1](../../store/summaries/No_More_Hand_Tuning_Rewards_Masked_Constrained_Policy_Optimization_for_Safe_Reinforcement/v1.md) |
| 37 | 80.0 | Extreme Value Policy Optimization for Safe Reinforcement Learning 🪨 | 2026 | 1 | ✅ 已总结 | [v1](../../store/summaries/Extreme_Value_Policy_Optimization_for_Safe_Reinforcement_Learning/v1.md) |
| 38 | 80.0 | From Reward Shaping to Q-Shaping: Achieving Unbiased Learning with LLM-Guided Knowledge 🪨 | 2024 | 0 | ✅ 已总结 | [v1](../../store/summaries/From_Reward_Shaping_to_Q_Shaping_Achieving_Unbiased_Learning_with_LLM_Guided_Knowledge/v1.md) |
| 39 | 80.0 | Predictive Control Barrier Functions for Online Safety Critical Control 🪨 | 2022 | 0 | ✅ 已总结 | [v1](../../store/summaries/Predictive_Control_Barrier_Functions_for_Online_Safety_Critical_Control/v1.md) |
| 40 | 80.0 | Leveraging exploration in off-policy algorithms via normalizing flows 🪨 | 2019 | 0 | ✅ 已总结 | [v1](../../store/summaries/Leveraging_exploration_in_off_policy_algorithms_via_normalizing_flows/v1.md) |
| 41 | 80.0 | Safe Reinforcement Learning with Probabilistic Control Barrier Functions for Ramp Merging 🪨 | 2022 | 0 | 📄 有全文 | — |
| 42 | 78.0 | Reinforcement Learning for Robust Parameterized Locomotion Control of Bipedal Robots | 2021 | 12 | 📄 有全文 | — |
| 43 | 78.0 | Humanoid Whole-Body Badminton via Multi-Stage Reinforcement Learning 🪨 | 2025 | 0 | 📄 有全文 | — |
| 44 | 78.0 | Recursively Feasible Probabilistic Safe Online Learning with Control Barrier Functions 🪨 | 2022 | 0 | 📄 有全文 | — |
| 45 | 76.0 | Sim-to-Real: Learning Agile Locomotion For Quadruped Robots | 2018 | 673 | 📄 有全文 | — |
| 46 | 76.0 | A survey of preference-based reinforcement learning methods | 2017 | 115 | 📄 有全文 | — |
| 47 | 76.0 | Model-based Safe Deep Reinforcement Learning via a Constrained Proximal Policy Optimization Algorithm | 2022 | 72 | 📄 有全文 | — |
| 48 | 76.0 | Input-to-State Safety for Reinforcement Learning. 🪨 | 2026 | 0 | 📄 有全文 | — |
| 49 | 76.0 | Humanoid Manipulation Interface: Humanoid Whole-Body Manipulation from Robot-Free Demonstrations 🪨 | 2026 | 0 | 📄 有全文 | — |
| 50 | 75.0 | Learning Complex Dexterous Manipulation with Deep Reinforcement Learning and Demonstrations | 2018 | 124 | 📄 有全文 | — |
| 51 | 75.0 | Constrained Variational Policy Optimization for Safe Reinforcement Learning | 2022 | 118 | 📄 有全文 | — |
| 52 | 75.0 | Curiosity Driven Reinforcement Learning for Motion Planning on Humanoids | 2014 | 75 | 📄 有全文 | — |
| 53 | 75.0 | Soft Actor-Critic Algorithm in High-Dimensional Continuous Control Tasks 🪨 | 2024 | 1 | 📄 有全文 | — |
| 54 | 75.0 | Causal-Paced Deep Reinforcement Learning 🪨 | 2025 | 0 | 📄 有全文 | — |
| 55 | 74.0 | Safe Reinforcement Learning With Stability Guarantee for Motion Planning of Autonomous Vehicles | 2021 | 150 | 📄 有全文 | — |
| 56 | 74.0 | Efficient Continuous Control with Double Actors and Regularized Critics | 2022 | 55 | 📄 有全文 | — |
| 57 | 74.0 | Decoupled Policy Actor-Critic: Bridging Pessimism and Risk Awareness in Reinforcement Learning | 2025 | 5 | 📄 有全文 | — |
| 58 | 74.0 | AFU: Actor-Free critic Updates in off-policy RL for continuous control 🪨 | 2024 | 0 | 📄 有全文 | — |
| 59 | 74.0 | The Role of Domain Randomization in Training Diffusion Policies for Whole-Body Humanoid Control 🪨 | 2024 | 0 | 📄 有全文 | — |
| 60 | 74.0 | Learning robotic manipulation skills with multiple semantic goals by conservative curiosity-motivated exploration 🪨 | 2023 | 0 | 📄 有全文 | — |
| 61 | 74.0 | Improved Soft Actor-Critic: Mixing Prioritized Off-Policy Samples with On-Policy Experience 🪨 | 2021 | 0 | 📄 有全文 | — |
| 62 | 72.0 | Deep Reinforcement Learning-Based End-to-End Navigation of Mobile Robots with Reward Shaping 🪨 | 2024 | 1 | 📄 有全文 | — |
| 63 | 72.0 | Transformer-based human-motion forecasting coupled with safe reinforcement learning for telepresence robot co-navigation. 🪨 | 2025 | 0 | 📄 有全文 | — |
| 64 | 72.0 | Reinforcement Learning with Stochastic Reward Machines 🪨 | 2025 | 0 | 📄 有全文 | — |
| 65 | 71.0 | CVaR-Constrained Policy Optimization for Safe Reinforcement Learning | 2024 | 50 | 📄 有全文 | — |
| 66 | 71.0 | JuggleRL: Mastering Ball Juggling with a Quadrotor via Deep Reinforcement Learning 🪨 | 2025 | 0 | 📄 有全文 | — |
| 67 | 70.0 | Hierarchical deep reinforcement learning: integrating temporal abstraction and intrinsic motivation | 2016 | 541 | 📄 有全文 | — |
| 68 | 70.0 | Stochastic Neural Networks for Hierarchical Reinforcement Learning | 2017 | 378 | 📄 有全文 | — |
| 69 | 70.0 | Safe Off-Policy Deep Reinforcement Learning Algorithm for Volt-VAR Control in Power Distribution Systems | 2019 | 307 | 📄 有全文 | — |
| 70 | 70.0 | A Survey on Offline Reinforcement Learning: Taxonomy, Review, and Open Problems | 2023 | 286 | 📄 有全文 | — |
| 71 | 70.0 | Safe Reinforcement Learning for Autonomous Vehicles through Parallel Constrained Policy Optimization | 2020 | 87 | 📄 有全文 | — |
| 72 | 70.0 | VCSAP: Online reinforcement learning exploration method based on visitation count of state-action pairs | 2025 | 8 | 📄 有全文 | — |
| 73 | 70.0 | Combining Soft-Actor Critic with Cross-Entropy Method for Policy Search in Continuous Control | 2022 | 8 | 📄 有全文 | — |
| 74 | 70.0 | Doubly Robust Off-Policy Actor-Critic Algorithms for Reinforcement Learning 🪨 | 2019 | 3 | 📄 有全文 | — |
| 75 | 70.0 | Soft Actor-Critic with Beta Policy via Implicit Reparameterization Gradients 🪨 | 2024 | 1 | 📄 有全文 | — |
| 76 | 70.0 | Mixture of Autoencoder Experts Guidance using Unlabeled and Incomplete Data for Exploration in Reinforcement Learning 🪨 | 2025 | 1 | 📄 有全文 | — |
| 77 | 70.0 | Value Bonuses using Ensemble Errors for Exploration in Reinforcement Learning 🪨 | 2026 | 0 | 📄 有全文 | — |
| 78 | 70.0 | Mirror Descent Safe Policy Optimization for Reinforcement Learning Agents. 🪨 | 2026 | 0 | 📄 有全文 | — |
| 79 | 70.0 | A graph-based safe reinforcement learning method for multi-agent cooperation 🪨 | 2026 | 0 | 📄 有全文 | — |
| 80 | 70.0 | Deep dive into model-free reinforcement learning for underwater locomotion: theory and practice. 🪨 | 2026 | 0 | 📄 有全文 | — |
| 81 | 68.0 | Constrained Policy Optimization with Explicit Behavior Density For Offline Reinforcement Learning | 2023 | 16 | 📄 有全文 | — |
| 82 | 68.0 | ReLU to the Rescue: Improve Your On-Policy Actor-Critic with Positive Advantages | 2023 | 11 | 📄 有全文 | — |
| 83 | 68.0 | Self-supervised network distillation: An effective approach to exploration in sparse reward environments | 2024 | 10 | 📄 有全文 | — |
| 84 | 68.0 | Broad Critic Deep Actor Reinforcement Learning for Continuous Control 🪨 | 2024 | 3 | 📄 有全文 | — |
| 85 | 68.0 | Game-Theoretic Constrained Policy Optimization for Safe Reinforcement Learning 🪨 | 2025 | 3 | 📄 有全文 | — |
| 86 | 68.0 | CIM: Constrained Intrinsic Motivation for Sparse-Reward Continuous Control 🪨 | 2022 | 2 | 📄 有全文 | — |
| 87 | 68.0 | What Matters in RL-Based Methods for Object-Goal Navigation? An Empirical Study and A Unified Framework 🪨 | 2025 | 2 | 📄 有全文 | — |
| 88 | 68.0 | Offline constrained policy optimization with safe anchoring. 🪨 | 2026 | 0 | 📄 有全文 | — |
| 89 | 68.0 | Scaling data-driven robotics with reward sketching and batch reinforcement learning 🪨 | 2019 | 0 | 📄 有全文 | — |
| 90 | 67.0 | Experimental evaluation of model-free reinforcement learning algorithms for continuous HVAC control | 2021 | 169 | 📄 有全文 | — |
| 91 | 66.0 | Model-based Reinforcement Learning: A Survey | 2023 | 481 | 📄 有全文 | — |
| 92 | 66.0 | Online Meta-Critic Learning for Off-Policy Actor-Critic Methods | 2020 | 54 | 📄 有全文 | — |
| 93 | 66.0 | Lazy Agents: A New Perspective on Solving Sparse Reward Problem in Multi-agent Reinforcement Learning | 2023 | 36 | 📄 有全文 | — |
| 94 | 66.0 | Improved Learning of Robot Manipulation Tasks Via Tactile Intrinsic Motivation | 2021 | 32 | 📄 有全文 | — |
| 95 | 66.0 | Comparing Deep Reinforcement Learning and Evolutionary Methods in Continuous Control 🪨 | 2017 | 0 | 📄 有全文 | — |
| 96 | 66.0 | Safe Control Synthesis via Input Constrained Control Barrier Functions 🪨 | 2021 | 0 | 📄 有全文 | — |
| 97 | 66.0 | Self-Organizing Dual-Buffer Adaptive Clustering Experience Replay (SODACER) for safe reinforcement learning in optimal control. 🪨 | 2026 | 0 | 📄 有全文 | — |
| 98 | 65.0 | Variational Dynamic for Self-Supervised Exploration in Deep Reinforcement Learning | 2021 | 24 | 📄 有全文 | — |
| 99 | 64.0 | An Algorithmic Perspective on Imitation Learning | 2018 | 370 | 📄 有全文 | — |
| 100 | 64.0 | Mastering Complex Control in MOBA Games with Deep Reinforcement Learning | 2020 | 271 | 📄 有全文 | — |

_🪨 = 边角文章（低引用，保留以备不同视角）_

## 相关性理由

- **[1] Soft Actor-Critic: Off-Policy Maximum Entropy Deep Reinforcement Learn** （95.0）：SAC 原始论文，直击用户主力算法，专讲样本复杂度、脆弱收敛与超参敏感性，实战工具箱核心
- **[2] End-to-End Safe Reinforcement Learning through Barrier Functions for S** （94.0）：control barrier function直接与RL结合保证学习期安全,正中用户'非常重要'的CBF安全增强诉求
- **[3] Safe Reinforcement Learning Using Robust Control Barrier Functions** （94.0）：直接命中需求(5):把鲁棒CBF做成可微安全层嵌入model-based RL,既保证安全又引导探索,RAL高质量来源。
- **[4] Deep Reinforcement Learning That Matters** （93.0）：《Deep RL That Matters》经典实证研究：可复现性、超参敏感性、方差与实验报告规范——直击训练稳定性工具箱
- **[5] What Matters In On-Policy Reinforcement Learning? A Large-Scale Empiri** （93.0）：>50个on-policy实现选择的大规模实证、25万agent、给出可操作训练建议，直击超参敏感性与实现细节。
- **[6] What Matters for On-Policy Deep Actor-Critic Methods? A Large-Scale St** （93.0）：同款大规模actor-critic实现选择实证研究的ICLR版，实战do/don't建议，直接命中。
- **[7] Temporal Logic Guided Safe Reinforcement Learning Using Control Barrie** （92.0）：直接命中:用控制屏障函数(CBF)+时序逻辑做安全RL与探索保障,正是研究点(5)
- **[8] Reproducibility of Benchmarked Deep Reinforcement Learning Tasks for C** （91.0）：连续控制 DRL 复现性/超参敏感性/方差实证研究并给报告准则，正中 empirical study 与 do/don't
- **[9] Reward-Adaptive Reinforcement Learning: Dynamic Policy Gradient Optimi** （90.0）：多头critic分解奖励通道+动态加权,直击(1)reward设计与(6)双足locomotion奖励工程,且对比sum-reward给出经验结论。
- **[10] STRIDE: Automating Reward Design, Deep Reinforcement Learning Training** （90.0）：直击 reward 设计自动化+humanoid locomotion 训练,且与 EUREKA 横向对比,实战导向满分命中
- **[11] Safe Learning in Robotics: From Learning-Based Control to Safe Reinfor** （88.0）：直击安全RL与CBF/控制论安全认证，统一control与RL语言，正是研究思路第(5)点核心
- **[12] Learning to Walk Via Deep Reinforcement Learning** （88.0）：最大熵 RL(SAC)真机学走路，主打少调参、对超参敏感性与样本效率——直击训练稳定性与算法工具箱
- **[13] Addressing Function Approximation Error in Actor-Critic Methods** （88.0）：TD3经典论文，解决actor-critic高估偏差的实现细节(双critic/延迟更新/目标网络)，直击稳定性trick与off-policy改进
- **[14] High-Dimensional Continuous Control Using Generalized Advantage Estima** （86.0）：GAE 是降方差、稳定策略梯度的核心实现技巧，PPO 基础，locomotion 实验，极实用
- **[15] Safe reinforcement learning: A control barrier function optimization a** （86.0）：直接命中CBF+安全RL：把控制屏障函数嵌入代价函数、用off-policy RL求安全最优策略，正是用户重点关注的安全增强方向
- **[16] Penalized Proximal Policy Optimization for Safe Reinforcement Learning** （86.0）：P3O 安全RL，惩罚法做约束优化+在locomotion任务上有reward/约束满足对比，直接命中算法与安全两块
- **[17] Automatic Intrinsic Reward Shaping for Exploration in Deep Reinforceme** （86.0）：自动内在reward shaping促探索并附内在奖励工具包,正中reward设计+稀疏奖励探索且实战可用
- **[18] Safe Reinforcement Learning via Shielding** （85.0）：AAAI的Shielding安全RL,学习/执行期强制安全约束,强相关研究点(5)安全增强
- **[19] Challenges of real-world reinforcement learning: definitions, benchmar** （85.0）：真实世界RL九大挑战+benchmark,正是实战导向的训练坑清单与do/don't分析
- **[20] End-To-End Robotic Reinforcement Learning without Reward Engineering** （85.0）：专攻去除人工reward工程、用成功样例+主动查询学奖励,直击reward设计与specification痛点
- **[21] Safe exploration in model-based reinforcement learning using control b** （85.0）：基于控制屏障函数的模型基RL安全探索，命中CBF安全+探索+model-based，Automatica顶刊
- **[22] Regularization Matters in Policy Optimization - An Empirical Study on ** （85.0）：连续控制策略优化的正则化 empirical study,正是训练稳定性/实现细节这条线,标题强相关(无摘要略扣)
- **[23] PPG Reloaded: An Empirical Study on What Matters in Phasic Policy Grad** （85.0）：PPG实证研究"什么最重要"，正是实现细节/超参empirical study(第2、4条)，ICML顶会。
- **[24] Tiered Reward: Designing Rewards for Specification and Fast Learning o** （85.0）：专讲reward设计原则与快速学习,正中reward shaping/specification这条主线,有理论+多算法验证
- **[25] SafeAdapt: Provably Safe Policy Updates in Deep Reinforcement Learning** （85.0）：可证明安全的RL策略更新，约束/安全RL，直接命中第(5)条安全增强与RL结合。
- **[26] Augmented Proximal Policy Optimization for Safe Reinforcement Learning** （84.0）：APPO 针对训练振荡/稳定收敛+精确约束、易实现且有大量baseline对比，实战导向
- **[27] Constraint-Conditioned Policy Optimization for Versatile Safe Reinforc** （84.0）：约束条件化的安全RL策略优化，命中第(4)约束优化与第(5)安全，NeurIPS高质量。
- **[28] Value Improved Actor Critic Algorithms** （83.0）：直接改进 TD3/SAC 等 off-policy actor-critic，权衡贪婪化与稳定性，命中算法改进与训练稳定性诉求
- **[29] From Sparse to Dense: Toddler-inspired Reward Transition in Goal-Orien** （82.0）：幼儿启发的稀疏→势函数稠密奖励过渡,直击reward shaping(1)与稀疏奖励课程(3),机械臂/导航有实验且分析了策略loss地形。
- **[30] #Exploration: A Study of Count-Based Exploration for Deep Reinforcemen** （80.0）：count-based探索在高维连续深度RL,直接命中稀疏奖励探索/内在激励这条线,有大量benchmark对比
- **[31] Distributional Soft Actor-Critic with Three Refinements** （80.0）：DSAC-T专治训练不稳定与对reward scaling的敏感性、且无需逐任务调超参,正中第2点(稳定性trick+超参敏感性empirical)与SAC改进。
- **[32] On the Emergence of Whole-Body Strategies From Humanoid Robot Push-Rec** （80.0）：humanoid 全身 push-recovery，奖励项融入专家知识，正是全身控制上的 reward 工程实例
- **[33] Secrets of RLHF in Large Language Models Part I: PPO** （80.0）：系统解剖PPO各组件对训练的影响、策略约束与奖励设计，正中训练稳定性与实现细节诉求（虽是RLHF场景）。
- **[34] What Matters for Batch Online Reinforcement Learning in Robotics?** （80.0）：机器人RL系统性empirical study，横向比较算法类/策略抽取/表达力三轴，正合'训练工具箱+实验对比'偏好
- **[35] Multimodal bipedal locomotion generation with passive dynamics via dee** （80.0）：双足locomotion DRL,显式讲reward权重规划+课程学习,正是reward工程与课程学习实例
- **[36] No More Hand-Tuning Rewards: Masked Constrained Policy Optimization fo** （80.0）：直接针对'手调reward耗时'痛点提出免调reward的安全RL，命中reward工程与安全两块
- **[37] Extreme Value Policy Optimization for Safe Reinforcement Learning** （80.0）：约束RL新算法(极值理论建模尾部代价)，命中SAC/PPO之外的约束优化与安全RL
- **[38] From Reward Shaping to Q-Shaping: Achieving Unbiased Learning with LLM** （80.0）：直接讲 reward shaping→Q-shaping 的无偏知识注入与样本效率，命中 reward 设计主题且有 20 环境实验对比
- **[39] Predictive Control Barrier Functions for Online Safety Critical Contro** （80.0）：预测式控制屏障函数，正中研究思路第(5)条CBF安全增强，虽未直接结合RL但是该方向核心方法。
- **[40] Leveraging exploration in off-policy algorithms via normalizing flows** （80.0）：用normalizing flows扩展SAC提升探索,正中SAC改进+off-policy+稀疏奖励探索,实现细节明确
- **[41] Safe Reinforcement Learning with Probabilistic Control Barrier Functio** （80.0）：概率 CBF 嵌入 RL 策略做安全控制,正中 CBF×RL 结合这条重点线
- **[42] Reinforcement Learning for Robust Parameterized Locomotion Control of ** （78.0）：Cassie 双足 locomotion 的 model-free RL + 域随机化做 sim-to-real 鲁棒控制，含可操作 trick
- **[43] Humanoid Whole-Body Badminton via Multi-Stage Reinforcement Learning** （78.0）：humanoid 全身羽毛球三阶段课程学习，含奖励塑形与课程设计的实战 pipeline
- **[44] Recursively Feasible Probabilistic Safe Online Learning with Control B** （78.0）：CBF+GP的概率安全在线学习，递归可行性与主动安全探索，直接服务安全增强方法这条重点线
- **[45] Sim-to-Real: Learning Agile Locomotion For Quadruped Robots** （76.0）：四足locomotion用简单reward+域随机化训鲁棒策略,提供locomotion上的reward工程与训练稳定实例
- **[46] A survey of preference-based reinforcement learning methods** （76.0）：偏好式 RL 综述，直接针对 reward shaping 难题与奖励设计的设计原则，可操作
- **[47] Model-based Safe Deep Reinforcement Learning via a Constrained Proxima** （76.0）：模型基+约束 PPO 的 safe RL，同时覆盖安全探索、PPO、model-based 三条线，实战导向
- **[48] Input-to-State Safety for Reinforcement Learning.** （76.0）：直接做强化学习的 input-to-state 安全，命中 CBF/safe-RL 安全增强这条重点线
- **[49] Humanoid Manipulation Interface: Humanoid Whole-Body Manipulation from** （76.0）：人形全身操控，明确点出reward engineering痛点与sim-to-real RL，契合第(6)条全身控制reward工程实例。
- **[50] Learning Complex Dexterous Manipulation with Deep Reinforcement Learni** （75.0）：DAPG经典:示范降低样本复杂度、解决高维稀疏奖励探索并提升鲁棒性,命中(2)(3)(6)。
- **[51] Constrained Variational Policy Optimization for Safe Reinforcement Lea** （75.0）：变分约束策略优化，明确针对 primal-dual 训练不稳定问题、含连续机器人实验与开源代码，命中稳定性+约束算法
- **[52] Curiosity Driven Reinforcement Learning for Motion Planning on Humanoi** （75.0）：iCub人形机器人上的好奇心/内在动机驱动RL运动规划,命中稀疏奖励探索(3)与人形控制(6),Frontiers正规OA。
- **[53] Soft Actor-Critic Algorithm in High-Dimensional Continuous Control Tas** （75.0）：SAC高维连续控制的超参敏感性(熵权重/学习率/reward scaling)实证，正中第(1)(2)条，惟会议层级一般。
- **[54] Causal-Paced Deep Reinforcement Learning** （75.0）：课程RL框架,直接命中稀疏奖励探索+课程学习,且在Bipedal Walker等有实验对比
- **[55] Safe Reinforcement Learning With Stability Guarantee for Motion Planni** （74.0）：把 Lyapunov 稳定性保证融入 SAC 做安全运动规划，直接涉及 SAC 稳定性与安全增强
- **[56] Efficient Continuous Control with Double Actors and Regularized Critic** （74.0）：双actor正则化critic缓解DDPG/TD3的高低估偏差并提升探索,直击工具箱第4点(SAC/PPO之外的off-policy改进)与第2点训练稳定性,AAAI来源可靠。
- **[57] Decoupled Policy Actor-Critic: Bridging Pessimism and Risk Awareness i** （74.0）：DAC用悲观/乐观双actor兼顾风险意识与探索,在locomotion/manipulation上提样本效率,贴合算法扩展+稳定性且沾边安全(风险感知),AAAI可靠。
- **[58] AFU: Actor-Free critic Updates in off-policy RL for continuous control** （74.0）：AFU解耦critic更新、剖析SAC陷局部最优的失效模式并改进,属SAC之外的off-policy新算法且带failure-mode分析,实战价值高。
- **[59] The Role of Domain Randomization in Training Diffusion Policies for Wh** （74.0）：人形全身控制的实证研究，考察数据集多样性/规模如何影响扩散策略训练，属算法多样性+训练经验+人形reward工程范畴
- **[60] Learning robotic manipulation skills with multiple semantic goals by c** （74.0）：稀疏奖励下好奇心驱动探索解决hard exploration，正中第(3)条稀疏奖励探索。
- **[61] Improved Soft Actor-Critic: Mixing Prioritized Off-Policy Samples with** （74.0）：改进SAC的优先级回放+on/off-policy混采,直接对应SAC实现细节、稳定性与样本效率的实战调优。
- **[62] Deep Reinforcement Learning-Based End-to-End Navigation of Mobile Robo** （72.0）：移动机器人导航的reward shaping+HER+TD3,含奖励塑形与稀疏奖励/收敛加速的可操作trick
- **[63] Transformer-based human-motion forecasting coupled with safe reinforce** （72.0）：约束策略优化+CBF shield 的 safe RL 实战框架，含基线对比，正中 CBF 与 RL 结合
- **[64] Reinforcement Learning with Stochastic Reward Machines** （72.0）：随机奖励机处理稀疏且依赖动作序列的噪声奖励,直接对应奖励设计(1)与稀疏奖励(3),有案例对比。
- **[65] CVaR-Constrained Policy Optimization for Safe Reinforcement Learning** （71.0）：CVaR 约束策略优化做 safe RL，风险尾部约束+trust-region，丰富约束优化算法工具箱
- **[66] JuggleRL: Mastering Ball Juggling with a Quadrotor via Deep Reinforcem** （71.0）：四旋翼颠球DRL,详述reward shaping+域随机化+sim2real鲁棒性技巧,实战训练细节丰富
- **[67] Hierarchical deep reinforcement learning: integrating temporal abstrac** （70.0）：分层DQN用内在动机解稀疏奖励探索，命中课程/探索侧面但偏方法非工程清单。
- **[68] Stochastic Neural Networks for Hierarchical Reinforcement Learning** （70.0）：用单一proxy奖励预训练技能再解稀疏奖励下游任务，关联探索与奖励设计但偏算法。
- **[69] Safe Off-Policy Deep Reinforcement Learning Algorithm for Volt-VAR Con** （70.0）：约束 soft actor-critic 解 constrained MDP,off-policy+安全约束算法直接可借鉴(应用域是电网)
- **[70] A Survey on Offline Reinforcement Learning: Taxonomy, Review, and Open** （70.0）：Offline RL综述,覆盖SAC/PPO之外算法分类与benchmark横向比较,直击算法工具箱诉求
- **[71] Safe Reinforcement Learning for Autonomous Vehicles through Parallel C** （70.0）：并行约束策略优化(PCPO)扩展 actor-critic 加风险网络，属 SAC/PPO 之外的安全约束算法与实现细节
- **[72] VCSAP: Online reinforcement learning exploration method based on visit** （70.0）：计数探索同时挂PPO/TRPO在MuJoCo稀疏奖励上实测对比,直接命中工具箱探索+算法横比,正刊
- **[73] Combining Soft-Actor Critic with Cross-Entropy Method for Policy Searc** （70.0）：CEM-SAC混合进化策略改进off-policy,MuJoCo上与SAC/TD3基线对比,命中算法丰富化与稳定性诉求。
- **[74] Doubly Robust Off-Policy Actor-Critic Algorithms for Reinforcement Lea** （70.0）：双稳健off-policy critic估计降方差、在reward随机/被污染时仍稳健并自称利于安全RL,贴合稳定性+reward鲁棒性两点。
- **[75] Soft Actor-Critic with Beta Policy via Implicit Reparameterization Gra** （70.0）：用隐式重参数让SAC用beta策略、在机器人locomotion上比较策略分布选择,属可操作的实现细节/超参选择,相关。
- **[76] Mixture of Autoencoder Experts Guidance using Unlabeled and Incomplete** （70.0）：用专家示范映射成shaped intrinsic reward做探索,直接命中稀疏奖励探索+奖励塑形主题
- **[77] Value Bonuses using Ensemble Errors for Exploration in Reinforcement L** （70.0）：集成误差做 value bonus 的定向探索，直接对应稀疏奖励/探索一栏，有多基线实验对比
- **[78] Mirror Descent Safe Policy Optimization for Reinforcement Learning Age** （70.0）：镜像下降做安全策略优化，约束探索，与稀疏奖励探索+安全增强相关
- **[79] A graph-based safe reinforcement learning method for multi-agent coope** （70.0）：图结构安全 MARL 用约束策略优化，指出仅靠 reward shaping 不保安全，命中安全增强与约束优化
- **[80] Deep dive into model-free reinforcement learning for underwater locomo** （70.0）：无模型RL在水下locomotion的理论与实践,贴合点(6)locomotion实战与算法实践
- **[81] Constrained Policy Optimization with Explicit Behavior Density For Off** （68.0）：约束策略优化+offline RL(NeurIPS),命中 SAC/PPO 之外的约束优化算法谱系
- **[82] ReLU to the Rescue: Improve Your On-Policy Actor-Critic with Positive ** （68.0）：三处on-policy actor-critic改动(正优势/谱归一化/dropout探索)在MuJoCo上胜过PPO/SAC,含探索与实现细节,相关偏理论推导。
- **[83] Self-supervised network distillation: An effective approach to explora** （68.0）：稀疏奖励内在动机探索(SND蒸馏误差),10个难探索环境实测对比,直接服务工具箱第(3)点
- **[84] Broad Critic Deep Actor Reinforcement Learning for Continuous Control** （68.0）：在 SAC/TD3/DDPG 上做混合架构改进并比训练效率，属算法横向增强，IEEE TNNLS 正规来源
- **[85] Game-Theoretic Constrained Policy Optimization for Safe Reinforcement ** （68.0）：博弈论视角的约束策略优化，处理多目标梯度冲突，与安全约束RL强相关但偏方法理论
- **[86] CIM: Constrained Intrinsic Motivation for Sparse-Reward Continuous Con** （68.0）：用拉格朗日约束优化平衡内在/外在奖励,兼顾第(3)探索与(4)约束优化及奖励组合设计,可操作
- **[87] What Matters in RL-Based Methods for Object-Goal Navigation? An Empiri** （68.0）：RL方法的'什么真正起作用'大规模实证+统一框架+设计准则，正是训练经验/调参敏感性所需方法论，唯应用域为导航
- **[88] Offline constrained policy optimization with safe anchoring.** （68.0）：离线安全约束策略优化，Safety-Gym有实验，相关但离线设定偏离在线训练痛点
- **[89] Scaling data-driven robotics with reward sketching and batch reinforce** （68.0）：学习型reward函数+batch/off-policy RL在真机操作,命中reward工程与SAC/PPO之外算法
- **[90] Experimental evaluation of model-free reinforcement learning algorithm** （67.0）：实测对比四种actor-critic算法、专门考察不同reward函数与数据效率/鲁棒性，正中empirical study(2)+算法比较(4)，仅领域是HVAC。
- **[91] Model-based Reinforcement Learning: A Survey** （66.0）：模型基RL权威综述,系统覆盖SAC/PPO之外的算法谱系,适合构建工具箱的横向认知
- **[92] Online Meta-Critic Learning for Off-Policy Actor-Critic Methods** （66.0）：元critic在线加速actor-critic学习、可叠加在SAC/TD3/DDPG上,属可操作的训练提速trick,相关但偏算法增量。
- **[93] Lazy Agents: A New Perspective on Solving Sparse Reward Problem in Mul** （66.0）：多智能体稀疏奖励的新视角，沾第(3)条稀疏奖励，但多智能体设定与单策略训练目标略偏。
- **[94] Improved Learning of Robot Manipulation Tasks Via Tactile Intrinsic Mo** （66.0）：稀疏奖励下基于触觉的内在激励+contact-prioritized replay,命中探索与 reward shaping 实例
- **[95] Comparing Deep Reinforcement Learning and Evolutionary Methods in Cont** （66.0）：PPO/DDPG 与进化方法横向实测对比、结论是无一致赢家，符合算法比较与 do/don't 取向
- **[96] Safe Control Synthesis via Input Constrained Control Barrier Functions** （66.0）：输入约束 CBF 安全控制综合，正是用户重点关注的 CBF 安全增强方法基础，虽未直接结合 RL
- **[97] Self-Organizing Dual-Buffer Adaptive Clustering Experience Replay (SOD** （66.0）：安全RL+经验回放改进(off-policy),命中算法增强与安全两条线,但无摘要难核实细节
- **[98] Variational Dynamic for Self-Supervised Exploration in Deep Reinforcem** （65.0）：变分动态模型做自监督探索解稀疏奖励，含真实机械臂实验，关联探索侧面。
- **[99] An Algorithmic Perspective on Imitation Learning** （64.0）：模仿学习算法综述含实现建议,作为绕开reward设计的替代路线相关且实用
- **[100] Mastering Complex Control in MOBA Games with Deep Reinforcement Learni** （64.0）：MOBA游戏RL但给出dual-clip PPO、action mask等可操作的PPO训练稳定性技巧与系统实现细节,对工具箱(2)(4)有用。

## 库内引用关系（31 条）

- 《Safe reinforcement learning: A control barrie》→ 引用 →《End-to-End Safe Reinforcement Learning throug》
- 《Challenges of real-world reinforcement learni》→ 引用 →《Deep Reinforcement Learning That Matters》
- 《Experimental evaluation of model-free reinfor》→ 引用 →《Deep Reinforcement Learning That Matters》
- 《Safe exploration in model-based reinforcement》→ 引用 →《Safe reinforcement learning: A control barrie》
- 《Safe exploration in model-based reinforcement》→ 引用 →《End-to-End Safe Reinforcement Learning throug》
- 《Safe Reinforcement Learning for Autonomous Ve》→ 引用 →《Safe Reinforcement Learning via Shielding》
- 《On the Emergence of Whole-Body Strategies Fro》→ 引用 →《Sim-to-Real: Learning Agile Locomotion For Qu》
- 《Safe Reinforcement Learning Using Robust Cont》→ 引用 →《End-to-End Safe Reinforcement Learning throug》
- 《Safe Reinforcement Learning Using Robust Cont》→ 引用 →《Safe Learning in Robotics: From Learning-Base》
- 《A Survey on Offline Reinforcement Learning: T》→ 引用 →《Safe Reinforcement Learning With Stability Gu》
- 《CVaR-Constrained Policy Optimization for Safe》→ 引用 →《Safe Learning in Robotics: From Learning-Base》
- 《Game-Theoretic Constrained Policy Optimizatio》→ 引用 →《Penalized Proximal Policy Optimization for Sa》
- 《Game-Theoretic Constrained Policy Optimizatio》→ 引用 →《Safe Reinforcement Learning via Shielding》
- 《Game-Theoretic Constrained Policy Optimizatio》→ 引用 →《CVaR-Constrained Policy Optimization for Safe》
- 《Safe Off-Policy Deep Reinforcement Learning A》→ 引用 →《Addressing Function Approximation Error in Ac》
- 《Safe Learning in Robotics: From Learning-Base》→ 引用 →《End-to-End Safe Reinforcement Learning throug》
- 《Learning Complex Dexterous Manipulation with 》→ 引用 →《Deep Reinforcement Learning That Matters》
- 《Learning to Walk Via Deep Reinforcement Learn》→ 引用 →《Deep Reinforcement Learning That Matters》
- 《Learning to Walk Via Deep Reinforcement Learn》→ 引用 →《Sim-to-Real: Learning Agile Locomotion For Qu》
- 《End-To-End Robotic Reinforcement Learning wit》→ 引用 →《Learning Complex Dexterous Manipulation with 》
- 《Model-based Reinforcement Learning: A Survey》→ 引用 →《Deep Reinforcement Learning That Matters》
- 《Model-based Reinforcement Learning: A Survey》→ 引用 →《Hierarchical deep reinforcement learning: int》
- 《Deep Reinforcement Learning That Matters》→ 引用 →《Reproducibility of Benchmarked Deep Reinforce》
- 《End-to-End Safe Reinforcement Learning throug》→ 引用 →《Safe Reinforcement Learning via Shielding》
- 《Multimodal bipedal locomotion generation with》→ 引用 →《Learning to Walk Via Deep Reinforcement Learn》
- 《Temporal Logic Guided Safe Reinforcement Lear》→ 引用 →《Safe Reinforcement Learning via Shielding》
- 《Temporal Logic Guided Safe Reinforcement Lear》→ 引用 →《End-to-End Safe Reinforcement Learning throug》
- 《Online Meta-Critic Learning for Off-Policy Ac》→ 引用 →《Addressing Function Approximation Error in Ac》
- 《What Matters In On-Policy Reinforcement Learn》→ 引用 →《Deep Reinforcement Learning That Matters》
- 《What Matters In On-Policy Reinforcement Learn》→ 引用 →《Reproducibility of Benchmarked Deep Reinforce》
- 《What Matters for On-Policy Deep Actor-Critic 》→ 引用 →《Reproducibility of Benchmarked Deep Reinforce》
