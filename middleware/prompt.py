from promptsource.templates import Template


PROMPTS = {
    'system': 'You are an automated program repair tool.',
    'apr': "Fix a buggy program written in {{lang_cluster}} language to solve the following programming problem:\nDescription: {{prob_desc_description}}\nInput Specification: {{prob_desc_input_spec}}\nOutput Specification: {{prob_desc_output_spec}}\n{% for input, output in zip(prob_desc_sample_inputs, prob_desc_sample_outputs) %}\nSample Input:\n{{input}}\nSample Output:\n{{output}}\n{% endfor %}\nNotes: {{prob_desc_notes}}\nTake input from {{prob_desc_input_from}} and output to {{prob_desc_output_to}}\n\nHere is the code with a bug of {{bug_exec_outcome}}:\n\n{{bug_source_code}}\n\nProvide the fixed {{lang_cluster}} code without any description or extra tokens.\n\nFixed source code:\n ||END-of-SRC|| ",
    'language_decision': 'Current Bug Information:\n{{bug_info}}\n\nHistorical Repair Data:\n{{history}}\n\nScope of Target Languages: {{scope}}\n\nPreviously Attempted Languages: {{attempted}}\n\nTask Description: The task is to translate the bugs that cannot be fixed in one programming language to another programming language and then try to fix it. You need to analyze the current bug and decide which programming language to translate it to for the next repair iteration. Base your decision on the provided historical repair data. Initially, the historical data includes previous repair attempts for bugs similar to the current bug. After the initial iteration, the historical translation-repair attempts will also be added to the historical repair data for you to analyze.\n- Consider factors such as:\n    - Bug similarity.\n    - Repair language.\n    - pass@10 scores.\n- Provide a justification for your decision step by step.\n\nConstraints:\n- The target language you select must be within the scope of target languages.\n- Previously attempted languages cannot be used again.\n\nOutput Format (json):\n- Target Language: [Your recommended language]\n- Justification: [Your reasoning]||END-of-SRC|| ',
    'nohist': 'There is buggy code in {{lang}} language.\n\nScope of Target Languages: {{scope}}\n\nPreviously Attempted Languages: {{attempted}}\n\nTask Description: The task is to translate the bugs that cannot be fixed in one programming language to another programming language and then try to fix it. You need to decide which programming language to translate it to for the next repair iteration. \n- Provide a justification for your decision step by step.\n\nConstraints:\n- The target language you select must be within the scope of target languages.\n- Previously attempted languages cannot be used again.\n\nOutput Format:\n- Target Language: [Your recommended language]\n- Justification: [Your reasoning]||END-of-SRC|| ',
    'translation': 'Here is code in {{source_lang}} programming lanaguge. Translate the following code from {{source_lang}} to {{target_lang}} programming lanaguge. Do not output any extra description or tokens other than the translated code. \n\n{{bug_source_code}}||END-of-SRC|| ',
    'back_translation': 'Here is code in {{target_lang}} programming lanaguge. Translate the following code from {{target_lang}} to {{source_lang}} programming lanaguge. Do not output any extra description or tokens other than the translated code. \n\n{{bug_source_code}}||END-of-SRC|| '
}

def apr(dt):
    tpl = Template("apr", PROMPTS['apr'], "xCodeEval", delimeter="||END-of-SRC||")
    prompt_text = tpl.apply(dt)
    return prompt_text

def decision(bug_retrieval):
    tpl = Template("decision", PROMPTS['language_decision'], "xCodeEval", delimeter="||END-of-SRC||")
    prompt_text = tpl.apply(bug_retrieval)
    return prompt_text

def nohist(bug_retrieval):
    tpl = Template("decision_nohist", PROMPTS['nohist'], "xCodeEval", delimeter="||END-of-SRC||")
    prompt_text = tpl.apply(bug_retrieval)
    return prompt_text

def trans(dt):
    tpl = Template("trans", PROMPTS['translation'], "xCodeEval", delimeter="||END-of-SRC||")
    prompt_text = tpl.apply(dt)
    return prompt_text

def back_trans(dt):
    tpl = Template("backtrans", PROMPTS['back_translation'], "xCodeEval", delimeter="||END-of-SRC||")
    prompt_text = tpl.apply(dt)
    return prompt_text
