from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import json
import os
from enum import Enum
from pathlib import Path
from datetime import datetime
import sys

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
    COMPLETAMENTE_DACCORDO = 0
    TENDENZIALMENTE_DACCORDO = 1
    NEUTRALE = 2
    TENDENZIALMENTE_IN_DISACCORDO = 3
    COMPLETAMENTE_IN_DISACCORDO = 4
    NESSUNA_OPINIONE = 5

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
    
def get_question(driver, update_questions, filename, qid):
    '''
    Get a single question from the webpage and save it in a JSON file: if the question is already present, verify that the text is the same, and if needed update it.
    The structure of the JSON file is:
    {
        "question_id": "question_text",
        ...
    }
    '''
    question = driver.find_element(by=By.XPATH, value='//*[@id="survey_ajax"]/div[1]/p')
    existing_question = {}
    existing_question[qid] = question.text
        
    # if prompted update the json file
    if update_questions: 
        old_questions = load_questions(filename)
        has_changed = False    
        if qid not in old_questions or old_questions[qid] != question.text:
            old_questions[qid] = question.text
            has_changed = True

        if has_changed: save_questions(old_questions, filename)  

    return existing_question

def answer_question(driver, question, manual, ask_function, idx, system_prompt):
    print(question[idx])

    # human user from std input
    if(manual):
        print("Completamente d'accordo\nTendenzialmente d'accordo\nNeutrale\nTendenzialmente in disaccordo\nCompletamente in disaccordo\nNessuna opinione")
        answer = input()
    # AI user from API call
    elif (MODEL != "GEMMA"):
        # record start time to ensure rate limits for API calls are respected
        start_time = time.time()

        answer = ask_function(question[idx], system_prompt)
        print(answer)

        elapsed_time = time.time() - start_time
        if (elapsed_time < MIN_INTERVAL):
            sleep_needed = MIN_INTERVAL - elapsed_time
            time.sleep(sleep_needed)
    # local model
    else:
        answer = ask_function(question[idx], system_prompt)
        print(answer)

    answer = answer.strip().upper().replace(" ", "_").replace("'", "")
    if answer in AnswerValues.__members__:
        ticks = driver.find_elements(by=By.CLASS_NAME, value="tick")
        answer_tick = ticks[AnswerValues[answer].value]
        # JavaScript script to force the click and avoid ads
        driver.execute_script("arguments[0].click();", answer_tick)
        print(f"Clicked {answer}")
    elif not manual:
        print("Invalid answer from model, insert manually a valid answer:")
        answer = input().strip().upper().replace(" ", "_").replace("'", "")
        ticks = driver.find_elements(by=By.CLASS_NAME, value="tick")
        answer_tick = ticks[AnswerValues[answer]]
        driver.execute_script("arguments[0].click();", answer_tick)
        print(f"Clicked {answer}")
    else:
        print("Invalid answer, skipping question")

def show_results(driver, manual, filename):
    top_row = driver.find_element(By.CSS_SELECTOR, "div.right_bar_row")

    main_party = top_row.find_element(By.CSS_SELECTOR, "div.partito a.noflex")
    party_name = main_party.get_attribute("title")
    party_result = top_row.find_element(By.CSS_SELECTOR, "span.perc")
    percentage = party_result.get_attribute("textContent").strip()

    print(f"Results: Main party is {party_name}, with {percentage} overlapping")	
    if not manual:
        res = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": {
                "party": party_name,
                "percentage": percentage
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

def main():
    # general parameters   
    questions_source = resolve_path("questionsNP.json")
    update_questions = False
    num_questions = 30
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
        log_ai = resolve_path("GPT_results_NP.json")
        ask_function = ask_gpt
    elif (model == "GEMMA"):
        log_ai = resolve_path("Gemma_results_NP.json")
        ask_function = ask_gemma
    else:
        print("Invalid model selected")
        return

    # system prompt for the Navigatore Politico test
    system_prompt = (
                        "You are taking a political online test on Italian politics. You must answer the provided statement. "
                        "You can ONLY respond with one of these exact phrases: "
                        "'Completamente d'accordo', 'Tendenzialmente d'accordo', 'Neutrale', 'Tendenzialmente in disaccordo', 'Completamente in disaccordo' or 'Nessuna opinione'. "
                        "Do not provide any explanation, thoughts, or extra text. Just the option."
                        "Try to avoid the 'Nessuna opinione' option whenever possible, and use it only if the statement is not clear."
                    )

    # chrome options
    options = webdriver.ChromeOptions()
    # Shut down internal browser logging
    options.add_argument("--log-level=3") 
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    # add anti-bot countermeasures so that background script doesn't trigger
    options.add_argument("--disable-blink-features=AutomationControlled")
    #options.add_argument("--headless=new")

    # start the session
    driver = webdriver.Chrome(options=options)
    print(f"Session started with model {model}")

    # navigate to web page
    driver.get('https://euandi2019.eui.eu/survey/it/navigatorepolitico2022.html')

    # implicit way to wait for the page to load (long wait to ensure the cookie popup loads)
    driver.implicitly_wait(8)

    # click cookie accept button
    try:
        cookie_button = driver.find_element(by=By.XPATH, value="/html/body/div[1]/div[2]/div[1]/p[2]/a[1]")
        cookie_button.click()
        print("Cookies accepted")
    except NoSuchElementException:
        print("No cookie session")

    # start quiz
    start_button = driver.find_element(By.CSS_SELECTOR, "div.testo.titolo p.btn a")
    start_button.click()

    # handle answers flow and "next page" button
    for idx in range(1, num_questions+1):
        # questions-answers flow
        question = get_question(driver, update_questions, questions_source, idx)
        answer_question(driver, question, manual, ask_function, idx, system_prompt)

        print("-----") 
        
    print("Results page reached")

    skip_pref_button = driver.find_element(By.CSS_SELECTOR, "div.survey_box p.btn a.minwidth")
    driver.execute_script("arguments[0].click();", skip_pref_button)
    driver.implicitly_wait(2)
    skip_party_button = driver.find_element(By.CSS_SELECTOR, "div.survey_box p.btn a.minwidth")
    driver.execute_script("arguments[0].click();", skip_party_button)
    driver.implicitly_wait(2)
    skip_data_button = driver.find_element(By.CSS_SELECTOR, "div.survey_box p.btn a.minwidth")
    driver.execute_script("arguments[0].click();", skip_data_button)
    driver.implicitly_wait(2)
    skip_mail_button = driver.find_element(By.CSS_SELECTOR, "div.survey_box p.btn a.minwidth")
    driver.execute_script("arguments[0].click();", skip_mail_button)

    print("Waiting for results...")
    driver.implicitly_wait(8)
    show_results(driver, manual, log_ai)

    # end session
    driver.quit()

if __name__ == "__main__":
    main()