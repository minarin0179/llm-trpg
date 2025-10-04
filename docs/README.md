# Multi-Agent TRPG Game Master System


## Directory Structure
.
├── character : Character sheets
├── rulebook : Rulebooks
├── scenario : Scenarios
└── src : Main source code

## Setup Instructions
### 1. Creating a Virtual Environment
Supports Github Codespace and Devcontainer


Open in [Codespace](https://github.com/codespaces/new/minarin0179/llm-trpg?quickstart=1) in your browser (works within the free tier)
![alt text](images/codespace.png)

Initial startup takes time as setup runs

### 2. Environment Variable Configuration
Copy .env.sample to .env and modify it
```bash
cp src/.env.sample src/.env
```

Set OPENAI_API_KEY in .env
```
OPENAI_API_KEY=(paste your API key here)
BCDICE_API_URL="https://bcdice.onlinesession.app"
```

## Usage Instructions
Execute with the following command or `run.sh`
```bash
streamlit run src/app.py
```
