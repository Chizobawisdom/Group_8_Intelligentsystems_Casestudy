import json
from pathlib import Path
from sqlalchemy import text
from langchain_anthropic import ChatAnthropic

from connect import get_engine
from get_schema import add_sample_values, format_for_prompt, get_schema
from baseline import build_llm, generate_sql, SYSTEM_PROMPT, get_schema_text

QUESTIONS = Path("data/benchmark/questions.jsonl")

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

def main(n: int = None):
    engine = get_engine()
    llm = build_llm()
    schema_text = get_schema_text()
    
    with QUESTIONS.open(encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()]
        
    results = []
    
    # If n is None, run all questions
    for item in items[:n]:
        print(f"Processing Q{item['id']}: {item['question']}")
        
        # Run the agent loop
        generated_sql = run_correction_agent(engine, llm, schema_text, item["question"])
        
        results.append({
            "id": item["id"],
            "question": item["question"],
            "gold_sql": item["gold_sql"],
            "generated_sql": generated_sql
        })
        print()
    
    # Save the agent's output for the evaluator
    output_path = Path("data/benchmark/agent_predictions.json")
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"✅ Saved agent predictions to {output_path}")

if __name__ == "__main__":
    main()