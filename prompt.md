# Overview

Our program repair prompt integrates a concise problem description, error type, input/output specifications, the buggy code, and a repair instruction. A key aspect of our framework is that in the repair prompt, the error type provided remains consistent both before and after the code is translated to a new language. This is a deliberate design choice since the failure information we use is high-level (e.g., TIME LIMIT EXCEEDED, WRONG ANSWER) rather than a fine-grained, language-specific error such as stack traces or faulty lines. While the problem description already sets the same ultimate objective of the repair, such high-level information points to the fundamental algorithmic or logical flaw, which is often preserved during translation. By providing this consistent context, we prompt the LLM's repair task to solve the root cause of the bug, which remains relevant across different languages.
On the other hand, even if the translation introduces a new bug, the subsequent repair process can attempt to address both the newly introduced and pre-existing bugs simultaneously, working toward the ultimate objective defined by the problem description. This approach also avoids the significant computational overhead of re-executing every translated bug to adapt the information in the prompt by checking whether a different failure is introduced, making our iterative process more efficient.
Similarly, our code translation prompt specifies the source and target languages, the corresponding code, and the translation instruction, with back-translation using the reversed source and target languages.
We also design the prompt dedicated to translation decision-making as illustrated in Figure 4 in a zero-shot chain of thought (CoT) paradigm, which systematically integrates bug characteristics, historical repair feedback, and task constraints into a structured reasoning framework. Through this step-by-step process, the model autonomously identifies optimal target languages that demonstrate superior capabilities in fixing similar bugs.


## Decision-Making Prompt of Optimal Target Language Selection

![Alt text](fig/decision-making.png)

### Program repair and translation
Prompt structure of program repair comprises key components such as problem description, error type, input and output specification, buggy code, and the repair instruction. Code translation prompt consists of the specified source and target languages, the corresponding code, and the translation instruction. Back-translation shares the same prompt design as code translation with opposite source and target languages.

### Target language decision-making
To construct the translation decision-making prompt, we adopt the basic structure from existing works of program repair agents, which demonstrate a common pipeline that mainly consists of role specification, problem statements, and task instructions. Specifically, the intermediate problem statements cover components such as the goals, guidelines, gathered information, and input and output specification. Moreover, we refer to prior work that incorporates the historical records in the prompt as environmental feedback to facilitate comprehensive reasoning. 

The above figure presents the translation decision-making prompt structure where a system message specifies the role of the LLM as a program repair tool, supported by detailed bug characteristics, top-k historical feedback of the initial direct repair as well as translation-based repair with similar bugs from previous attempts. All are integrated with task instructions that define the target language scope, list previously attempted languages to avoid repetition, specify objectives and constraints, and employ a hand-crafted zero-shot CoT instruction to guide a concise and step-by-step decision process.

The figure also exhibits an example of LLM response with the selected target language and a step-by-step justification. Each step of the justification corresponds to a different component provided in the prompt. The reasoning process takes into consideration the information such as the current bug characteristics, the historical feedback, and the restrictions to conclude a final decision on the target language. 

