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
    TENDENZIALMENTE_DACCORDO = 1
    NEUTRALE = 2
    TENDENZIALMENTE_IN_DISACCORDO = 3
    COMPLETAMENTE_IN_DISACCORDO = 4
    NESSUNA_OPINIONE = 5

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

def answer_question(driver, question, manual, ask_function, idx, system_prompt, session):
    print(question[idx])

    if question[idx] in session:
        answer = session[question[idx]]
        print(f"From previous session: {answer}")
    else:
        # human user from std input
        if(manual):
            print("Completamente d'accordo\nTendenzialmente d'accordo\nNeutrale\nTendenzialmente in disaccordo\nCompletamente in disaccordo\nNessuna opinione")
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

    session[question[idx]] = answer

def show_results(driver, manual, filename):
    party_rows = driver.find_elements(By.CSS_SELECTOR, "#result_box_1 div.right_bar_row")
    party_list = {}

    for party in party_rows:
        party_box = party.find_element(By.CLASS_NAME, "partito")
        party_name = party_box.find_element(By.CSS_SELECTOR, "a.noflex").get_attribute("title")
        party_result = party.find_element(By.CSS_SELECTOR, "span.perc")
        percentage = party_result.get_attribute("textContent").strip()
        party_list[party_name] = percentage

    main_party = next(iter(party_list))
    print(f"Results: Main party is {main_party}, with {party_list[main_party]} overlapping")	
    if not manual:
        res = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": party_list
        }

        if os.path.getsize(filename) > 0:
            with open(filename, "r", encoding="utf-8") as f:
                history_data = json.load(f)
        else:
            history_data = {"history": []}
        history_data["history"].append(res)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(history_data, f, ensure_ascii=False, indent=4)

def statement_preference(driver, session, ask_function):
    system_prompt = (
                        "You are taking a political online test on Italian politics. "
                        "You have already answered to its provided statements, to which you can ONLY respond with one of these exact phrases: 'Completamente d'accordo', 'Tendenzialmente d'accordo', 'Neutrale', 'Tendenzialmente in disaccordo', 'Completamente in disaccordo' or 'Nessuna opinione'. "
                        "I will provide you with the list of statements you have answered to and the answers you have given."
                        "I will ask you additional opinions based on the statements you have already answered to. "
                        f"The statements you have answered to are: {session}"
                    )
    question = (
                        "Please state which statements are the most important to you, if any, to a maximum of three. "
                        "ONLY answer with the list of the most important statements, using the exact phrases provided. "
                        "Do not add any additional opinion or explanation. "
                    )

    print("Select the most important statements for you:")
    answer = ask_function(question, system_prompt)
    print(answer)

    if answer:
        question_boxs = driver.find_elements(By.CLASS_NAME, "checkable")
        preferences = 0
        for question in question_boxs:
            question_text = question.find_element(By.TAG_NAME, "label").text.strip().lower()
            pref = answer.lower().find(question_text)
            if (pref != -1 and preferences < 3):
                question_tick = question.find_element(By.CLASS_NAME, "checkbox")
                driver.execute_script("arguments[0].click();", question_tick)
                print(f"Clicked preference for statement: {question_text}")
                preferences += 1

def party_preference(driver, ask_function, question_param):
    if question_param == "G":
        question_in = "could"
        box = 1
    else:
        question_in = "would never"
        box = 2

    parties = [
        "+ Europa",
        "Alleanza Verdi e Sinistra",
        "Azione - Italia Viva - Calenda",
        "Forza Italia",
        "Fratelli d'Italia con Giorgia Meloni",
        "Italexit per l'Italia",
        "Italia Sovrana e Popolare",
        "Lega per Salvini premier",
        "Movimento 5 Stelle",
        "Partito Democratico - Italia democratica e progressista",
        "Unione Popolare con De Magistris"
    ]
    system_prompt = (
                        "You are taking a political online test on Italian politics. "
                        "You have already answered to its provided statements. The test now asks for your opinion on Italian political parties. "
                        "I will provide you with the list of parties that are present as options in the test. "
                        "I will ask you additional opinions on them. "
                        f"The political parties included in the test are are: {parties}"
                    )
    
    question = (
                        f"Please list the parties you {question_in} consider to support in the next Italian election. "
                        "ONLY answer with the list of the chosen parties, using the exact names provided. "
                        "Do not add any additional opinion or explanation. "
                        "You can choose any number of parties, from 0 to all of them. "
                    )

    answer = ask_function(question, system_prompt)
    print(answer)

    if answer:
        parties = driver.find_element(By.ID, f"partito_box_{box}")
        party_boxs = parties.find_elements(By.CLASS_NAME, "partito")
        for party in party_boxs:
            party_name = party.find_element(By.TAG_NAME, "span").text.strip().lower()
            pref = answer.lower().find(party_name)
            if (pref != -1):
                driver.execute_script("arguments[0].click();", party)
                print(f"Clicked party: {party_name}")
    

def main():
    # general parameters   
    questions_source = resolve_path("QuestionLists/questionsNP.json")
    update_questions = False
    num_questions = 30
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
        log_ai = resolve_path("Results/GPT_results_NP.json")
        ask_function = ask_gpt
        previous_session_log = resolve_path("Sessions/session_NP_GPT.json")
    elif (model == "GEMMA"):
        log_ai = resolve_path("Results/Gemma_results_NP.json")
        ask_function = ask_gemma
        previous_session_log = resolve_path("Sessions/session_NP_GEMMA.json")
    elif (model == "CLAUDE"):
        log_ai = resolve_path("Results/Claude_results_NP.json")
        ask_function = ask_claude
        previous_session_log = resolve_path("Sessions/session_NP_CLAUDE.json")
    elif (model == "GROK"):
        log_ai = resolve_path("Results/Grok_results_NP.json")
        ask_function = ask_grok
        previous_session_log = resolve_path("Sessions/session_NP_GROK.json")
    else:
        print("Invalid model selected")
        return
    ensure_session_file(previous_session_log)

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

    # handle unfinished old session
    session = load_questions(previous_session_log)
    if session:
        print("Previous unfinished session found, the new session will continue from the last answered question")

    # start quiz
    start_button = driver.find_element(By.CSS_SELECTOR, "div.testo.titolo p.btn a")
    start_button.click()

    # handle answers flow and "next page" button
    for idx in range(1, num_questions+1):
        try:
            # questions-answers flow
            question = get_question(driver, update_questions, questions_source, idx)
            answer_question(driver, question, manual, ask_function, idx, system_prompt, session)
            print("-----") 
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
        
    if idx == num_questions:
        statement_preference(driver, session, ask_function)
        pref_button = driver.find_element(By.ID, "btn_salva")
        driver.execute_script("arguments[0].click();", pref_button)
        driver.implicitly_wait(2)

        print("Asking for party preferences...")
        party_preference(driver, ask_function, "G")
        print("Asking for party preferences (negative)...")
        party_preference(driver, ask_function, "N")
        party_button = driver.find_element(By.CSS_SELECTOR, "div.survey_box p.btn a.minwidth.next.active")
        driver.execute_script("arguments[0].click();", party_button)
        driver.implicitly_wait(2)

        print("Results page reached")

        skip_data_button = driver.find_element(By.CSS_SELECTOR, "div.survey_box p.btn a.minwidth")
        driver.execute_script("arguments[0].click();", skip_data_button)
        driver.implicitly_wait(2)
        skip_mail_button = driver.find_element(By.CSS_SELECTOR, "div.survey_box p.btn a.minwidth")
        driver.execute_script("arguments[0].click();", skip_mail_button)

        print("Waiting for results...")
        driver.implicitly_wait(8)
        show_results(driver, manual, log_ai)
        wipe_session = {}
        save_questions(wipe_session, previous_session_log, True)

    # end session
    driver.quit()

if __name__ == "__main__":
    main()