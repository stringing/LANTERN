INIT_PROMPT = """
The following code is buggy.
{buggy_code}

Please provide a fixed version.
{function_header}
"""

INIT_CHATGPT_PROMPT = """
The following code is buggy.
```
{buggy_code}
```
Please provide a fixed version.
"""

INIT_CHATGPT_INFILL_PFC_PROMPT = """
The following code contains a buggy hunk that has been removed.
```
{buggy_code}
```
This was the original buggy hunk which was removed by the infill location
```
// buggy hunk
{buggy_hunk}
```
The code fails on this test: `{failing_test}()`
on this test line: `{failing_line}`
with the following test error: {error_message}

It can be fixed by these hunks
1.
```
{fix_hunk}
```
"""

PFC_SUFFIX_PROMPT = "Please generate an alternative fix hunk at the infill location."

PFC_ADD_PROMPT = """
{num}.
```
{fix_hunk}
```
"""

INIT_CHATGPT_INFILL_LINE_PFC_PROMPT = """
The following code contains a buggy line that has been removed.
```
{buggy_code}
```
This was the original buggy line which was removed by the infill location
```
// buggy line
{buggy_hunk}
```
The code fails on this test: `{failing_test}()`
on this test line: `{failing_line}`
with the following test error: {error_message}

It can be fixed by these hunk
1.
```
{fix_hunk}
```
"""

PFC_SUFFIX_LINE_PROMPT = "Please generate an alternative fix line at the infill location."

INIT_CHATGPT_FUNCTION_PFC_PROMPT = """
The following code contains a bug.
```
{buggy_code}
```
The code fails on this test: `{failing_test}()`
on this test line: `{failing_line}`
with the following test error: {error_message}

It can be fixed by this patch function
```
{patch_function}
```
"""

PFC_SUFFIX_FUNCTION_PROMPT = "Please generate an alternative fix function."

INIT_CHATGPT_INFILL_PROMPT = """
The following code contains a buggy line that has been removed.
```
{buggy_code}
```
This was the original buggy line which was removed by the infill location
```
// buggy line
{buggy_hunk}
```

Please provide the correct line at the infill location.
"""

INIT_CHATGPT_INFILL_FAILING_TEST = """
The following code contains a buggy line that has been removed.
```
{buggy_code}
```
This was the original buggy line which was removed by the infill location
```
// buggy line
{buggy_hunk}
```
The code fails on the test: `{failing_test}()`
with the following test error: {error_message}

Please provide the correct line at the infill location.
"""

INIT_CHATGPT_INFILL_FAILING_TEST_LINE = """
The following code contains a buggy line that has been removed.
```
{buggy_code}
```
This was the original buggy line which was removed by the infill location
```
// buggy line
{buggy_hunk}
```
The code fails on this test: `{failing_test}()`
on this test line: `{failing_line}`
with the following test error: {error_message}

Please provide the correct line at the infill location.
"""

INIT_CHATGPT_INFILL_HUNK = """
The following code contains a buggy hunk that has been removed.
```
{buggy_code}
```
This was the original buggy hunk which was removed by the infill location
```
// buggy hunk
{buggy_hunk}
```

Please provide the correct code hunk at the infill location.
"""


INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE = """
The following code contains a buggy hunk that has been removed.
```
{buggy_code}
```
This was the original buggy hunk which was removed by the infill location
```
// buggy hunk
{buggy_hunk}
```
The code fails on this test: `{failing_test}()`
on this test line: `{failing_line}`
with the following test error: {error_message}

Please provide the correct code hunk at the infill location.
"""

INIT_CHATGPT_INFILL_LINE_FAILING_TEST_LINE_QUIXBUGS = """
The following code contains a buggy line that has been removed.
```
{buggy_code}
```
This was the original buggy line which was removed by the infill location
```
// buggy line
{buggy_hunk}
```
{function_header}({values}) incorrectly returns {return_val} 

Please provide the correct code line at the infill location.
"""

INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE_QUIXBUGS = """
The following code contains a buggy hunk that has been removed.
```
{buggy_code}
```
This was the original buggy hunk which was removed by the infill location
```
// buggy hunk
{buggy_hunk}
```
{function_header}({values}) incorrectly returns {return_val} 

Please provide the correct code hunk at the infill location.
"""


INIT_CHATGPT_INFILL_FUNCTION_FAILING_TEST_LINE = """
The following code contains a bug.
```
{buggy_code}
```
The code fails on this test: `{failing_test}()`
on this test line: `{failing_line}`
with the following test error: {error_message}

Please provide the correct function to fix the bug.
"""

INIT_CHATGPT_INFILL_FUNCTION_FAILING_QUIXBUGS= """
The following code contains a bug.
```
{buggy_code}
```
{function_header}({values}) incorrectly returns {return_val} 

Please provide the correct function to fix the bug.
"""

INIT_CHATGPT_INFILL_FUNCTION = """
The following code contains a bug.
```
{buggy_code}
```

Please provide the correct function to fix the bug.
"""

INIT_CHATGPT_INFILL_FAILING_TEST_METHOD = """
The following code contains a buggy line that has been removed.
```
{buggy_code}
```
This was the original buggy line which was removed by the infill location
```
// buggy line
{buggy_hunk}
```
The code fails on this test: 
```
{failing_test_method}
```
with the following test error: {error_message}

Please provide the correct line at the infill location.
"""


INIT_CHATGPT_CORRECT_RESPONSE = """
The correct line at the infill location would be 
```
{correct_hunk}
```
"""

INIT_CHATGPT_CORRECT_HUNK_RESPONSE = """
The correct hunk at the infill location would be 
```
{correct_hunk}
```
"""

INIT_CHATGPT_CORRECT_FUNCTION_RESPONSE = """
The correct function would be 
```
{correct_hunk}
```
"""

CHATGPT_LOCALIZE_PROMPT = """
The following code contains a buggy line.
```
{buggy_code}
```

with the following failing tests:
{root_cause}

Please indicate which line is buggy.
"""

CHATGPT_LOCALIZE_RESPONSE = """
The buggy line in the above code is
```
{buggy_line}
```
"""