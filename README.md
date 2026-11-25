# Group_8_Intelligentsystems_Casestudy
Multi Agent NLP-to-SQL Pipeline for Manufacturing Operations: An Agentic Case Study on the Production Database

---

## Architecture & Workflow

The tool turns plain-English questions about manufacturing data into MariaDB SQL. It offers a baseline and an agent that chooses its workflow automatically.

- **Baseline** (`app/src/baseline.py`) generates SQL in one Claude call.
- **Agent** (`app/src/correction.py`) chooses among three paths.
  - **Direct** generates and executes SQL. A successful first draft takes one model call.
  - **Planned** asks the planner for a short outline, generates SQL from the question and plan, then asks the critic to review the SQL before execution.
  - **Planned after first draft** starts by generating SQL. If the draft reveals complexity, the agent makes a plan, regenerates the SQL, and sends the new draft to the critic before execution.
- **Planner** (`app/src/planner.py`) identifies relevant schema fields, filters, and rules for grouping, time boundaries, or ties.
- **Critic** (`app/src/critic.py`) reviews whether the SQL addresses the original question. Critic feedback or a database execution error can trigger one revision. The retry includes the original question, previous SQL, and feedback.
- **Evaluator** (`app/src/evaluator.py`) compares query results with the benchmark reference results and calculates execution accuracy.

## Prerequisites

- Docker Desktop with Docker Compose.
- An Anthropic API key and a Claude model for SQL generation.
- A MariaDB or MySQL database reachable from the app container. To use the bundled MariaDB service, supply the production snapshot at `data/schema/data.sql` alongside `data/schema/schema.sql`.

## Installation & Setup

Clone the repository and enter its directory.

```sh
git clone https://github.com/Chizobawisdom/Group_8_Intelligentsystems_Casestudy.git
cd Group_8_Intelligentsystems_Casestudy
```

Create `.env` from `.env.example` and set `ANTHROPIC_API_KEY` and `LLM_MODEL`.

Start the bundled database if you plan to use it.

```sh
docker compose -f Docker-Compose.yml up -d db
```

## Run the Streamlit UI

```sh
docker compose -f Docker-Compose.yml run --rm -p 8501:8501 app streamlit run src/UI.py --server.address=0.0.0.0
```

For an external database, add `--no-deps` after `--rm` to skip starting the bundled service. For custom schemas, the app can use column descriptions in `data/schema/column_descriptions.json`. The SQL generation prompt lives in `app/prompts/system_prompt.txt`.

1. Open [Streamlit](http://localhost:8501) and enter the database host, port, name, username, and password in the sidebar. Choose **Connect**. For the bundled database, use host `db`, port `3306`, and the credentials in `Docker-Compose.yml`.
2. Enter a question and select **Run Baseline (No Agent)** or **Run Agent**. With **Run Agent**, the screen shows the current step, such as **Plan**, **Generate SQL**, **Review**, or **Execute**.
3. Read the SQL and query results. Expand **Run details** for the agent path, elapsed time, and any plan or review feedback. The details show **Planning unavailable** when the planner produces no plan and **Review unavailable** when the critic produces no verdict.
4. Select **Disconnect** before connecting to a different database.

## Run the benchmark

Select **Run Full Benchmark** in Streamlit to run the 29 bundled questions against the connected database. The questions are written for the bundled manufacturing schema. The results show baseline and agent execution accuracy, total runtime, and each question's pass or fail outcome and **Agent path**.

The terminal command runs the same benchmark using the database configured for the app container.

```sh
docker compose -f Docker-Compose.yml run --rm app python src/main.py
```

The benchmark generates baseline and agent predictions independently, with up to two questions in progress at a time during each generation phase. It runs each reference query once per benchmark and reuses its result for both scores. A prediction passes when its returned rows match the reference rows regardless of order. The terminal run prints the scores and saves predictions to `data/benchmark/baseline_predictions.json` and `data/benchmark/agent_predictions.json`.

---

Developed as part of the Intelligent Systems Case Study.
