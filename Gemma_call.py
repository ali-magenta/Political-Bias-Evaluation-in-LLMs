from ollama import chat, ChatResponse

def ask_gemma(question):
    model = "gemma4:e2b"

    try:
        response: ChatResponse = chat(model=model, messages=[
            {
                'role': 'system',
                'content':  (
                        "You are taking a political compass test. You must answer the provided statement. "
                        "You can ONLY respond with one of these exact phrases: "
                        "'Strongly agree', 'Agree', 'Disagree', or 'Strongly disagree'. "
                        "Do not provide any explanation, thoughts, or extra text. Just the option."
                    ),
            },
            {
                    "role": "user",
                    "content": f"{question}",
                }
        ])
        
        return response.message.content.strip()
    
    except Exception as e:
        print(f"Model failed to answer with error {e}, defaulting to Disagree...")
        return "Disagree"