import ast
import difflib
import subprocess
# import tiktoken
import transformers

from Dataset.validate_defects4j import validate_one_patch

# Initialize the deepseek tokenizer for offline token counting
try:
    chat_tokenizer_dir = "/root/deepseek_v3_tokenizer/"
    deepseek_tokenizer = transformers.AutoTokenizer.from_pretrained(
        chat_tokenizer_dir, trust_remote_code=True
    )
except Exception as e:
    print(f"Warning: Could not load deepseek tokenizer: {e}")
    deepseek_tokenizer = None

graph_based = ["breadth_first_search",
               "depth_first_search",
               "detect_cycle",
               "minimum_spanning_tree",
               "reverse_linked_list",
               "shortest_path_length",
               "shortest_path_lengths",
               "shortest_paths",
               "topological_ordering",
               "wrap" # remove wrap since its test case is too long
               ]


def simple_parse(gen_body, header, lang="python"):
    body = ""
    if lang == "python":
        for l in gen_body.splitlines():
            if l.strip() == "":
                continue
            if len(l.lstrip()) == len(l):
                break
            body += l + "\n"
    else:
        stack = ["{"]
        for l in gen_body.splitlines():
            x = l.count("{")
            for index in range(x):
                stack.append("{")
            x = l.count("}")
            for index in range(x):
                stack.pop()
            if len(stack) == 0:
                body += "}"
                break
            body += l + "\n"

    return header + "\n" + body.rstrip(), body.rstrip()


def num_tokens_from_messages_offline(messages, model="deepseek-chat"):
    """Returns the number of tokens used by a list of messages using offline deepseek tokenizer."""
    if deepseek_tokenizer is None:
        raise RuntimeError("Deepseek tokenizer not available")
    
    num_tokens = 0
    for message in messages:
        num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
        for key, value in message.items():
            num_tokens += len(deepseek_tokenizer.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    
    return num_tokens
    


def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    if model == "gpt-3.5-turbo-0301":  # note: future models may deviate from this
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens
    else:
        raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}. See 
        https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to 
        tokens.""")


def get_initial_failing_tests(args, bug_id):
    bug = bug_id.split(".java")[0]
    project, bug_num = bug.split("-")[0], bug.split("-")[1]
    run_code = subprocess.run("defects4j info -p {} -b {}".format(project, bug_num), shell=True,
                               capture_output=True,
                               encoding="utf-8",
                               text=True)
    print(run_code.stdout)

    outputs = run_code.stdout.split("--------------------------------------------------------------------------------")

    for o in outputs:
        if "Root cause in triggering tests:" in o:
            return o.split("Root cause in triggering tests:")[-1].strip()

    assert False
    # TODO: quixbugs


def build_values(values):
    str_builder = ""
    for v in values:
        str_builder += "{}, ".format(v)
    str_builder = str_builder[:-2]
    return str_builder


def simple_chatgpt_parse(gen_body, lang="python"):
    # first check if its a code block
    if "```" in gen_body:
        func = gen_body.split("```")[1]
        func = "\n".join(func.split("\n")[1:])
        # basically saves previous history up until the last
        pre_history = "```".join(gen_body.split("```")[:2]) + "```"
    else:
        func, pre_history = "", ""
    return func, pre_history


def complex_chatgpt_parse(gen_body, suffix, prefix):
    if "```" in gen_body:
        func = gen_body.split("```")[1]
        func = "\n".join(func.split("\n")[1:]).strip()
        strip_suffix = "".join(suffix.split())
        strip_prefix = "".join(prefix.split())

        # check if some suffix is overlapped
        index, found = 2, False
        while index <= len(func):
            if strip_suffix.startswith("".join(func[-index:].split())):
                found = True
                break
            index += 1

        if found and not len("".join(func[-index:].split()))*"}" == "".join(func[-index:].split()):
            func = func[:len(func) - index].strip()
        # check if some prefix is overlapped
        index, found = 1, False
        while index <= len(func):
            if strip_prefix.endswith("".join(func[:index].split())):
                found = True
                break
            index += 1
        if found and index != 1:
            func = func[index:].strip()
        # basically saves previous history up until the last
        pre_history_list = gen_body.split("```")[:2]
        # revisionist history :p
        pre_history_list[1] = func
        pre_history = "```\n".join(pre_history_list) + "\n```"
    else:
        func, pre_history = "", ""
    return func.strip(), pre_history


def complex_chatgpt_localize_parse(gen_body):
    if "```" in gen_body:
        func = gen_body.split("```")[1]
        func = "\n".join(func.split("\n")[1:]).strip()
        # basically saves previous history up until the last
        pre_history_list = gen_body.split("```")[:2]
        # revisionist history :p
        pre_history_list[1] = func
        pre_history = "```\n".join(pre_history_list) + "\n```"
    else:
        func, pre_history = "", ""
    return func.strip(), pre_history


def write_file(args, folder, patch, file_name, bug, skip_val=True, lang="python", reset=False):
    with open(folder + "/" + file_name, "w") as f:
        f.write(patch)

    if skip_val:
        return False, "Not Evaluated"
    message = "Not needed"
    if lang == "python":
        print("cd ../QuixBugs; python python_tester.py --bug {} --file {}/{} --add_pf"
                                   .format(bug, folder, file_name))
        exit_code = subprocess.run("cd ../QuixBugs; python python_tester.py --bug {} --file {}/{} --add_pf"
                                   .format(bug, folder, file_name), shell=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        valid = exit_code.returncode == 0
        with open("../QuixBugs/error.txt", "r") as f:
            s = f.readlines()
        message = ""
        if bug in graph_based:
            pass
        else:
            try:
                message = (s[0].strip(), s[1].strip(), s[2].strip())
            except:
                pass
    else:
        if "defects4j" in args.dataset:
            valid, message = validate_one_patch(folder="../Dataset/", patch=patch, bug_id=bug, reset=reset,
                                                tmp_prefix=args.tmp_prefix)
        else:
            print("cd ../QuixBugs; python java_tester.py --bug {} --file {}/{} --add_pf"
                                       .format(bug, folder, file_name))
            exit_code = subprocess.run("cd ../QuixBugs; python java_tester.py --bug {} --file {}/{} --add_pf"
                                       .format(bug, folder, file_name), shell=True,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            valid = exit_code.returncode == 0
            with open("../QuixBugs/error.txt", "r") as f:
                s = f.readlines()
            message = ""
            if bug in graph_based:
                pass
            else:
                try:
                    message = (s[0].strip(), s[1].strip(), s[2].strip())
                except:
                    pass

    return valid, message


def build_error_message_based_chatgpt_response_message(args, message, bug_info, hunk=False, function=False):

    str_builder = "\n\nThe fixed version is still not correct.\n"
    if "defects4j" in args.dataset:
        error_message, test_method_name, failing_line = message[0], message[1], message[2]
        if error_message == "SyntaxError":
            if hunk:
                str_builder += "After adding the suggested hunk the function has syntax error"
            elif function:
                str_builder += "The suggested function has syntax error"
            else:
                str_builder += "After adding the suggested line the function has syntax error"

        elif "[javac]" in error_message or "[exec]" in error_message: # todo check exec
            str_builder += "code has the following compilation error: [javac] " + ":".join(error_message.split(":")[1:])
        else:
            if bug_info['failing_tests'][0]['test_method_name'].strip() != test_method_name.strip() or \
                    bug_info['failing_tests'][0]['failing_line'].strip() != failing_line.strip() or \
                    bug_info['failing_tests'][0]['failure_message'].strip() != error_message.strip():
                str_builder += "The code fails on this test: `{}()`".format(test_method_name.strip()) + \
                               "\non this test line: `{}`".format(failing_line.strip()) + \
                               "\nwith the following test error: {}".format(error_message.strip())
            else:
                str_builder += "It still does not fix the original test failure"
    else:

        if message == "":
            str_builder += "It still does not fix the original test failure"
        else:
            input_values, output, correct_output = message[0], message[1], message[2]
            input_values = ast.literal_eval(input_values)

            if input_values == bug_info['failing_tests']['input_values'] and output == bug_info['failing_tests']['output_values']:
                str_builder += "It still does not fix the original test failure"
            else:
                if args.lang == "python":
                    str_builder += bug_info['function_header'] + "("
                else:
                    str_builder += bug_info['function_header'].split("(")[0].split()[-1] + "("
                for value in input_values:
                    str_builder += "{}, ".format(value)
                if args.lang == "python":
                    if "<class '" in output and "Error" in output:
                        str_builder = str_builder[:-2] + ") has " + output.split("<class '")[-1].split("'>")[0]
                    elif "<class '" in output and "Exception" in output:
                        str_builder = str_builder[:-2] + ") has " + output.split("Exception('")[-1].split("')")[
                            0] + " Exception"
                    else:
                        str_builder = str_builder[:-2] + ") returns " + output + " but it should return " + correct_output
                else:
                    if "TimeoutExpired" in output:
                        str_builder = str_builder[:-2] + ") timed out "
                    elif "java.lang." in output:
                        str_builder = str_builder[:-2] + ") gives "
                        for s in output.split():
                            if s.startswith("java.lang."):
                                str_builder += s.split(":")[0]
                                break
                    elif output == "None":
                        str_builder = str_builder[:-2] + ") cannot compile "
                    else:
                        str_builder = str_builder[:-2] + ") returns " + output + " but it should return " + correct_output

    print(str_builder)
    if hunk:
        str_builder += "\n\nPlease provide the correct code hunk at the infill location.\n"
    elif function:
        str_builder += "\n\nPlease provide the correct function.\n"
    else:
        str_builder += "\n\nPlease provide the correct line at the infill location.\n"

    return str_builder

