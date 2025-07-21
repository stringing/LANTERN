import openai
import os
import signal
import time

from Generation.prompt import INIT_CHATGPT_INFILL_PROMPT, INIT_CHATGPT_CORRECT_RESPONSE, \
    INIT_CHATGPT_INFILL_FAILING_TEST_LINE, INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE, \
    INIT_CHATGPT_CORRECT_HUNK_RESPONSE, INIT_CHATGPT_INFILL_FUNCTION_FAILING_TEST_LINE, \
    INIT_CHATGPT_CORRECT_FUNCTION_RESPONSE, INIT_CHATGPT_INFILL_FUNCTION_FAILING_QUIXBUGS, \
    INIT_CHATGPT_INFILL_LINE_FAILING_TEST_LINE_QUIXBUGS, INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE_QUIXBUGS
from Generation.prompt import CHATGPT_LOCALIZE_PROMPT, CHATGPT_LOCALIZE_RESPONSE
from Generation.util.util import get_initial_failing_tests, build_values


def create_openai_config(prompt,
                         engine_name="code-davinci-002",
                         stop="# Provide a fix for the buggy function",
                         max_tokens=3000,
                         top_p=0.95,
                         temperature=1):
    return {
        "engine": engine_name,
        "prompt": prompt,
        "max_tokens": max_tokens,
        "top_p": top_p,
        "temperature": temperature,
        "logprobs": 1,
        "stop": stop
    }


def create_chatgpt_config(prev: dict, message: str, max_tokens: int, bug_id, bugs, few_shot: int = 0,
                          temperature: float = 1, # default most diverse temperature
                          system_message: str = "You are an Automated Program Repair tool.",
                          localize: bool = False,
                          hunk: bool = False,
                          function: bool =False,
                          dataset: str = "",
                          model: str = "deepseek-chat"):
    if prev == {}:
        if few_shot > 0:
            config = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system_message}
                ]
            }
            bug_project = bug_id.split("-")[0]
            examples = []
            for bug, v in bugs.items():
                if (bug.startswith(bug_project) and bug != bug_id) or ("quixbugs" in dataset and bug != bug_id):
                    x = v
                    x['name'] = bug
                    examples.append(x)
            examples = sorted(examples, key=lambda d: len(d['buggy']))
            for e in examples[:few_shot]:
                if localize:
                    config["messages"].append({"role": "user", "content": CHATGPT_LOCALIZE_PROMPT.format(
                        buggy_code=e['buggy'],
                        root_cause=get_initial_failing_tests(None, e['name']))})
                    config["messages"].append({"role": "assistant", "content": CHATGPT_LOCALIZE_RESPONSE.format(
                        buggy_line=e['buggy_line']
                    ).strip()})
                elif hunk:
                    if "quixbugs" in dataset:
                        config["messages"].append(
                            {"role": "user", "content": INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE_QUIXBUGS.format(
                                buggy_code=(e['prefix'] + "\n" + ">>> [ INFILL ] <<<" + "\n" + e['suffix']),
                                buggy_hunk=e['buggy_line'],
                                function_header=(e['function_header']),
                                values=build_values(e['failing_tests']['input_values']),
                                return_val=e['failing_tests']['output_values'])})
                        config["messages"].append(
                            {"role": "assistant", "content": INIT_CHATGPT_CORRECT_RESPONSE.format(
                                correct_hunk=e['correct_line']
                            ).strip()})
                    else:
                        config["messages"].append({"role": "user", "content": INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE.format(
                            buggy_code=(e['prefix'] + "\n" + ">>> [ INFILL ] <<<" + "\n" + e['suffix']),
                            buggy_hunk=e['buggy_line'],
                            failing_test=e['failing_tests'][0]['test_method_name'],
                            error_message=e['failing_tests'][0]['failure_message'].strip(),
                            failing_line=e['failing_tests'][0]['failing_line'].strip()).strip()})
                        config["messages"].append({"role": "assistant", "content": INIT_CHATGPT_CORRECT_HUNK_RESPONSE.format(
                            correct_hunk=e['correct_line']
                        ).strip()})
                elif function:
                    if "quixbugs" in dataset:
                        config["messages"].append(
                            {"role": "user", "content": INIT_CHATGPT_INFILL_FUNCTION_FAILING_QUIXBUGS.format(
                                buggy_code=(e['buggy']),
                                function_header=(e['function_header']),
                                values=build_values(e['failing_tests']['input_values']),
                                return_val=e['failing_tests']['output_values'])})
                        config["messages"].append(
                            {"role": "assistant", "content": INIT_CHATGPT_CORRECT_FUNCTION_RESPONSE.format(
                                correct_hunk=e['fix']
                            ).strip()})
                    else:
                        config["messages"].append(
                            {"role": "user", "content": INIT_CHATGPT_INFILL_FUNCTION_FAILING_TEST_LINE.format(
                                buggy_code=(e['buggy']),
                                failing_test=e['failing_tests'][0]['test_method_name'],
                                error_message=e['failing_tests'][0]['failure_message'].strip(),
                                failing_line=e['failing_tests'][0]['failing_line'].strip()).strip()})
                        config["messages"].append(
                            {"role": "assistant", "content": INIT_CHATGPT_CORRECT_FUNCTION_RESPONSE.format(
                                correct_hunk=e['fix']
                            ).strip()})
                else:
                    if "quixbugs" in dataset:
                        config["messages"].append(
                            {"role": "user", "content": INIT_CHATGPT_INFILL_LINE_FAILING_TEST_LINE_QUIXBUGS.format(
                                buggy_code=(e['prefix'] + "\n" + ">>> [ INFILL ] <<<" + "\n" + e['suffix']),
                                buggy_hunk=e['buggy_line'],
                                function_header=(e['function_header']),
                                values=build_values(e['failing_tests']['input_values']),
                                return_val=e['failing_tests']['output_values'])})
                        config["messages"].append(
                            {"role": "assistant", "content": INIT_CHATGPT_CORRECT_RESPONSE.format(
                                correct_hunk=e['correct_line']
                            ).strip()})
                    else:
                        config["messages"].append({"role": "user", "content": INIT_CHATGPT_INFILL_FAILING_TEST_LINE.format(
                            buggy_code=(e['prefix'] + "\n" + ">>> [ INFILL ] <<<" + "\n" + e['suffix']),
                            buggy_hunk=e['buggy_line'],
                            failing_test=e['failing_tests'][0]['test_method_name'],
                            error_message=e['failing_tests'][0]['failure_message'].strip(),
                            failing_line=e['failing_tests'][0]['failing_line'].strip()).strip()})
                        config["messages"].append({"role": "assistant", "content": INIT_CHATGPT_CORRECT_RESPONSE.format(
                            correct_hunk=e['correct_line']
                        ).strip()})
            config["messages"].append({"role": "user", "content": message.strip()})
            return config
        else:
            return {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": message.strip()}
                ]
            }
    else:
        return prev


def handler(signum, frame):
    raise Exception("end of time")


def request_chatgpt_engine(config):
    ret = None
    while ret is None:
        try:
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(100)
            ret = openai.ChatCompletion.create(**config)
            signal.alarm(0)  # cancel alarm
        except openai.error.InvalidRequestError as e:
            print(e)
            signal.alarm(0)  # cancel alarm
        except openai.error.RateLimitError as e:
            print("Rate limit exceeded. Waiting...")
            print(e)
            signal.alarm(0)  # cancel alarm
            time.sleep(5)  # wait for a minute
        except openai.error.APIConnectionError as e:
            print("API connection error. Waiting...")
            signal.alarm(0)  # cancel alarm
            time.sleep(5)  # wait for a minute
        except Exception as e:
            print(e)
            print("Unknown error. Waiting...")
            signal.alarm(0)  # cancel alarm
            time.sleep(1)  # wait for a minute
    return ret


# Handles requests to OpenAI API
def request_engine(config):
    ret = None
    while ret is None:
        try:
            ret = openai.Completion.create(**config)
        except openai.error.InvalidRequestError as e:
            print(e)
            if "Please reduce your prompt" in str(e):
                config['max_tokens'] = config['max_tokens'] - 200
                if config['max_tokens'] < 100:
                    return None
            else:
                return None
        except openai.error.RateLimitError as e:
            print("Rate limit exceeded. Waiting...")
            time.sleep(60)  # wait for a minute
        except openai.error.APIConnectionError as e:
            print("API connection error. Waiting...")
            time.sleep(5)  # wait for a minute
        except:
            print("Unknown error. Waiting...")
            time.sleep(5)  # wait for a minute
    return ret
