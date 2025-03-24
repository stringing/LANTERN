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