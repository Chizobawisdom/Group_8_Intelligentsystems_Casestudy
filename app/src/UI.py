import os
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from time import perf_counter

import pandas as pd
import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from connect import create_database_engine
from baseline import build_llm, generate_sql, get_schema_text
from correction import run_agent_with_details
from main import BenchmarkResult
from main import main as run_benchmark

st.set_page_config(page_title="Agentic NLP to SQL Artefact", page_icon="🤖", layout="wide")

st.title("🤖 Agentic NLP-to-SQL Artefact")
st.markdown("Ask a question in plain English, and the AI Agent will generate and execute the SQL.")

@st.cache_resource
def load_llm():
    return build_llm()


def show_query_results(engine, sql_query: str) -> None:
    st.subheader("Query Results")
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            rows = result.fetchall()
            if rows:
                df = pd.DataFrame(rows, columns=result.keys())
                st.dataframe(df, use_container_width=True)
            else:
                st.info("The query returned no results.")
    except Exception as exc:
        st.error(f"❌ SQL Execution Error:\n{exc}")


def stream_benchmark_output(engine, llm, schema_text: str, lines: list[str], panel) -> BenchmarkResult:
    messages: Queue[str | None] = Queue()

    def run() -> BenchmarkResult:
        try:
            return run_benchmark(engine, llm=llm, schema_text=schema_text, log=messages.put)
        finally:
            messages.put(None)

    # Benchmark workers enqueue text. The Streamlit script thread renders the panel.
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run)
        while (message := messages.get()) is not None:
            lines.extend(message.split("\n"))
            panel.code("\n".join(lines[-14:]), language=None)
        return future.result()


st.sidebar.header("Database connection")
connection = st.session_state.get("database_connection")

if connection is None:
    with st.sidebar.form("database_connection_form"):
        host = st.text_input("Host", value=os.getenv("DB_HOST", ""))
        port_input = st.text_input("Port", value=os.getenv("DB_PORT", "3306"))
        database = st.text_input("Database", value=os.getenv("DB_NAME", ""))
        username = st.text_input("Username", value=os.getenv("DB_USER", ""))
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Connect")

    if submitted:
        host, database, username = host.strip(), database.strip(), username.strip()
        if not (host and database and username):
            st.sidebar.error("Enter a host, database name, and username.")
            st.stop()

        try:
            port = int(port_input)
        except ValueError:
            port = 0
        if not 1 <= port <= 65535:
            st.sidebar.error("Enter a port number between 1 and 65535.")
            st.stop()

        with st.spinner("Connecting and loading the database schema..."):
            engine = create_database_engine(
                host=host, port=port, database=database, username=username, password=password
            )
            try:
                schema_text = get_schema_text(engine)
            except SQLAlchemyError:
                engine.dispose()
                st.sidebar.error(
                    "Could not connect or load the schema. Check the connection details "
                    "and confirm that the account can read the database."
                )
                st.stop()

        st.session_state.database_connection = (engine, schema_text)
        st.rerun()

    st.info("Connect to a database using the sidebar to start asking questions.")
    st.stop()

engine, schema_text = connection
st.sidebar.success("Connected")
st.sidebar.text(f"{engine.url.host}:{engine.url.port}/{engine.url.database}")

if st.sidebar.button("Disconnect"):
    engine.dispose()
    del st.session_state.database_connection
    st.session_state.pop("benchmark_result", None)
    st.session_state.pop("benchmark_output", None)
    st.rerun()

# Create the UI layout
user_question = st.text_input("Enter your question:", placeholder="e.g., How many records were logged on 2026-07-15?")

col1, col2 = st.columns(2)
run_baseline_btn = col1.button("Run Baseline (No Agent)")
run_agent_btn = col2.button("Run Agent")
col2.caption("Plans and reviews complex questions automatically.")

if (run_baseline_btn or run_agent_btn) and not user_question:
    st.warning("Please enter a question first.")
elif run_baseline_btn:
    with st.spinner("Generating baseline SQL..."):
        sql_query = generate_sql(load_llm(), schema_text, user_question)
    st.subheader("Baseline SQL")
    st.code(sql_query, language="sql")
    show_query_results(engine, sql_query)
elif run_agent_btn:
    started_at = perf_counter()
    progress = st.empty()

    def show_stage(stage: str) -> None:
        progress.info(f"{stage}…")

    try:
        agent_run = run_agent_with_details(
            engine, load_llm(), schema_text, user_question,
            on_stage=show_stage,
        )
    except Exception:
        progress.empty()
        st.error("The agent could not finish. Check the database and model settings, then try again.")
    else:
        st.subheader("Agent SQL")
        st.code(agent_run.sql, language="sql")
        if agent_run.validation_error is not None:
            st.error(f"The revised SQL still fails output validation. {agent_run.validation_error}")
        else:
            show_query_results(engine, agent_run.sql)
        progress.empty()

        with st.expander("Run details", expanded=False):
            st.caption(f"{agent_run.path} · {perf_counter() - started_at:.1f} seconds")
            if agent_run.plan is not None:
                st.markdown("**Plan**")
                st.markdown(agent_run.plan)
            if agent_run.review is not None:
                st.markdown(f"**Review** · {agent_run.review.status}")
                if agent_run.review.feedback is not None:
                    st.write(agent_run.review.feedback)
            if agent_run.revision is not None:
                st.caption(agent_run.revision)

st.subheader("Benchmark")
st.caption("Runs the bundled benchmark questions against the connected database.")

run_full_benchmark = st.button("Run Full Benchmark")
if run_full_benchmark:
    st.session_state.pop("benchmark_result", None)
    st.session_state.benchmark_output = []

benchmark_output = st.session_state.get("benchmark_output")
if benchmark_output is not None:
    st.subheader("Benchmark output")
    with st.container(height=320):
        log_panel = st.empty()
    if run_full_benchmark:
        log_panel.code("Starting benchmark...", language=None)
        try:
            st.session_state.benchmark_result = stream_benchmark_output(
                engine, load_llm(), schema_text, benchmark_output, log_panel
            )
        except Exception:
            st.error("The benchmark could not finish. Check the database and model settings, then try again.")
    log_panel.code("\n".join(benchmark_output) or "No benchmark output.", language=None)

benchmark_result = st.session_state.get("benchmark_result")
if benchmark_result is not None:
    elapsed_seconds = getattr(benchmark_result, "elapsed_seconds", None)
    if elapsed_seconds is not None:
        st.caption(f"Benchmark runtime {elapsed_seconds:.1f} seconds")
    baseline_score, agent_score = st.columns(2)
    baseline_score.metric("Baseline accuracy", f"{benchmark_result.baseline_accuracy:.2f}%")
    agent_score.metric(
        "Agent accuracy",
        f"{benchmark_result.agent_accuracy:.2f}%",
        delta=f"{benchmark_result.agent_accuracy - benchmark_result.baseline_accuracy:+.2f} pp",
    )
    st.dataframe(pd.DataFrame(benchmark_result.question_results), hide_index=True)
