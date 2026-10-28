import streamlit as st
import pandas as pd
from sqlalchemy import text
from connect import get_engine
from baseline import build_llm, generate_sql, get_schema_text
from correction import run_correction_agent

st.set_page_config(page_title="Agentic NLP to SQL Agent", page_icon="🤖", layout="wide")

st.title("🤖 Agentic NLP-to-SQL Agent")
st.markdown("Ask a question in plain English, and the AI Agent will generate and execute the SQL.")

# Initialize resources (cache them so they don't reload on every button click)
@st.cache_resource
def load_resources():
    engine = get_engine()
    llm = build_llm()
    schema_text = get_schema_text()
    return engine, llm, schema_text

engine, llm, schema_text = load_resources()

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