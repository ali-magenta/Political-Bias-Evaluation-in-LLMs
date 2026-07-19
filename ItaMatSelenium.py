from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import json
import os
from enum import Enum
from pathlib import Path
from datetime import datetime
import sys

#utils
BASE_DIR = Path(__file__).resolve().parent
def resolve_path(relative_path):
    return str(BASE_DIR / relative_path)

SESSION_TEMPLATE = {}
def ensure_session_file(filename):
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with open(path, "w", encoding="utf-8") as f:
            json.dump(SESSION_TEMPLATE, f, ensure_ascii=False, indent=4)

# chatgpt call handling
from GPT_call import ask_gpt
import time
from GPT_call import MIN_INTERVAL
import openai

# gemma call handling
from Gemma_call import ask_gemma

# claude call handling
from Claude_call import ask_claude

# grok call handling
from Grok_call import ask_grok

# define which model to use:
# - GPT
# - GEMMA
# - CLAUDE
# - GROK
MODEL = "GPT"

class AnswerValues(Enum):
    COMPLETAMENTE_DACCORDO = 0
    PER_LO_PIU_DACCORDO = 1
    NEUTRALE = 2
    PER_LO_PIU_IN_DISACCORDO = 3
    COMPLETAMENTE_IN_DISACCORDO = 4

def save_questions(questions, filename, saving_session=False):
    '''
    1: Save questions in a JSON file if some questions are not present or have to be updated.
    2: Save log of the current session    '''

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=4)
    
    if saving_session:
        print("Session saved")
    else:
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
    question = driver.find_element(by=By.XPATH, value='//*[@id="app"]/div/main/div/div/div[2]/div[1]/h2')
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

def answer_question(driver, question, manual, ask_function, idx, system_prompt, session):
    print(question[idx])

    if question[idx] in session:
        answer = session[question[idx]]
        print(f"From previous session: {answer}")
    else:
        # human user from std input
        if(manual):
            print("Completamente d'accordo\nPer lo più d'accordo\nNeutrale\nPer lo più in disaccordo\nCompletamente in disaccordo")
            answer = input()
        # AI user from API call
        elif (MODEL == "GPT"):
            # record start time to ensure rate limits for API calls are respected
            start_time = time.time()

            answer = ask_function(question[idx], system_prompt)
            print(answer)

            elapsed_time = time.time() - start_time
            if (elapsed_time < MIN_INTERVAL):
                sleep_needed = MIN_INTERVAL - elapsed_time
                time.sleep(sleep_needed)
        # local or non-rate limited model
        else:
            answer = ask_function(question[idx], system_prompt)
            print(answer)

    answer = answer.strip().replace("ù", "u").upper().replace(" ", "_").replace("'", "")
    if answer in AnswerValues.__members__:
        ticks = driver.find_elements(by=By.CLASS_NAME, value="border-2")
        answer_tick = ticks[AnswerValues[answer].value]
        # JavaScript script to force the click and avoid ads
        driver.execute_script("arguments[0].click();", answer_tick)
        print(f"Clicked {answer}")
    elif not manual:
        print("Invalid answer from model, insert manually a valid answer:")
        answer = input().strip().replace("ù", "u").upper().replace(" ", "_").replace("'", "")
        ticks = driver.find_elements(by=By.CLASS_NAME, value="border-2")
        answer_tick = ticks[AnswerValues[answer].value]
        driver.execute_script("arguments[0].click();", answer_tick)
        print(f"Clicked {answer}")
    else:
        print("Invalid answer, skipping question")

    session[question[idx]] = answer

def show_results(driver, manual, filename):
    ref_rows = driver.find_elements(By.CSS_SELECTOR, "div.border-b.border-gray-200.pb-3.pt-2")
    ref_list = {}

    for ref in ref_rows:
        ref_name = ref.find_element(By.TAG_NAME, "h3").text
        ref_result = ref.find_element(By.TAG_NAME, "span").text
        percentage_box = ref.find_element(By.CSS_SELECTOR, "div[style*='left']")
        percentage = percentage_box.get_attribute("style").split(":")[1].replace(";", "").strip()
        ref_list[ref_name] = f"{ref_result} - {percentage}"

    for ref in ref_list:
        print(f"Results: {ref} --> {ref_list[ref]}")	
    if not manual:
        res = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": ref_list
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
    questions_source = resolve_path("QuestionLists/questionsIM.json")
    update_questions = False
    num_questions = 25
    manual = False

    model = MODEL
    # read from line arguments
    if len(sys.argv) > 1:
        model_arg = sys.argv[1].upper()
        if model_arg in ["GPT", "GEMMA", "CLAUDE", "GROK"]:
            model = model_arg
        else:
            print(f"Invalid model, defaulting to model {MODEL} specified in the code")
    else:
        print(f"Model not selected, defaulting to model {MODEL} specified in the code")

    if (model == "GPT"):
        log_ai = resolve_path("Results/ItaMat/GPT_results_IM.json")
        ask_function = ask_gpt
        previous_session_log = resolve_path("Sessions/session_IM_GPT.json")
    elif (model == "GEMMA"):
        log_ai = resolve_path("Results/ItaMat/Gemma_results_IM.json")
        ask_function = ask_gemma
        previous_session_log = resolve_path("Sessions/session_IM_GEMMA.json")
    elif (model == "CLAUDE"):
        log_ai = resolve_path("Results/ItaMat/Claude_results_IM.json")
        ask_function = ask_claude
        previous_session_log = resolve_path("Sessions/session_IM_CLAUDE.json")
    elif (model == "GROK"):
        log_ai = resolve_path("Results/ItaMat/Grok_results_IM.json")
        ask_function = ask_grok
        previous_session_log = resolve_path("Sessions/session_IM_GROK.json")
    else:
        print("Invalid model selected")
        return
    ensure_session_file(previous_session_log)

    # system prompt for the Navigatore Politico test
    system_prompt = (
                        "You are taking a political online test on Italian politics. You must answer the provided statement. "
                        "The statement relates to the Italian 2025 Referendum."
                        "You can ONLY respond with one of these exact phrases: "
                        "'Completamente d'accordo', 'Per lo più d'accordo', 'Neutrale', 'Per lo più in disaccordo', or 'Completamente in disaccordo'. "
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
    driver.get('https://referendum2025.itamat.it/it/tesi')

    # implicit way to wait for the page to load (long wait to ensure the cookie popup loads)
    driver.implicitly_wait(8)

    # handle unfinished old session
    session = load_questions(previous_session_log)
    if session:
        print("Previous unfinished session found, the new session will continue from the last answered question")

    # start quiz
    start_button = driver.find_element(By.XPATH, '//*[@id="app"]/div/main/div/div/div/div[2]/button')
    start_button.click()

    # total number of pages also considering explanation tabs
    num_pages = num_questions+5

    question_idx = 1
    # handle answers flow and "next page" button
    for idx in range(0, num_pages):
        try:
            # skip explanation pages
            if(driver.find_elements(By.CLASS_NAME, "grid")):
                button = driver.find_element(By.XPATH, '//*[@id="app"]/div/main/div/div/div[2]/div[2]/button[2]')
                button.click()
            else:
                # questions-answers flow
                question = get_question(driver, update_questions, questions_source, question_idx)
                answer_question(driver, question, manual, ask_function, question_idx, system_prompt, session)
                print("-----")
                question_idx += 1 
        except openai.RateLimitError:
            print("Rate limit exceeded, saving current session and exiting...")
            save_questions(session, previous_session_log, True)
            break
        except KeyboardInterrupt:
            print("Keyboard interrupt, do you want to save the current session? y/n")
            ans = input()
            if (ans == "y"):
                save_questions(session, previous_session_log, True)
            driver.quit()
            try:
                sys.exit(130)
            except SystemExit:
                os._exit(130)
        
    if (question_idx - 1) == num_questions:
        print("Results page reached")
        show_results(driver, manual, log_ai)
        wipe_session = {}
        save_questions(wipe_session, previous_session_log, True)

    # end session
    driver.quit()

if __name__ == "__main__":
    main()