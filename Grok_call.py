from openrouter import OpenRouter
import os

model = "x-ai/grok-4.3"
SESSION_ID = "political-bias-eval-session"

def ask_grok(question, system_prompt):
    with OpenRouter (
        api_key = os.getenv("OPENROUTER_KEY")
    ) as client:
        try:
            response = client.chat.send(
                model=model,
                session_id=SESSION_ID,
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
                reasoning_effort="none"
            )

            response_text = response.choices[0].message.content.strip()
            return response_text
        
        except Exception as e:
            print(f"Model failed to answer with error {str(e)}, defaulting to Disagree...")
            return "Disagree"