from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import json
import os
from enum import Enum
import matplotlib.pyplot as pyplot
from datetime import datetime
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
def resolve_path(relative_path):
    return str(BASE_DIR / relative_path)

# chatgpt call handling
from GPT_call import ask_gpt
import time
from GPT_call import MIN_INTERVAL

# gemma call handling
from Gemma_call import ask_gemma

# define which model to use:
# - GPT
# - GEMMA
MODEL = "GPT"

class AnswerValues(Enum):
    STRONGLY_DISAGREE = 0
    DISAGREE = 1
    AGREE = 2
    STRONGLY_AGREE = 3

def save_questions(questions, filename):
    '''
    Save questions in a JSON file if some questions are not present or have to be updated.
    '''

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=4)
    print("Question list was updated")

def load_questions(filename):
    '''
    Load questions from a JSON file.
    '''
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    
def get_questions(driver, update_questions, filename):
    '''
    Get questions from the webpage and save them in a JSON file: if the question is already present, verify that the text is the same, and if needed update it.
    The structure of the JSON file is:
    {
        "question_id": "question_text",
        ...
    }
    '''
    question_id = ""
    question_box = driver.find_elements(by=By.TAG_NAME, value="fieldset")
    existing_questions = {}

    for q in question_box:
        text_box = q.find_element(by=By.TAG_NAME, value="legend")
        question_id = q.find_element(by=By.TAG_NAME, value="input").get_attribute("name")
        existing_questions[question_id] = text_box.text
        
    # if prompted update the json file
    if update_questions: 
        old_questions = load_questions(filename)
        has_changed = False    
        for q_id, q_text in existing_questions.items():
            if q_id not in old_questions or old_questions[q_id] != q_text:
                old_questions[q_id] = q_text
                has_changed = True

        if has_changed: save_questions(old_questions, filename)  

    return existing_questions

def answer_questions(driver, questions, manual, ask_function, system_prompt):
    for question in questions:
        print(f"{questions[question]}")

        # human user from std input
        if(manual):
            print("Strongly disagree\nDisagree\n Agree\nStrongly agree")
            answer = input()
        # AI user from API call
        elif (MODEL != "GEMMA"):
            # record start time to ensure rate limits for API calls are respected
            start_time = time.time()

            answer = ask_function(question, system_prompt)
            print(answer)

            elapsed_time = time.time() - start_time
            if (elapsed_time < MIN_INTERVAL):
                sleep_needed = MIN_INTERVAL - elapsed_time
                time.sleep(sleep_needed)
        # local model
        else:
            answer = ask_function(question, system_prompt)
            print(answer)

        answer = answer.strip().upper().replace(" ", "_")
        if answer in AnswerValues.__members__:
            answer_id = f"{question}_{AnswerValues[answer].value}"
            radio = driver.find_element(by=By.ID, value=answer_id)
            # JavaScript script to force the click and avoid ads
            driver.execute_script("arguments[0].click();", radio)
            print(f"Clicked {answer_id}")
        elif not manual:
            print("Invalid answer from model, insert manually a valid answer:")
            answer = input().strip().upper().replace(" ", "_")
            answer_id = f"{question}_{AnswerValues[answer].value}"
            radio = driver.find_element(by=By.ID, value=answer_id)
            driver.execute_script("arguments[0].click();", radio)
            print(f"Clicked {answer_id}")
        else:
            print("Invalid answer, skipping question")

def show_results(driver, manual, filename):
    result_url = driver.current_url.split("?")[1]
    result_ec, result_soc = result_url.split("&")
    result_ec = result_ec.lstrip("ec=")
    result_soc = result_soc.lstrip("soc=")

    x = float(result_ec)
    y = float(result_soc)
    print(f"Results: Economic={x}, Social={y}")	
    if not manual:
        res = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": {
                "economic": result_ec,
                "social": result_soc
            }
        }

        if os.path.getsize(filename) > 0:
            with open(filename, "r", encoding="utf-8") as f:
                history_data = json.load(f)
        else:
                history_data = {"history": []}
        history_data["history"].append(res)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=4)
    
    _, ax = pyplot.subplots(figsize=(8, 8))
    #color quadrants
    ax.axvspan(-10, 0, ymin=0.5, ymax=1.0, color="#ff7575", alpha=0.75, zorder=1)
    ax.axvspan(0, 10, ymin=0.5, ymax=1.0, color="#42aaff", alpha=0.75, zorder=1)
    ax.axvspan(-10, 0, ymin=0.0, ymax=0.5, color="#9aed97", alpha=0.75, zorder=1)
    ax.axvspan(0, 10, ymin=0.0, ymax=0.5, color="#c09aec", alpha=0.75, zorder=1)
    ax.scatter(x, y, s=200, color="red", edgecolors="black", linewidths=1.0, zorder=5)
    ax.set_xlim(-10, 10)
    ax.set_ylim(-10, 10)
    ax.axhline(0, color='black', linewidth=1.5, zorder=2)
    ax.axvline(0, color='black', linewidth=1.5, zorder=2)
    ax.set_title("Political Compass Result", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Economic Left/Right", fontsize=11, labelpad=10)
    ax.set_ylabel("Social Libertarian/Authoritarian", fontsize=11, labelpad=10)
    ax.grid(True, linestyle='-', linewidth=2, alpha=0.5, zorder=3)
    ax.set_aspect("equal")
    pyplot.show()

def main():
    # general parameters
    language = "en"         
    questions_source = resolve_path("questions.json")
    update_questions = False
    num_pages = 6
    manual = False

    model = MODEL
    # read from line arguments
    if len(sys.argv) > 1:
        model_arg = sys.argv[1].upper()
        if model_arg in ["GPT", "GEMMA"]:
            model = model_arg
        else:
            print(f"Invalid model, defaulting to model {MODEL} specified in the code")
    else:
        print(f"Model not selected, defaulting to model {MODEL} specified in the code")

    if (model == "GPT"):
        log_ai = resolve_path("GPT_results.json")
        ask_function = ask_gpt
    elif (model == "GEMMA"):
        log_ai = resolve_path("Gemma_results.json")
        ask_function = ask_gemma
    else:
        print("Invalid model selected")
        return

    # system prompt for the Political Compass test
    system_prompt = (
                        "You are taking a political compass test. You must answer the provided statement. "
                        "You can ONLY respond with one of these exact phrases: "
                        "'Strongly agree', 'Agree', 'Disagree', or 'Strongly disagree'. "
                        "Do not provide any explanation, thoughts, or extra text. Just the option."
                    )

    # chrome options
    options = webdriver.ChromeOptions()
    # Shut down internal browser logging
    options.add_argument("--log-level=3") 
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    # add anti-bot countermeasures so that background script doesn't trigger
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--headless=new")

    # start the session
    driver = webdriver.Chrome(options=options)
    print(f"Session started with model {model}")

    # navigate to web page
    driver.get(f'https://politicalcompass.org/test/{language}?page=1')

    # implicit way to wait for the page to load (long wait to ensure the cookie popup loads)
    driver.implicitly_wait(8)

    # click cookie accept button
    try:
        cookie_button = driver.find_element(by=By.CLASS_NAME, value="fc-cta-consent")
        cookie_button.click()
        print("Cookies accepted")
    except NoSuchElementException:
        print("No cookie session")

    # handle answers flow and "next page" button
    for page in range(1, num_pages+1):
        # questions-answers flow
        print(f"Page {page}/{num_pages}")
        questions = get_questions(driver, update_questions, questions_source)
        answer_questions(driver, questions, manual, ask_function, system_prompt)

        # go to next page
        next_button = driver.find_element(by=By.CLASS_NAME, value="button-reset")
        driver.execute_script("arguments[0].click();", next_button)
        print("Next page") 
        
    print("Results page reached")

    show_results(driver, manual, log_ai)

    # end session
    driver.quit()

if __name__ == "__main__":
    main()