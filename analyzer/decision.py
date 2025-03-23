import sys
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Adjust if needed
sys.path.append(project_root)
import json
from middleware import history
import yaml
import random

class TransDecision:
    def __init__(self, base_dir, it, config_path):
        self.base_dir = base_dir
        self.it = it
        with open(config_path, "r") as file:
            self.config = yaml.safe_load(file)
        self.LANGS = self.config["langs"]
        cal_dir = os.path.join(base_dir, "cal_results")
        base_results_file = None
        for file in os.listdir(cal_dir):
            if "results" in file and "iter" not in file and file.endswith(".json"):
                base_results_file = file
                break
        base_results_file_path = os.path.join(cal_dir, base_results_file)
        with open(base_results_file_path, "r") as file:
            data = json.load(file)
        lang_p10 = {l: data[l]["pass@10"] for l in self.LANGS}
        self.sorted_pl = sorted(lang_p10.keys(), key=lambda lang: lang_p10[lang], reverse=True)
        
    def get_random_lang(self, base_dir, id, langs):
        historical_langs = history.get_historical_chain(base_dir, id, self.it, "target_lang")
        eligible_langs = list(set(langs) - set(historical_langs))
        if len(eligible_langs) == 0:
            target = random.choice(langs)
        else:
            target = random.choice(eligible_langs)
        return target
    
    def get_decision(self, base_dir, it, id):
        dec_path = os.path.join(base_dir, f"iter_{it}/decision.json")
        with open(dec_path, "r") as f:
            data = json.load(f)
        return data[id]
    
    def get_diff(self, base_dir):
        lang_path = os.path.join(base_dir, f"lang.json")
        with open(lang_path, "r") as f:
            data = json.load(f)
        return data['lang']
    
    def decide_lang(self, sample=None, it=1, mode="greedy"):
        assert it > 0, "Invalid iteration!"
        assert mode in ["greedy", "random", "reasoning", "nohist", "nocot", "diff"], "Invalid mdoe!"
        if mode == "greedy":
            return self.sorted_pl[it - 1]
        if mode == "random":
            return self.get_random_lang(self.base_dir, sample["bug_code_uid"], self.LANGS)
        if mode in ["reasoning", "nohist", "nocot"]:
            return self.get_decision(self.base_dir, self.it, sample["bug_code_uid"])
        if mode == "diff":
            return self.get_diff(self.base_dir)

            