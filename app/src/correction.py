from sqlalchemy import text

from connect import get_engine
from baseline import (
    build_llm,
    generate_predictions,
    generate_sql,
    get_schema_text,
    load_questions,
    save_predictions,
)
from evaluator import AGENT_PREDICTIONS

def execute_sql(engine, query):
    try:
        with engine.connect() as conn:
            conn.execute(text(query))
        return True, "Success"
    except Exception as e:
        return False, str(e)

def run_correction_agent(engine, llm, schema_text, question):
    # 1. First Attempt
    sql_query = generate_sql(llm, schema_text, question)
    
    # 2. Execute & Validate
    success, error_msg = execute_sql(engine, sql_query)
    
    # 3. If it fails, ask the LLM to fix it!
    if not success:
        print(f"⚠️ First attempt failed for question: {question[:30]}...")
        print(f"   Error: {error_msg}")
        print("   🔄 Agent is attempting to self-correct...")
        
        correction_prompt = f"""
        The SQL query you wrote failed with this database error:
        {error_msg}
        
        Here was your query:
        {sql_query}
        
        Please fix the query and output ONLY the corrected SQL.
        """
        
        # Call the LLM again with the error context
        sql_query = generate_sql(llm, schema_text, correction_prompt)
        success, error_msg = execute_sql(engine, sql_query)
        
        if success:
            print("   ✅ Agent successfully corrected the SQL!")
        else:
            print(f"   ❌ Agent failed again: {error_msg}")
            
    return sql_query

def main(n: int | None = None) -> None:
    engine = get_engine()
    try:
        llm = build_llm()
        schema_text = get_schema_text()
        predictions = generate_predictions(
            load_questions()[:n],
            lambda question: run_correction_agent(engine, llm, schema_text, question),
        )
        save_predictions(AGENT_PREDICTIONS, predictions)
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
