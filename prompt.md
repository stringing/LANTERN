# Decision-Making Prompt of Optimal Target Language Selection

![Alt text](fig/decision-making.png)

### Program repair and translation
Prompt structure of program repair comprises key components such as problem description, error type, input and output specification, buggy code, and the repair instruction. Code translation prompt consists of the specified source and target languages, the corresponding code, and the translation instruction. Back-translation shares the same prompt design as code translation with opposite source and target languages.

### Target language decision-making
To construct the translation decision-making prompt, we adopt the basic structure from existing works of program repair agents, which demonstrate a common pipeline that mainly consists of role specification, problem statements, and task instructions. Specifically, the intermediate problem statements cover components such as the goals, guidelines, gathered information, and input and output specification. Moreover, we refer to prior work that incorporates the historical records in the prompt as environmental feedback to facilitate comprehensive reasoning. 

The above figure presents the translation decision-making prompt structure where a system message specifies the role of the LLM as a program repair tool, supported by detailed bug characteristics, top-k historical feedback of the initial direct repair as well as translation-based repair with similar bugs from previous attempts. All are integrated with task instructions that define the target language scope, list previously attempted languages to avoid repetition, specify objectives and constraints, and employ a hand-crafted zero-shot CoT instruction to guide a concise and step-by-step decision process.

The figure also exhibits an example of LLM response with the selected target language and a step-by-step justification. Each step of the justification corresponds to a different component provided in the prompt. The reasoning process takes into consideration the information such as the current bug characteristics, the historical feedback, and the restrictions to conclude a final decision on the target language. 

