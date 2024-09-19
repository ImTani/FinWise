# Use a pipeline as a high-level helper
from transformers import pipeline

messages = [
    {"role": "user", "content": "Who are you?"},
]
pipe = pipeline("text-generation", model="mattshumer/Reflection-Llama-3.1-70B")
pipe(messages)