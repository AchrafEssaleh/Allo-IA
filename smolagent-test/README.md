# Smolagent Prototype for Documentation Genereation

This simple test code uses **smolagents** to build an AI agent that generates structured technical documentation from project descriptions. The agent connects to the ILaaS API to access a language model and can use tools such as web search to enrich the generated documentation.

## Project files

### `main.py` – Smolagent implementation

Contains the main documentation agent implementation.

- Initializes the LLM using `OpenAIModel` and the ILaaS API.
- Defines the agent and its available tools.
- Processes project descriptions and generates structured technical documentation.
- Exports the generated documentation into the desired formats.

The model is selected through the `ILAAS_MODEL_ID` constant:

```python
ILAAS_MODEL_ID = "qwen-3.6-35b-instruct"
```

To use a different model, simply change this value to another model ID available through ILaaS (a list of the available model is given by the `test_ilaas.py` file). The selected model is then used by the agent.

### `test_ilaas.py` – ILaaS API test

A standalone script used to test the ILaaS API independently of the smolagents implementation.

- Tests API authentication using the API key.
- Retrieves and displays the available model IDs.
- Sends a test request to the selected model to check whether it responds successfully.

To test a specific model, change the `model_id` in the script before running it. This allows you to check different models without modifying the main agent.

For example, `qwen-3.6-35b-instruct` was successfully tested, while `gemma-4-31b` did not work with the current API setup.

### `project_description.txt` – Input example

Contains an example project description used as input for the documentation agent.

It can be edited or replaced with another project description to test the agent with different projects.

### `output/` – Generated documentation

Contains the documentation files generated from `project_description.txt`.

These outputs provide an example of the agent's current results and can be used to evaluate the quality and structure of the generated documentation.

## Setup

1. Create and activate a Python virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install the project dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set the ILaaS API key as an enviroment variable in your terminal:

   ```bash
   export ILAAS_API_KEY="the api key given by mr Baptiste for the inference service"
   ```

## Running the project

Run the documentation agent:

```bash
python main.py project_description.txt
```

Test the ILaaS API and show the available models:

```bash
python test_ilaas.py
```

## Configuration and security

The current model configuration is:

```python
ILAAS_MODEL_ID = "qwen-3.6-35b-instruct"
```

The API key is read from the `ILAAS_API_KEY` environment variable rather than being hardcoded in the source code.

**Important:** Never commit API keys or other secrets to the repository.