"""Baseline: a single LLM call with the full schema in the prompt.
The LLM is chosen via environment variables (LLM_PROVIDER, LLM_MODEL), not in code.
"""
import json
import os
import re
from pathlib import Path
from prompter import load_prompt
from langchain_anthropic import ChatAnthropic
from connect import get_engine
from get_schema import add_sample_values, format_for_prompt, get_schema, load_descriptions

QUESTIONS = Path("data/benchmark/questions.jsonl")
SYSTEM_PROMPT = load_prompt("baseline_system_prompt.txt")

def build_llm():
    return ChatAnthropic(model=os.environ["LLM_MODEL"], max_tokens=1024)


def get_schema_text() -> str:
    engine = get_engine()
    cache = Path("/tmp/schema_cache_nlp2sql.json") 
    if cache.exists():
        schema = json.loads(cache.read_text(encoding="utf-8"))
    else:
        schema = add_sample_values(engine, get_schema(engine))  # all tables of the connected DB
        cache.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    return format_for_prompt(schema, load_descriptions())


def _to_text(content) -> str:
    """Some providers return a list of content blocks instead of a plain string."""
    if isinstance(content, str):
        return content
    return "".join(
        part.get("text", "") if isinstance(part, dict) else str(part) for part in content
    )


def extract_sql(text: str) -> str:
    """Strip markdown fences and any chatty text before the SQL starts."""
    # 1. Remove markdown fences if they exist
    match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    sql = match.group(1) if match else text
    
    # 2. Find the first instance of SELECT or WITH and cut everything before it
    match_sql = re.search(r"(?i)\b(SELECT|WITH)\b", sql)
    if match_sql:
        sql = sql[match_sql.start():]
        
    return sql.strip().rstrip(";") + ";"


def generate_sql(llm, schema_text: str, question: str) -> str:
    messages = [
        ("system", SYSTEM_PROMPT.format(schema=schema_text)),
        ("human", question),
    ]
    return extract_sql(_to_text(llm.invoke(messages).content))


def main(n: int = None) -> None:
    llm = build_llm()
    schema_text = get_schema_text()
    with QUESTIONS.open(encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()]
    
    results = []
    # If n is None, run all questions
    for item in items[:n]:
        print(f"Processing Q{item['id']}...")
        generated_sql = generate_sql(llm, schema_text, item["question"])
        results.append({
            "id": item["id"],
            "question": item["question"],
            "gold_sql": item["gold_sql"],
            "generated_sql": generated_sql
        })
    
    # Save to a file for the evaluator to read
    Path("data/benchmark/baseline_predictions.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print("Saved predictions to data/benchmark/baseline_predictions.json")


if __name__ == "__main__":
    main()