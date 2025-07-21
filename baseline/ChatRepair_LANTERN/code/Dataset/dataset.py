import glob
import json
import os

from difflib import unified_diff

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


def get_unified_diff(source, mutant):
    output = ""
    for line in unified_diff(source.split('\n'), mutant.split('\n'), lineterm=''):
        output += line + "\n"
    return output


def check_d4j_2(bug, d4j_2=False):
    is_d4j_2 = True
    if 'Time' in bug or 'Math' in bug or 'Mockito' in bug or 'Chart' in bug or 'Lang' in bug:
        is_d4j_2 = False
    elif 'Closure' in bug:
        if int(bug.split(".java")[0].split("-")[-1]) <= 133:
            is_d4j_2 = False

    return is_d4j_2 == d4j_2


def remove_suffix(input_string, suffix):
    if suffix and input_string.endswith(suffix):
        return input_string[:-len(suffix)]
    return input_string


def remove_prefix(input_string, prefix):
    if prefix and input_string.startswith(prefix):
        return input_string[len(prefix):]
    return input_string


def parse_defects4j_12(folder, single_hunk=False, single_line=False):
    if single_hunk:
        file = "single_function_single_hunk_repair"
    elif single_line:
        file = "single_function_single_line_repair"
    else:
        file = "single_function_repair"
    with open(folder + "Defects4j/{}.json".format("failing_test_info"), "r") as f:
        failing_test_info = json.load(f)
    with open(folder + "Defects4j/{}.json".format(file), "r") as f:
        result = json.load(f)
    cleaned_result = {}
    for k, v in result.items():
        lines = v['buggy'].splitlines()
        leading_white_space = len(lines[0]) - len(lines[0].lstrip())
        cleaned_result[k + ".java"] = v
        cleaned_result[k + ".java"]["buggy"] = "\n".join([line[leading_white_space:] for line in lines])
        lines = v['fix'].splitlines()
        leading_white_space = len(lines[0]) - len(lines[0].lstrip())
        cleaned_result[k + ".java"]["fix"] = "\n".join([line[leading_white_space:] for line in lines])
        if k + ".java" in failing_test_info:
            cleaned_result[k + ".java"]["failing_tests"] = failing_test_info[k + ".java"]['failing_tests']
        if "prefix" in v:
            lines = v["prefix"].splitlines()
            cleaned_result[k + ".java"]["prefix"] = "\n".join([line[leading_white_space:] for line in lines])
            lines = v["suffix"].splitlines()
            cleaned_result[k + ".java"]["suffix"] = "\n".join([line[leading_white_space:] for line in lines])
            cleaned_result[k + ".java"]["buggy_line"] = remove_suffix(remove_prefix(cleaned_result[k + ".java"]["buggy"], cleaned_result[k + ".java"]["prefix"]),
                                                                      cleaned_result[k + ".java"]["suffix"]).strip()
            cleaned_result[k + ".java"]["correct_line"] = remove_suffix(
                remove_prefix(cleaned_result[k + ".java"]["fix"], cleaned_result[k + ".java"]["prefix"]),
                cleaned_result[k + ".java"]["suffix"]).strip()
    result = {k: v for k, v in cleaned_result.items() if check_d4j_2(k, False)}

    return result


def parse_defects4j_2(folder):
    file = "single_function_single_line_repair"
    with open(folder + "Defects4j/{}.json".format("failing_test_info"), "r") as f:
        failing_test_info = json.load(f)
    with open(folder + "Defects4j/{}.json".format(file), "r") as f:
        result = json.load(f)
    cleaned_result = {}
    for k, v in result.items():
        lines = v['buggy'].splitlines()
        leading_white_space = len(lines[0]) - len(lines[0].lstrip())
        cleaned_result[k + ".java"] = v
        cleaned_result[k + ".java"]["buggy"] = "\n".join([line[leading_white_space:] for line in lines])
        lines = v['fix'].splitlines()
        leading_white_space = len(lines[0]) - len(lines[0].lstrip())
        cleaned_result[k + ".java"]["fix"] = "\n".join([line[leading_white_space:] for line in lines])
        if k + ".java" in failing_test_info:
            cleaned_result[k + ".java"]["failing_tests"] = failing_test_info[k + ".java"]['failing_tests']
        if "prefix" in v:
            lines = v["prefix"].splitlines()
            cleaned_result[k + ".java"]["prefix"] = "\n".join([line[leading_white_space:] for line in lines])
            lines = v["suffix"].splitlines()
            cleaned_result[k + ".java"]["suffix"] = "\n".join([line[leading_white_space:] for line in lines])
            cleaned_result[k + ".java"]["buggy_line"] = remove_suffix(remove_prefix(cleaned_result[k + ".java"]["buggy"], cleaned_result[k + ".java"]["prefix"]),
                                                                      cleaned_result[k + ".java"]["suffix"]).strip()
            cleaned_result[k + ".java"]["correct_line"] = remove_suffix(
                remove_prefix(cleaned_result[k + ".java"]["fix"], cleaned_result[k + ".java"]["prefix"]),
                cleaned_result[k + ".java"]["suffix"]).strip()
    result = {k: v for k, v in cleaned_result.items() if check_d4j_2(k, True)}

    return result


def parse_python(folder):
    with open(folder+"QuixBugs/failing_test_info.json", "r") as f:
        tests = json.load(f)
    ret = {}
    for file in glob.glob(folder + "QuixBugs/Python/fix/*.py"):
        filename = os.path.basename(file)
        # if filename.split(".")[0] in graph_based:
        #     continue
        if "_test" in file or "node.py" in file:
            continue
        with open(file, "r") as f:
            x = f.read().strip()
        with open(folder + "QuixBugs/Python/buggy/{}".format(filename), "r") as f:
            y = f.read().strip()
        filename = filename.split(".")[0]
        ret[filename] = {'fix': x, 'buggy': y, 'function_header': y.splitlines()[0].split("def ")[-1].split("(")[0]}
        ret[filename]['failing_tests'] = tests[filename]
        diff_lines = get_unified_diff(y, x).splitlines()
        line_no = -1
        for line in diff_lines:
            if "@@" in line:
                rline = line.split(" ")[1][1:]
                line_no = int(rline.split(",")[0].split("-")[0])
            elif line_no == -1:
                continue
            if line.startswith("-"):
                ret[filename]['line_no'] = line_no - 2
                ret[filename]['line_content'] = line[1:]
                ret[filename]['type'] = 'modify'
                ret[filename]['prefix'] = "\n".join(ret[filename]['buggy'].splitlines()[:ret[filename]['line_no']])
                ret[filename]['suffix'] = "\n".join(ret[filename]['buggy'].splitlines()[ret[filename]['line_no'] + 1:])
                break
            elif line.startswith("+"):
                ret[filename]['line_no'] = line_no - 2
                ret[filename]['line_content'] = line[1:]
                ret[filename]['type'] = 'add'
                ret[filename]['prefix'] = "\n".join(ret[filename]['buggy'].splitlines()[:ret[filename]['line_no']])
                ret[filename]['suffix'] = "\n".join(ret[filename]['buggy'].splitlines()[ret[filename]['line_no']:])
                break
            line_no += 1

        ret[filename]["buggy_line"] = remove_suffix(
            remove_prefix(ret[filename]["buggy"], ret[filename]["prefix"]),
            ret[filename]["suffix"]).strip()
        ret[filename]["correct_line"] = remove_suffix(
            remove_prefix(ret[filename]["fix"], ret[filename]["prefix"]),
            ret[filename]["suffix"])
        ret[filename]["leading_whitespace"] = " " * (len(ret[filename]["correct_line"])-len(ret[filename]["correct_line"].lstrip()) -1)
        ret[filename]["correct_line"] = ret[filename]["correct_line"].strip()

    return ret


def parse_java(folder):
    with open(folder+"QuixBugs/failing_test_info_java.json", "r") as f:
        tests = json.load(f)
    ret = {}
    for file in glob.glob(folder + "QuixBugs/Java/fix/*.java"):
        filename = os.path.basename(file)
        # if filename.split(".")[0].lower() in graph_based:
        #     continue
        with open(file, "r") as f:
            x = f.read().strip()
        with open(folder + "QuixBugs/Java/buggy/{}".format(filename), "r") as f:
            y = f.read().strip()

        ret[filename.split(".")[0].lower()] = {'fix': x, 'buggy': y, 'function_header': y.splitlines()[0].split("(")[0].split()[-1]}
        ret[filename.split(".")[0].lower()]['failing_tests'] = tests[filename.split(".")[0].lower()]
        diff_lines = get_unified_diff(y, x).splitlines()
        remove, gap, add, single_hunk = False, False, False, True
        line_no = 0
        for line in diff_lines[2:]:
            if "@@" in line:
                rline = line.split(" ")[1][1:]
                line_no = int(rline.split(",")[0].split("-")[0])
            elif line.startswith("-"):
                if not remove:
                    start_line_no = line_no
                if gap:
                    single_hunk = False
                remove = True
                end_line_no = line_no
            elif line.startswith("+"):
                if not remove and not add:
                    start_line_no = line_no
                if not add:
                    end_line_no = line_no
                add = True
                if gap:
                    single_hunk = False
            else:
                if remove:
                    gap = True

            if not single_hunk:
                break
            line_no += 1

        if not single_hunk:
            print("Not single hunk bug")
        else:
            print("Single hunk bug")
            ret[filename.split(".")[0].lower()]['prefix'] = "\n".join(ret[filename.split(".")[0].lower()]['buggy'].splitlines()[:start_line_no - 2])
            ret[filename.split(".")[0].lower()]['suffix'] = "\n".join(ret[filename.split(".")[0].lower()]['buggy'].splitlines()[end_line_no - 2:])
            ret[filename.split(".")[0].lower()]["buggy_line"] = remove_suffix(
                remove_prefix(ret[filename.split(".")[0].lower()]["buggy"], ret[filename.split(".")[0].lower()]["prefix"]),
                ret[filename.split(".")[0].lower()]["suffix"]).strip()
            ret[filename.split(".")[0].lower()]["correct_line"] = remove_suffix(
                remove_prefix(ret[filename.split(".")[0].lower()]["fix"], ret[filename.split(".")[0].lower()]["prefix"]),
                ret[filename.split(".")[0].lower()]["suffix"]).strip()
            print("\n".join(diff_lines))

    return ret