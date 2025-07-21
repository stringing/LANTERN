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

TRANS_PROMPT = """
Here is code in {source_lang} programming lanaguge. Translate the following code from {source_lang} to {target_lang} programming lanaguge. Do not output any extra description or tokens other than the translated code. 
```
{buggy_code}
```
"""

BACK_TRANS_PROMPT = """
Here is code in {source_lang} programming lanaguge. 
```
{buggy_code}
```

Translate the {source_lang} code from {source_lang} to {target_lang} programming lanaguge. 
Prefix: 
```
{prefix}

Translate only the function/method from {source_lang} to {target_lang} with the given prefix. Output only the equivalent function/method in {target_lang} without any additional code such as imports, class declarations, package statements, or wrapper code. Do not output any extra description or tokens other than the translated code. 
"""

# REPAIR_TRANSLATED_PROMPT = """
# The following {target_lang} code is a translation of buggy Java code that needs to be fixed.

# {translated_buggy_code}

# The original Java code fails on this test: 

# Failing test: {failing_test}
# Error message: {error_message}
# Failing line: {failing_line}

# Please fix the {target_lang} code so that when translated back to Java, it will pass the test. Focus on the logical error rather than language-specific syntax.
# """

# REPAIR_TRANSLATED_PROMPT = """
# Here is buggy {target_lang} code that needs to be fixed.
# ```
# {translated_buggy_code}
# ```
# The {target_lang} code has a bug similar to the following Java test failure: 

# Failing test: {failing_test}
# Error message: {error_message}
# Failing line: {failing_line}

# Please provide the fixed {target_lang} code. Do not output any extra description or tokens other than the fixed code.
# """

REPAIR_TRANSLATED_PROMPT = """
Here is buggy {target_lang} code that needs to be fixed.
```
{translated_buggy_code}
```

There was a Java bug very similar to the {target_lang} bug, which has the following test failure: 

Failing test: {failing_test}
Test function: 
```
{failing_test_function}
```
Failing line: {failing_line}
Error message: {error_message}


Please provide the fixed {target_lang} code. Do not output any extra description or tokens other than the fixed code.
"""

+

# Here is buggy code in C++ programming language. Fix the bug based on the failing test information.

# Buggy code:
# {buggy_code}

# Failing test: {failing_test}
# Error message: {error_message}
# Failing line: {failing_line}

# Please provide the corrected C++ code. Do not output any extra description or tokens other than the fixed code.
# """



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