from ollama import chat, ChatResponse

def ask_gemma(question, system_prompt):
    model = "gemma4:e2b"

    try:
        response: ChatResponse = chat(model=model, messages=[
            {
                'role': 'system',
                'content':  f"{system_prompt}",
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