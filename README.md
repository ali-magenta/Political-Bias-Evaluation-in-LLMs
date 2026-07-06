# Political-Bias-Evaluation-in-LLMs

This project contains scripts to administer political orientation tests to the most common LLMs to evaluate their political bias.

### Dependencies

#### Python modules

To fully run the scripts, you need to install the following Python modules:

- os
- openai
- selenium
- json
- enum
- matplotlib
- datetime
- ollama
- sys
- pathlib

All of them must be installed using

```bash
pip install <module_name1> <module_name2> ...
```

or using the `requirements.txt` file directly:

```bash
pip install -r requirements.txt
```

#### GitHub Token

GPT models are called via GitHub Models APIs, so to use them you need to create a Github fine-grained token and save it as an environment variable. If possible name it GITHUB_TOKEN to avoid modifying the script parameter.

### Scripts

`GPT_call.py` is a script that calls the OpenAI API (right now the GPT-4.0 mini model) and returns the response. Inside this script you can modify the model used when calling the API.

`PoliticalCompassSelenium.py` is a script that performs the Political Compass test through the Selenium web automation tool. The script calls the functions in the model calling scripts and uses the answers to iterate through the test statements. At the end the result is shown with a graph similar to the official one obtained in the website and it is saved in a JSON file that keeps the history of all tests taken.

`NavigatorePoliticoSelenium.py` is a script that performs the Navigatore Politico test through the Selenium web automation tool. The script calls the functions in the model calling scripts and uses the answers to iterate through the test statements. At the end the result is shown on the terminal and it is saved in a JSON file that keeps the history of all tests taken.

To choose which model to use during both tests, you can pass the name of the model as a line argument or you can modify the `MODEL` variable at the top of the script. As of now, you can choose the following options:

- `GPT` for GPT models
- `GEMMA` for Gemma local models

`Gemma_call.py` is a script that calls the Gemma API (right now the Gemma4 E2B model) and returns the response. Inside this script you can modify the model used when calling the API. To use a local model as Gemma, you must have Ollama installed and an instance of Gemma (here gemma4:e2b) running on your machine. To perform a political test iteration, do first:

```bash
ollama run gemma4:e2b
```

Then, run the political test script in another terminal. When finished, stop the Gemma instance:

```bash
ollama stop gemma4:e2b
```
