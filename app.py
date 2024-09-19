import openai

client = openai.OpenAI(base_url="https://codestral.us.gaianet.network/v1", api_key="api_key")

completion = client.chat.completions.create(
    model="codestral",
    messages=[
        {"role": "system", "content": "You are GodotGuru."},
        {
            "role": "user",
            "content": "Tell me about yourself"
        }
    ]
)

print(completion.choices[0].message.content)