import openai
import time
import os

openai.api_key = os.environ.get("API_KEY", "your-api-key")
openai.api_base = os.environ.get("API_BASE", "your-api-base")

def call_chatgpt(messages, model=None, stop=None, temperature=1.0, top_p=1.0,
        max_tokens=4096, echo=False, majority_at=None):
    
    model = os.environ.get("MODEL_NAME", "deepseek-chat")
    
    num_completions = majority_at if majority_at is not None else 1
    num_completions_batch_size = 10

    completions = []
    for i in range(20 * (num_completions // num_completions_batch_size + 1)):
        try:
            requested_completions = min(num_completions_batch_size, num_completions - len(completions))

            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                n=requested_completions,
                frequency_penalty=0.0,
                presence_penalty=0.0,
            )
            
            completions.extend([choice.message.content for choice in response.choices])
            if len(completions) >= num_completions:
                return completions[:num_completions]
                
        except openai.error.RateLimitError as e:
            print(f"Rate limit hit, waiting {min(i**2, 60)} seconds...")
            time.sleep(min(i**2, 60))
        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(min(i**2, 60))
            
    raise RuntimeError('Failed to call GPT API after multiple attempts')