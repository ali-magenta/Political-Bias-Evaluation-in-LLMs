from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import json
from enum import Enum

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

def answer_questions(driver, questions):
    for question in questions:
        print(f"{questions[question]}")
        print("Strongly disagree \n Disagree \n Agree \n Strongly agree")
        answer = input().strip().upper().replace(" ", "_")
        if answer in AnswerValues.__members__:
            answer_id = f"{question}_{AnswerValues[answer].value}"
            radio = driver.find_element(by=By.ID, value=answer_id)
            # JavaScript script to force the click and avoid ads
            driver.execute_script("arguments[0].click();", radio)
            print(f"Clicked {answer_id}")
        else:
            print("Invalid answer, skipping question")

def main():
    # general parameters
    language = "en"         # language may be en or it
    filename = "questions.json"
    update_questions = False
    num_pages = 6

    # chrome options
    options = webdriver.ChromeOptions()
    # Shut down internal browser logging
    options.add_argument("--log-level=3") 
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    # add anti-bot countermeasures so that background script doesn't trigger
    options.add_argument("--disable-blink-features=AutomationControlled")

    # start the session
    driver = webdriver.Chrome()

    # navigate to a web page
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
    page_counter = 1
    while True:
        # TODO move this try to make it cleaner
        try:
            # questions-answers flow
            print(f"Page {page_counter}/{num_pages}")
            questions = get_questions(driver, update_questions, filename)
            answer_questions(driver, questions)

            # go to next page
            next_button = driver.find_element(by=By.CLASS_NAME, value="button-reset")
            driver.execute_script("arguments[0].click();", next_button)
            page_counter += 1
            print("Next page") 
        except NoSuchElementException:
            print("Last page reached")
            break

    # end session
    driver.quit()

if __name__ == "__main__":
    main()