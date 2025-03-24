import yaml
from repairer import gen_apr, re_gen
from translator import initilize, translate, back_translate
from analyzer import decide
from evaluator import eval_apr, get_result
from . import history
import logging
import os

class Coordinator:
    def __init__(self, config_path, restart):
        self.config_path = config_path
        with open(config_path, "r") as file:
            self.config = yaml.safe_load(file)

        logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s - %(levelname)s - %(message)s", 
        datefmt="%Y-%m-%d %H:%M:%S", 
        handlers=[
            logging.FileHandler(os.path.join(self.config["log_dir"], f"{self.config['name']}_logs.txt")), 
            logging.StreamHandler() 
            ]
        )
    
    def __get_args(self, *args):
        res = {}
        for arg in args:
            if ":" in arg:
                k, v = arg.split(":")
                res[k] = int(v) if v.isnumeric() else v
            else:
                v = None
                for k in arg.split("."):
                    if v is None:
                        v = self.config[k]
                    else:
                        v = v[k]
                res[arg.split(".")[-1]] = v
        return res
    
    def __get_repair_mode(self):
        return self.config["repair"]["mode"]
    
    def __check_termination(self):
        '''
        Check termination conditions.
        '''
        if self.__get_state("it") >= self.__get_args("termination.max_it")["max_it"]:
            return True
        return False
    
    def __check_run(self, action, condition, kwarg):
        '''
        Execute the action if the condition is satisfied.
        '''
        if condition:
            action(**kwarg)
            return True
        return False
    
    def __perform_action(self, action, condition, it, action_name, desc, kwarg):
        self.__log_record(it, action_name, desc)
        return self.__check_run(action, condition, kwarg)
    
    def __get_state(self, k):
        return self.config["state"][k]
    
    def __update_state(self, it=-1, action=None):
        if it != -1:
            self.config["state"]["it"] = it
        if action is not None:
            self.config["state"]["action"] = action
        self.__update_config()
    
    def __update_config(self):
        with open(self.config_path, "w") as file:
            yaml.dump(self.config, file)
    
    def __check_state(self, k, v, op="eq"):
        if op == "eq":
            return self.config["state"][k] == v
        elif op == "ge":
            return self.config["state"][k] >= v
        elif op == "le":
            return self.config["state"][k] <= v
        elif op == "g":
            return self.config["state"][k] > v
        elif op == "l":
            return self.config["state"][k] < v
        elif op == "in":
            return self.config["state"][k] in v
        else:
            return False
    
    def __check_mode(self, mode, op="eq"):
        if op == "eq":
            return self.config["translate"]["mode"] == mode
        elif op == "not":
            return self.config["translate"]["mode"] != mode
        elif op == "in":
            return self.config["translate"]["mode"] in mode
        else:
            return False
    
    def _base_run(self):
        if self.__perform_action(
            gen_apr.run, 
            self.__check_state("it", 0) and self.__check_state("action", "start"), 
            0, 
            "gen_apr", 
            "generating patched code", 
            self.__get_args("base_dir", "num_proc", "dry_run", "gen.nsample", "gen.nattempt", "gen.temperature", "dataset_path")
        ):
            self.__update_state(action="gen")
        
        if self.__perform_action(
            eval_apr.run, 
            self.__check_state("it", 0) and self.__check_state("action", "gen"), 
            0, 
            "eval_apr", 
            "evaluating patched code", 
            self.__get_args("base_dir", "state.it")
        ):
            self.__update_state(action="eval")
        
        if self.__perform_action(
            get_result.run, 
            self.__check_state("it", 0) and self.__check_state("action", "eval"), 
            0, 
            "cal", 
            "calculating results", 
            self.__get_args("base_dir", "result.k", "state.it", "name", "note:base run")
        ):
            self.__update_state(action="cal")
        
        if self.__perform_action(
                history.build_history, 
                self.__check_state("it", 0) and self.__check_state("action", "cal"), 
                0, 
                "save_history", 
                "saving historical data", 
                self.__get_args("base_dir", "it:0")
            ):
                self.__update_state(action="save_history")

    def __log_record(self, it=0, action="start", desc=""):
        if desc == "":
            content = f"Iteration {it}: Performing action <{action}>"
        else:
            content = f"Iteration {it}: Performing action <{action}> - {desc}"
        logging.info(content)
    
    def run(self):
        self._base_run()
        while not self.__check_termination():
            this_it = self.__get_state("it") + 1

            if self.__perform_action(
                initilize.run, 
                self.__check_state("it", 0, "ge") and self.__check_state("action", ["save_history", "re_cal"], "in"), 
                this_it, 
                "initialize", 
                "initializing new iteration", 
                self.__get_args("base_dir", f"it:{this_it}", "unfixed_k")
            ):
                self.__update_state(action="init")
            
            if self.__check_mode("diff") and this_it == 2:
                print('############################ tr diff finished ############################')
                break

            if self.__perform_action(
                decide.run, 
                self.__check_state("it", 0, "ge") and self.__check_state("action", "init") and self.__check_mode(["reasoning", "nohist", "nocot"], "in"), 
                this_it, 
                "decide", 
                "determining target language", 
                self.__get_args("base_dir", "num_proc", "dry_run", f"it:{this_it}", "translate.mode", "hist_top_k", "dataset_path")
            ):
                self.__update_state(action="decide")

            if self.__perform_action(
                translate.run, 
                self.__check_state("it", 0, "ge") and self.__check_state("action", ["init", "decide"], "in") and self.__check_mode("notrans", "not"), 
                this_it, 
                "translate", 
                "translating unfixed bugs", 
                self.__get_args("base_dir", "num_proc", "dry_run", f"it:{this_it}", "translate.mode", f"r_mode:{self.__get_repair_mode()}", "dataset_path", f"config_path:{self.config_path}")
            ):
                self.__update_state(action="translate")
            
            if self.__perform_action(
                re_gen.run, 
                self.__check_state("it", 0, "ge") and self.__check_state("action", ["translate", "init"], "in"), 
                this_it, 
                "re_gen", 
                "generating patched code for unfixed bugs", 
                self.__get_args("base_dir", "num_proc", "dry_run", "gen.nsample", "gen.nattempt", f"it:{this_it}", "repair.mode", "gen.temperature", "dataset_path")
            ):
                self.__update_state(action="re_gen")
            
            if self.__perform_action(
                back_translate.run, 
                self.__check_state("it", 0, "ge") and self.__check_state("action", "re_gen") and self.__check_mode("notrans", "not"), 
                this_it, 
                "back_translate", 
                "back-translating generated patched code", 
                self.__get_args("base_dir", "num_proc", "dry_run", f"it:{this_it}", "repair.mode")
            ):
                self.__update_state(action="back_translate")
            
            if self.__perform_action(
                eval_apr.run, 
                self.__check_state("it", 0, "ge") and self.__check_state("action", ["back_translate", "re_gen"], "in"), 
                this_it, 
                "re_eval", 
                "evaluating back-translated patched code", 
                self.__get_args("base_dir", f"it:{this_it}", "repair.mode")
            ):
                self.__update_state(action="re_eval")

            if self.__perform_action(
                get_result.run, 
                self.__check_state("it", 0, "ge") and self.__check_state("action", "re_eval"), 
                this_it, 
                "re_cal", 
                "calculating results", 
                self.__get_args("base_dir", "result.k", f"it:{this_it}", "name", f"note:iter {this_it}")
            ):
                self.__update_state(action="re_cal")
            
            if self.__perform_action(
                history.build_history, 
                self.__check_state("it", 0, "ge") and self.__check_state("action", "re_cal") and self.__check_mode("notrans", "not"), 
                this_it, 
                "save_history", 
                "saving historical data", 
                self.__get_args("base_dir", f"it:{this_it}")
            ):
                self.__update_state(action="save_history")
            
            self.__update_state(it=this_it)

            