# Group_8_Intelligentsystems_Casestudy
Multi Agent NLP-to-SQL Pipeline for Manufacturing Operations: An Agentic Case Study on the Production Database

---

## Architecture & Workflow
The pipeline is fully Dockerized and consists of the following components:
 - MariaDB: Hosts the production database (nlp2sql).
 - Baseline (baseline.py): A single LLM call using LangChain and Claude to generate SQL.
 - Agent (correction.py): An agentic loop that executes the generated SQL, catches syntax errors, feeds the error back to the LLM, and self-corrects.
 - Evaluator (evaluator.py): Executes both the generated and "Gold" SQL, compares the results, and calculates Execution Accuracy.
 - Streamlit UI (UI.py): A frontend to interactively test questions against a database selected in the sidebar.

## Prerequisites
 - Docker Desktop installed and running.
 - An Anthropic API Key (for Claude)
 - Production DB sql snapshot as data/schema/data.sql
    - If the Production DB is replaced, the column_descriptions.json should also be updated to match the new data
    - The prompt can also be updated to match the new SQL query
 - Production DB sql schema as data/schema/schema.sql

## Installation & Setup
 - Clone the repository with the terminal: git clone https://github.com/Chizobawisdom/Group_8_Intelligentsystems_Casestudy.git
                          cd Group_8_Intelligentsystems_Casestudy
 - Create a .env file in the root directory and add your API key using the .env.example
 - If using the bundled database, start it with `docker-compose up -d db`.

## Running the Pipeline
 - To run the entire automated workflow (Baseline → Agent → Evaluation) using the benchmark test questions : docker-compose run --rm app python src/main.py
 - Launch the interactive Streamlit UI with `docker-compose run --rm -p 8501:8501 app streamlit run src/UI.py --server.address=0.0.0.0`.
    - If using an external MariaDB or MySQL server, add `--no-deps` after `--rm` to skip starting the bundled database.
    - Open http://localhost:8501 and enter the host, port, database name, username, and password in the sidebar. Select **Connect** to load the schema and start asking questions.
    - For the bundled database, use host `db`, port `3306`, and the database credentials from the Compose configuration.
    - To switch databases, select **Disconnect** and connect with the new details.
    - Select **Run Full Benchmark** to run the bundled questions against the connected database and see both accuracy scores and per-question results. The questions use the bundled manufacturing schema.

## Results
 - Baseline Accuracy: 78.95%
 - Agent Accuracy: 89.47%

---

Developed as part of the Intelligent Systems Case Study.
