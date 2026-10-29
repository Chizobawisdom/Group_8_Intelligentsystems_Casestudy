# Group_8_Intelligentsystems_Casestudy
Multi Agent NLP-to-SQL Pipeline for Manufacturing Operations: An Agentic Case Study on the Production Database

---

## Architecture & Workflow
The pipeline is fully Dockerized and consists of the following components:
 - MariaDB: Hosts the production database (nlp2sql).
 - Baseline (baseline.py): A single LLM call using LangChain and Claude to generate SQL.
 - Agent (correction.py): An agentic loop that executes the generated SQL, catches syntax errors, feeds the error back to the LLM, and self-corrects.
 - Evaluator (evaluator.py): Executes both the generated and "Gold" SQL, compares the results, and calculates Execution Accuracy.
 - Streamlit UI (ui.py): A frontend to interactively test questions against the database.

## Prerequisites
 - Docker Desktop installed and running.
 - An Anthropic API Key (for Claude)
 - Production DB sql snapshot as data/schema/data.sql
    - If the Production DB is replaced, the column_descriptions.json should also be updated to match the new data
    - The prompt can also be updated to match the new SQL query
 - Production DB sql schema as data/schema/schema.sql
 - To use a live sql server, replace the server details in the Docker-Compose.yml file

## Installation & Setup
 - Clone the repository with the terminal: git clone https://github.com/Chizobawisdom/Group_8_Intelligentsystems_Casestudy.git
                          cd Group_8_Intelligentsystems_Casestudy
 - Create a .env file in the root directory and add your API key using the .env.example
 - Start the database in the cloned repository with the terminal: docker-compose up -d db

## Running the Pipeline
 - To run the entire automated workflow (Baseline → Agent → Evaluation) using the benchmark test questions : docker-compose run --rm app python src/main.py
 - To launch the interactive Streamlit UI and ask new questions: docker-compose run --rm -p 8501:8501 app streamlit run src/ui.py --server.address=0.0.0.0
    - Open http://localhost:8501 in your browser.

## Results
 - Baseline Accuracy: 78.95%
 - Agent Accuracy: 89.47%

---

Developed as part of the Intelligent Systems Case Study.
