import openai
import os


openai.api_key = os.environ.get("API_KEY", "your-api-key")
openai.api_base = os.environ.get("API_BASE", "your-api-base")

c = openai.ChatCompletion.create(
                model=os.environ.get("MODEL_NAME", "deepseek-chat"),
                messages=[{"role": "user", "content": "What is the capital of France?"}],
                temperature=1,
                top_p=1,
                n=1,
                frequency_penalty=0.0,
                presence_penalty=0.0,
            )

print(c)