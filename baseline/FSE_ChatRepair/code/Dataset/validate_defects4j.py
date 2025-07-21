import json
import time
import javalang
import subprocess
import re
import os
import signal
import argparse

from Dataset.dataset import get_unified_diff


def run_d4j_test(source, testmethods, bug_id, project, bug):
    bugg = False
    compile_fail = False
    timed_out = False
    entire_bugg = False
    error_string = ""

    try:
        tokens = javalang.tokenizer.tokenize(source)
        parser = javalang.parser.Parser(tokens)
        parser.parse()
    except:
        print("Syntax Error")
        return compile_fail, timed_out, bugg, entire_bugg, True, "SyntaxError"

    for t in testmethods:
        cmd = 'defects4j test -w %s/ -t %s' % (('/tmp/' + bug_id), t.strip())
        Returncode = ""
        error_file = open("stderr.txt", "wb")
        child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=error_file, bufsize=-1,
                                 start_new_session=True)
        while_begin = time.time()
        while True:
            Flag = child.poll()
            if Flag == 0:
                Returncode = child.stdout.readlines()  # child.stdout.read()
                print(b"".join(Returncode).decode('utf-8'))
                error_file.close()
                break
            elif Flag != 0 and Flag is not None:
                compile_fail = True
                error_file.close()
                with open("stderr.txt", "rb") as f:
                    r = f.readlines()
                for index, line in enumerate(r):
                    if re.search(':\serror:\s', line.decode('utf-8')):
                        error_string = line.decode('utf-8').strip()
                        if "cannot find symbol" in error_string:
                            error_string += " (" + r[index + 3].decode('utf-8').split("symbol:")[-1].strip() + ")"
                        break
                print("Error")
                print(error_string)
                if error_string == "":
                    subprocess.run('rm -rf ' + '/tmp/' + bug_id, shell=True)
                    subprocess.run("defects4j checkout -p %s -v %s -w %s" % (project, bug + 'b', ('/tmp/' + bug_id)),
                                   shell=True)

                break
            elif time.time() - while_begin > 15:
                error_file.close()
                os.killpg(os.getpgid(child.pid), signal.SIGTERM)
                timed_out = True
                error_string = "TimeOutError"
                break
            else:
                time.sleep(0.001)
        log = Returncode
        if len(log) > 0 and log[-1].decode('utf-8') == "Failing tests: 0\n":
            continue
        else:
            bugg = True
            break

    # Then we check if it passes all the tests, include the previously okay tests
    if not bugg:
        print('So you pass the basic tests, Check if it passes all the test, include the previously passing tests')
        cmd = 'defects4j test -w %s/' % ('/tmp/' + bug_id)
        Returncode = ""
        child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1,
                                 start_new_session=True)
        while_begin = time.time()
        while True:
            Flag = child.poll()
            if Flag == 0:
                Returncode = child.stdout.readlines()  # child.stdout.read()
                break
            elif Flag != 0 and Flag is not None:
                bugg = True
                break
            elif time.time() - while_begin > 180:
                os.killpg(os.getpgid(child.pid), signal.SIGTERM)
                bugg = True
                error_string = "TimeOutError"
                break
            else:
                time.sleep(0.01)
        log = Returncode
        if len(log) > 0 and log[-1].decode('utf-8') == "Failing tests: 0\n":
            print('success')
        else:
            entire_bugg = True

    return compile_fail, timed_out, bugg, entire_bugg, False, error_string


REAL_SOURCE = []


# def parse_source(source):
#     method_dict = {}
#     tree = javalang.parse.parse(source)
#     for path, node in tree:
#         if type(node) == javalang.tree.MethodDeclaration or type(node) == javalang.tree.ConstructorDeclaration:
#             method_dict[node.name] = {'start': node.start_position.line, 'end': node.end_position.line}
#     return method_dict

def parse_source(source):
    method_dict = {}
    lines = source.splitlines()
    
    try:
        tree = javalang.parse.parse(source)
    except Exception as e:
        print(f"Failed to parse source: {e}")
        return method_dict
    
    # Get all method and constructor declarations with their positions
    methods = []
    for path, node in tree:
        if isinstance(node, (javalang.tree.MethodDeclaration, javalang.tree.ConstructorDeclaration)):
            if hasattr(node, 'position') and node.position:
                methods.append((node.name, node.position.line))
    
    # Sort methods by line number
    methods.sort(key=lambda x: x[1])
    
    # Calculate end lines
    for i, (method_name, start_line) in enumerate(methods):
        if i < len(methods) - 1:
            # End is before the next method starts
            next_start = methods[i + 1][1]
            end_line = find_method_end_before_line(lines, start_line, next_start)
        else:
            # Last method, find end by brace counting
            end_line = find_method_end_line(lines, start_line, method_name)
        
        method_dict[method_name] = {
            'start': start_line,
            'end': end_line
        }
    
    return method_dict

def find_method_end_line(lines, start_line, method_name):
    """
    Find the end line of a method by counting braces from the start line.
    """
    brace_count = 0
    in_method = False
    
    for i in range(start_line - 1, len(lines)):
        line = lines[i]
        
        # Start counting braces after we find the opening brace of the method
        if '{' in line:
            in_method = True
            brace_count += line.count('{')
        
        if in_method:
            brace_count -= line.count('}')
            
            # When brace count reaches 0, we've found the end of the method
            if brace_count == 0:
                return i + 1  # +1 because line numbers are 1-indexed
    
    # Fallback: return the last line if we can't find the end
    return len(lines)

def find_method_end_before_line(lines, start_line, before_line):
    """Find method end by counting braces, but stop before a certain line."""
    brace_count = 0
    in_method = False
    
    for i in range(start_line - 1, min(before_line - 1, len(lines))):
        line = lines[i]
        
        if '{' in line:
            in_method = True
            brace_count += line.count('{')
        
        if in_method:
            brace_count -= line.count('}')
            
            if brace_count == 0:
                return i + 1
    
    return before_line - 1

def grab_failing_testcode(bug_id, file_name, test_method_name, line_number, tmp_bug_id):
    test_dir = os.popen("defects4j export -p dir.src.tests -w /tmp/" + tmp_bug_id).readlines()[-1].strip()

    if not os.path.isfile("/tmp/" + tmp_bug_id + "/" + test_dir + "/" + file_name + ".java"):
        return "", ""
    try:
        with open("/tmp/" + tmp_bug_id + "/" + test_dir + "/" + file_name + ".java", "r") as f:
            source = f.read()
    except:
        with open("/tmp/" + tmp_bug_id + "/" + test_dir + "/" + file_name + ".java", "r", encoding='ISO-8859-1') as f:
            source = f.read()
    # print(source)
    method_dict = parse_source(source)
    lines = source.splitlines()

    if line_number == "":
        return "\n".join(lines[method_dict[test_method_name]['start'] - 1:method_dict[test_method_name]['end']]), ""
    else:
        return "\n".join(lines[method_dict[test_method_name]['start'] - 1:method_dict[test_method_name]['end']]), \
               lines[int(line_number) - 1]


def validate_one_patch(folder, patch, bug_id, dataset_name="defects4j_1.2_full", tmp_prefix="test", reset=False):
    global REAL_SOURCE
    if dataset_name == "defects4j_1.2_full":
        with open(folder + "Defects4j" + "/single_function_repair.json", "r") as f:
            bug_dict = json.load(f)

    bug, project = bug_id.split("-")[1], bug_id.split("-")[0]
    start = bug_dict[bug_id]['start']
    end = bug_dict[bug_id]['end']
    with open(folder + "Defects4j/location" + "/{}.buggy.lines".format(bug_id), "r") as f:
        locs = f.read()
    loc = set([x.split("#")[0] for x in locs.splitlines()])  # should only be one
    loc = loc.pop()
    tmp_bug_id = tmp_prefix + project + bug

    if reset:  # check out project again
        subprocess.run('rm -rf ' + '/tmp/' + tmp_prefix + "*", shell=True)  # clean up
        subprocess.run('rm -rf ' + '/tmp/' + tmp_bug_id, shell=True)
        subprocess.run("defects4j checkout -p %s -v %s -w %s" % (project, bug + 'b', ('/tmp/' + tmp_bug_id)),
                       shell=True)

    testmethods = os.popen('defects4j export -w %s -p tests.trigger' % ('/tmp/' + tmp_bug_id)).readlines()
    source_dir = os.popen("defects4j export -p dir.src.classes -w /tmp/" + tmp_bug_id).readlines()[-1].strip()

    if reset:
        try:
            with open("/tmp/" + tmp_bug_id + "/" + source_dir + "/" + loc, 'r') as f:
                REAL_SOURCE = f.read().splitlines()
        except:
            with open("/tmp/" + tmp_bug_id + "/" + source_dir + "/" + loc, 'r', encoding='ISO-8859-1') as f:
                REAL_SOURCE = f.read().splitlines()

    source = REAL_SOURCE
    source = "\n".join(source[:start - 1] + patch.splitlines() + source[end:])

    try:
        with open("/tmp/" + tmp_bug_id + "/" + source_dir + "/" + loc, 'w') as f:
            f.write(source)
        subprocess.run("touch -d '12 December' " + "/tmp/" + tmp_bug_id + "/" + source_dir + "/" + loc,
                       shell=True)
    except:
        with open("/tmp/" + tmp_bug_id + "/" + source_dir + "/" + loc, 'w', encoding='ISO-8859-1') as f:
            f.write(source)
        subprocess.run("touch -d '12 December' " + "/tmp/" + tmp_bug_id + "/" + source_dir + "/" + loc,
                       shell=True)

    compile_fail, timed_out, bugg, entire_bugg, syntax_error, error_string = run_d4j_test(source,
                                                                                          testmethods,
                                                                                          tmp_bug_id,
                                                                                          project, bug)
    if not compile_fail and not timed_out and not bugg and not entire_bugg and not syntax_error:
        print("{} has valid patch".format(bug_id))
        return True, ("valid", "", "")
    else:
        test_method_name, failing_line = "", ""
        if (bugg or entire_bugg) and not compile_fail:
            if not os.path.isfile('/tmp/' + tmp_bug_id + '/failing_tests'):
                error_string = ""
            else:
                try:
                    with open('/tmp/' + tmp_bug_id + '/failing_tests', "r") as f:
                        text = f.read()
                except:
                    with open('/tmp/' + tmp_bug_id + '/failing_tests', "r", encoding='ISO-8859-1') as f:
                        text = f.read()
                if len(text.split("--- ")) >= 2:
                    # error_string = text[1]
                    x = text.split("--- ")[1]  # just grab first one
                    test_name = x.splitlines()[0]
                    file_name = test_name.split("::")[0].replace(".", "/")
                    if len(test_name.split("::")) == 1:
                        error_string = ""
                    else:
                        test_method_name = test_name.split("::")[1]
                        line_number = ""
                        error_string = x.splitlines()[1]
                        for line in x.splitlines()[1:]:
                            if test_method_name in line:
                                line_number = line.split(":")[-1].split(")")[0]
                                file_name = line.split("." + test_method_name)[0].split("at ")[1].replace(".", "/")
                                break
                        print(file_name, test_method_name, line_number)
                        failing_function, failing_line = grab_failing_testcode(bug_id.split(".java")[0], file_name,
                                                                               test_method_name, line_number, tmp_bug_id)
                else:
                    error_string = ""
        print("{} has invalid patch".format(bug_id))
        return False, (error_string, test_method_name, failing_line)


# used to mass validate a bunch of generated files
def validate_all_patches(folder, j_file, dataset_name, tmp_prefix="test"):
    if dataset_name == "defects4j_1.2_full":
        with open("Defects4j" + "/single_function_repair.json", "r") as f:
            bug_dict = json.load(f)

    with open(folder + "/" + j_file, "r") as f:
        repair_dict = json.load(f)

    plausible, total = 0, 0
    seen_bugs = {}

    bugs_with_plausible_patch = []

    for s, patches in repair_dict.items():
        bug_id = s.split(".java")[0]
        bug = bug_id.split("-")[1]
        project = bug_id.split("-")[0]
        start = bug_dict[bug_id]['start']
        end = bug_dict[bug_id]['end']
        with open("Defects4j/location" + "/{}.buggy.lines".format(bug_id), "r") as f:
            locs = f.read()
        loc = set([x.split("#")[0] for x in locs.splitlines()])  # should only be one
        loc = loc.pop()

        tmp_bug_id = tmp_prefix + project + bug

        if tmp_bug_id not in seen_bugs:
            for sb in seen_bugs.keys():
                subprocess.run('rm -rf ' + '/tmp/' + sb, shell=True)
            seen_bugs[tmp_bug_id] = 1
            subprocess.run('rm -rf ' + '/tmp/' + tmp_bug_id, shell=True)
            subprocess.run("defects4j checkout -p %s -v %s -w %s" % (project, bug + 'b', ('/tmp/' + tmp_bug_id)),
                           shell=True)
            with open(folder + "/" + j_file, "w") as f:
                json.dump(repair_dict, f)

        testmethods = os.popen('defects4j export -w %s -p tests.trigger' % ('/tmp/' + tmp_bug_id)).readlines()
        source_dir = os.popen("defects4j export -p dir.src.classes -w /tmp/" + tmp_bug_id).readlines()[-1].strip()

        diff_set = set()

        for index, generation in enumerate(patches):
            patch = generation['patch']
            lines = bug_dict[bug_id]['fix'].splitlines()
            leading_white_space = len(lines[0]) - len(lines[0].lstrip())
            fix = "\n".join([line[leading_white_space:] for line in lines])
            diff = get_unified_diff(fix, patch)
            if diff in diff_set:
                continue
            diff_set.add(diff)
            print(diff)

            if seen_bugs[tmp_bug_id] == 1:
                try:
                    with open("/tmp/" + tmp_bug_id + "/" + source_dir + "/" + loc, 'r') as f:
                        source = f.read().splitlines()
                except:
                    with open("/tmp/" + tmp_bug_id + "/" + source_dir + "/" + loc, 'r', encoding='ISO-8859-1') as f:
                        source = f.read().splitlines()
                seen_bugs[tmp_bug_id] = source
            else:
                source = seen_bugs[tmp_bug_id]
            source = "\n".join(source[:start - 1] + patch.splitlines() + source[end + 1:])

            try:
                with open("/tmp/" + tmp_bug_id + "/" + source_dir + "/" + loc, 'w') as f:
                    f.write(source)
                subprocess.run("touch -d '12 December' " + "/tmp/" + tmp_bug_id + "/" + source_dir + "/" + loc,
                               shell=True)
            except:
                with open("/tmp/" + tmp_bug_id + "/" + source_dir + "/" + loc, 'w', encoding='ISO-8859-1') as f:
                    f.write(source)
                subprocess.run("touch -d '12 December' " + "/tmp/" + tmp_bug_id + "/" + source_dir + "/" + loc,
                               shell=True)

            compile_fail, timed_out, bugg, entire_bugg, syntax_error, error_string = run_d4j_test(source,
                                                                                                  testmethods,
                                                                                                  tmp_bug_id,
                                                                                                  project, bug)
            if not compile_fail and not timed_out and not bugg and not entire_bugg and not syntax_error:
                plausible += 1
                repair_dict[s][index]['valid'] = True
                print('success')
                print("{} has valid patch: {}".format(bug_id, index))
                bugs_with_plausible_patch.append(bug_id)
            else:
                repair_dict[s][index]['error'] = error_string
                print("{} has invalid patch: {}".format(bug_id, index))

            total += 1

    print("{}/{} are plausible".format(plausible, total))

    with open(folder + "/" + j_file, "w") as f:
        json.dump(repair_dict, f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=str)
    parser.add_argument("--jfile", type=str, default="lm_repair.json")
    parser.add_argument("--dataset_name", type=str, default=None)
    parser.add_argument("--project_name", type=str, default=None)
    parser.add_argument("--bug_id_g", type=str, default=None)
    parser.add_argument("--tmp", type=str, default="test")  # facilitate parallel runs
    args = parser.parse_args()

    validate_all_patches(args.folder, args.jfile, args.dataset_name, tmp_prefix=args.tmp)


if __name__ == "__main__":
    main()
