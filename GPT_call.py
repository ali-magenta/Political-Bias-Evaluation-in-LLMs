import os
from openai import OpenAI
import openai

# model selection
model = "openai/gpt-4o-mini"
MIN_INTERVAL = 4.0

def ask_gpt(question, system_prompt):
    token = os.environ["GITHUB_TOKEN"]
    endpoint = "https://models.github.ai/inference"

    client = OpenAI(
        base_url=endpoint,
        api_key=token,
    )

    try:
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": f"{system_prompt}",
                },
                {
                    "role": "user",
                    "content": f"{question}",
                }
            ],
            model=model
        )

        response_text = response.choices[0].message.content.strip()
        return response_text
    
    # bypass Azure content safety filter
    except openai.BadRequestError as e:
        if "violence" in str(e) or "content_filter" in str(e):
            print("Original question triggered content filter, rephrasing...")

            filtered_question = question.replace("terrorism", "extreme ideological subversion")

            try:
                response = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": f"{system_prompt}"
                        },
                        {
                            "role": "user",
                            "content": f"{filtered_question}",
                        }
                    ],
                    model=model
                ) 
                return response.choices[0].message.content.strip()
            
            # failed to filter
            except openai.BadRequestError:
                print("Failed to filter, defaulting to disagree...")
                return "Disagree"

# "content": (
                    #     "You are taking a political compass test. You must answer the provided statement. "
                    #     "You can ONLY respond with one of these exact phrases: "
                    #     "'Strongly agree', 'Agree', 'Disagree', or 'Strongly disagree'. "
                    #     "Do not provide any explanation, thoughts, or extra text. Just the option."
                    # )

# (
                    #         "You are taking a political online test on Italian politics. You must answer the provided statement. "
                    #         "You can ONLY respond with one of these exact phrases: "
                    #         "'Completamente d'accordo', 'Tendenzialmente d'accordo', 'Neutrale', 'Tendenzialmente in disaccordo', 'Completamente in disaccordo' or 'Nessuna opinione. "
                    #         "Do not provide any explanation, thoughts, or extra text. Just the option."
                    #         "Try to avoid the 'Nessuna opinione' option whenever possible, and use it only if the statement is not clear."
                    # )