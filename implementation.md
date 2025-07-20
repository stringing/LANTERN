# Implementation Details
To ensure a fair comparison, key hyperparameters were standardized across our approach and all baselines.

### Generation Temperature:

- Repair Tasks: Set to 1.0 for our approach and all baseline methods (ChatRepair, Self-Planning, and Self-Collaboration).
- Translation Tasks: Set to a more deterministic 0.3 for our approach, aligning with the xCodeEval benchmark settings.
- Other Generative Tasks (Baselines): The default settings in the original work were used for other tasks, such as planning and analysis, within the baseline methods.

### Maximum Generated Tokens:

Fixed at 4096 for all approaches, which is consistent with the default configuration of DeepSeek-V3.

### Maximum Iterations:

A maximum of 11 iterations was set for our approach to thoroughly explore the 11 languages in the xCodeEval benchmark.
This 11-iteration limit was also applied to baseline methods that involve repetitive code refinement.

### Execution Environment:

- CPU: 12-core
- RAM: 64 GB
- Operating System: Ubuntu 22.04
- Python: 3.9.2