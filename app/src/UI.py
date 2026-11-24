import os

import pandas as pd
import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from connect import create_database_engine
from baseline import build_llm, generate_sql, get_schema_text
from correction import run_correction_agent
from main import main as run_benchmark

st.set_page_config(page_title="Agentic NLP to SQL Agent", page_icon="🤖", layout="wide")

st.title("🤖 Agentic NLP-to-SQL Agent")
st.markdown("Ask a question in plain English, and the AI Agent will generate and execute the SQL.")

@st.cache_resource
def load_llm():
    return build_llm()


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
    st.rerun()

# Create the UI layout
user_question = st.text_input("Enter your question:", placeholder="e.g., How many records were logged on 2026-07-15?")

col1, col2 = st.columns(2)
run_baseline_btn = col1.button("Run Baseline (No Agent)")
run_agent_btn = col2.button("Run Agent (Self-Correction)")

if run_baseline_btn or run_agent_btn:
    if not user_question:
        st.warning("Please enter a question first.")
    else:
        with st.spinner("Thinking..."):
            llm = load_llm()
            if run_baseline_btn:
                st.subheader("Baseline SQL")
                sql_query = generate_sql(llm, schema_text, user_question)
                st.code(sql_query, language="sql")
            
            elif run_agent_btn:
                st.subheader("Agent SQL")
                # We use st.empty() to show the agent thinking in real-time
                status_container = st.empty()
                
                # Note: To see the print statements from your agent in Streamlit, 
                # we'd normally need to modify the agent to use st.write(). 
                # For now, it will just run silently and return the result.
                sql_query = run_correction_agent(engine, llm, schema_text, user_question)
                
                st.code(sql_query, language="sql")

        # Execute the final SQL to show the data
        st.subheader("Query Results")
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql_query))
                rows = result.fetchall()
                
                if rows:
                    # Convert to a Pandas DataFrame for a beautiful table
                    df = pd.DataFrame(rows, columns=result.keys())
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("The query returned no results.")
                    
        except Exception as e:
            st.error(f"❌ SQL Execution Error:\n{e}")

st.subheader("Benchmark")
st.caption("Runs the bundled benchmark questions against the connected database.")

if st.button("Run Full Benchmark"):
    st.session_state.pop("benchmark_result", None)
    with st.spinner("Running the baseline, agent, and evaluation..."):
        try:
            st.session_state.benchmark_result = run_benchmark(
                engine, llm=load_llm(), schema_text=schema_text
            )
        except Exception:
            st.error("The benchmark could not finish. Check the database and model settings, then try again.")

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
