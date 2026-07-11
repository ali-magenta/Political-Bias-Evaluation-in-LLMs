from openrouter import OpenRouter
import os

model = "anthropic/claude-haiku-4.5"

def ask_claude(question, system_prompt):
    with OpenRouter (
        api_key = os.getenv("OPENROUTER_KEY")
    ) as client:
        try:
            response = client.chat.send(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": f"{system_prompt}"
                    },
                    {
                        "role": "user",
                        "content": f"{question}"
                    }
                ],
            )

            response_text = response.choices[0].message.content.strip()
            return response_text
        
        except Exception as e:
            print(f"Model failed to answer with error {str(e)}, defaulting to Disagree...")
            return "Disagree"