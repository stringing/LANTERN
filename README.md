# Major Revision - Additional Information

## Prompt Design

The description and ALL details of prompt design, which was supposed to be in **Section 4 Approach**, is now put in the additional document [prompt](https://anonymous.4open.science/r/LANTERN-67EE/prompt.md) due to page limit of the paper.

## Implementation Details

Implementation Details can be referred in the document [implementation](https://anonymous.4open.science/r/LANTERN-67EE/implementation.md).

## Addtional Experiments

### Real-world Generalizability

#### 1. SWE-Bench Lite

#### Prerequisite

Install the SWE-Bench framework for evaluation:

```bash
cd baseline/SWE-bench
pip install -e .
```

In *baseline/Agentless*:

Install Agentless according to the document at [Agentless](https://github.com/OpenAutoCoder/Agentless/).

Please download the repository structure in advance at [repo_structure](https://drive.google.com/file/d/15-4XjTmY48ystrsc_xcvtOkMs3Fx8RoW/view?usp=sharing) and prior generation from AGENTLESS for bug context extraction at [swe-bench-lite](https://github.com/OpenAutoCoder/Agentless/releases/download/v1.5.0/agentless_swebench_lite.zip).

Unzip the compressed repository structure file in *baseline/Agentless*. 

Export the structure location:

```bash
export PROJECT_FILE_LOC={xxx/Agentless/repo_structure/repo_structures}
```

Create a *results* folder in *baseline/Agentless*.

Unzip the agentless_swebench_lite.zip in *results*.


The final structures of them should be:

```bash
Agentless
...repo_structure
......repo_structures
.........astropy__astropy-6938.json
        ...
...results
......swe-bench-lite
.........edit_location_individual
        ...
```


Next, please set the OpenAI configurations in Agentless/script/api_key.sh.

Then run the script to repair:

```bash
cd baseline/Agentless

bash script/run_trans.sh

```

Finally, get the result:

```bash
python script/cmp_all.py ../SWE-bench
```

#### 2. Defects4J

**ChatRepair:**

```bash
export API_KEY=your_api_key
export API_BASE=your_api_base
export MODEL_NAME=your_model_name

cd baseline/FSE_ChatRepair/code/Generation

python repair.py --folder Results/1.2f --lang java --dataset defects4j-1.2-function --few_shot 1 --chain_length 3 --total_tries 11 --assertion_line

python repair.py --folder Results/1.2sh --lang java --dataset defects4j-1.2-single-hunk --few_shot 1 --chain_length 3 --total_tries 11 --assertion_line

python repair.py --folder Results/1.2sl --lang java --dataset defects4j-1.2-single-line --few_shot 1 --chain_length 3 --total_tries 11 --assertion_line

python repair.py --folder Results/2.0 --lang java --dataset defects4j-2.0-single-line --few_shot 1 --chain_length 3 --total_tries 11 --assertion_line
```

Combine 3 scenarios for D4J 1.2 to count the solved bugs:

```bash
python myutil/count_num_proj.py Results/1.2f

python myutil/count_num_proj.py Results/1.2sh

python myutil/count_num_proj.py Results/1.2sl

python myutil/combine.py Results/CR_combine
```

Count the solved bugs on D4J 2.0:

```bash
python myutil/count_num.py Results/2.0
```

**LANTERN:**


```bash
export API_KEY=your_api_key
export API_BASE=your_api_base
export MODEL_NAME=your_model_name

cd baseline/ChatRepair_LANTERN/code/Generation

bash run12.sh

bash run20.sh
```

Count the solved bugs:

```bash
python myutil/count_num_proj.py Results/1.2f

python myutil/count_num.py Results/2.0

```

### Approach Comparison

- **ChatRepair**

```bash
cd LANTERN

python main.py --config config/add/tr_chatreapir.yaml

```

- **Self-Planning**

```bash
export API_KEY=your_api_key
export API_BASE=your_api_base
export MODEL_NAME=your_model_name

cd baseline/self-planning

python planning.py --base-dir <result directory> --num-proc <number of process> --dataset-path <xcodeeval_dataset>

python implementation.py --base-dir <result directory> --num-proc <number of process>
```

- **Self-Collaboration**



```bash
export API_KEY=your_api_key
export API_BASE=your_api_base
export MODEL_NAME=your_model_name

cd baseline/Self-collaboration-Code-Generation

bash run.sh

bash evaluate.sh
```

### Model Generalizability

(Please set corresponding OpenAI API before running the scripts.)

- **Claude 3.5 Sonnet**

```bash
python main.py --config config/add/tr_reasoning_claude.yaml
```

- **QWen2.5-72B-Instruct**

```bash
python main.py --config config/add/tr_reasoning_qwen.yaml
```


# LANTERN

Artifacts of "Unlocking LLM Repair Capabilities in Low-Resource Programming Languages Through Cross-Language Translation and Multi-Agent Refinement".

# Project Structure
```bash
.
├── analyzer                    # reason about the optimal target language 
│   ├── decide.py
│   └── decision.py
├── config                      # configuration files for different strategies
├── dataset                     # APR evaluation benchmark of xCodeEval
│   └── apr.tar.gz
├── evaluator                   # evaluate the repaired code and calculate metrics
│   ├── eval_apr.py
│   └── get_result.py
├── logs                        # log records of each execution
├── middleware                  # coordination, historical storage and retrieval, prompt construction, etc.
│   ├── coordinator.py
│   ├── history.py
│   ├── prompt.py
│   ├── repair_retrieval.py
│   └── retrieval.py
├── repairer                    # program repair
│   ├── gen_apr.py
│   └── re_gen.py
└── translator                  # bug translation and code back-translation
    ├── back_translate.py
    ├── initilize.py
    └── translate.py
├── main.py                     # the main entry of the pipeline
```

# Dependency
### Docker Engine
Install docker engine at [Docker-CE](https://docs.docker.com/engine/install/).

### Python Environment
Install Python environment with necessary packages.
```bash
conda create -n lantern python=3.9.2
conda activate lantern
cd LANTERN
pip install -r requirements.txt
```

### ExecEval
Install the execution engine of xCodeEval at [ExecEval](https://github.com/ntunlp/execeval) and start the docker server.
```bash
git clone https://github.com/ntunlp/ExecEval
cd ExecEval
docker build . -t exec-eval:1.0
docker run -it -p 5000:5000 -e NUM_WORKERS=37 exec-eval:1.0
```

# Pipeline Configuration
Below is a template of the config file.
```yaml
base_dir: /root/my/data/xCodeEval/evaluation/tr_reasoning   # the execution directory where all outcomes are produced
dataset_path: /root/my/data/xCodeEval/apr                   # the benchmark path
dry_run: 0                      
gen:
  nattempt: 20                                              # number of samples generated for each problem
  nsample: 1
  temperature: 1.0                                          # LLM temperature
hist_top_k: 15                                              # number of top-k historical feedback
langs:                                                      # programming language scope
- C
- C#
- C++
- Go
- Java
- Javascript
- Kotlin
- PHP
- Python
- Ruby
- Rust
log_dir: logs                                               # log directory
name: reasoning trans-repair v3 lt                          # name of this run
num_proc: 17                                                # number of paralell processes
repair:
  mode: vanilla                                             # repair mode [vanilla/cmp]
result:
  k: 20                                                     # calculation from Pass@1 to Pass@k
state:                                                      # current state of the pipeline
  action: save_history                                      # last finished action
  it: 11                                                    # current iteration
termination:                                                # termination condition
  max_it: 11                                                # maxinal number of iterations
translate:
  mode: reasoning                                           # translation mode [greedy/random/reasoning/notrans/nohist]
unfixed_k: 0                                                

```

# Pipeline Execution
Decompress the dataset:
```bash
tar -xzvf dataset/apr.tar.gz -C dataset
```
Set the base_dir, dataset_path, and other necessary configurations in the yaml config files.

Set the API configuration of your LLM:
```bash
export API_KEY=your_api_key
export API_BASE=your_api_base
export MODEL_NAME=your_model_name
```
### Greedy strategy
```python
python main.py --config config/tr_greedy.yaml
```

### Random strategy
```python
python main.py --config config/tr_random.yaml
```

### Reasoning strategy
```python
python main.py --config config/tr_reasoning.yaml
```

### w/o translation
```python
python main.py --config config/tr_cmp.yaml
```

### w/o historical feedback
```python
python main.py --config config/tr_cmp_nohist.yaml
```