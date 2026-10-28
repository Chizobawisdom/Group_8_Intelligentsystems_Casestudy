"""Baseline: a single LLM call with the full schema in the prompt.
The LLM is chosen via environment variables (LLM_PROVIDER, LLM_MODEL), not in code.
"""
import json
import os
import re
from pathlib import Path

from langchain_anthropic import ChatAnthropic

from connect import get_engine
from get_schema import add_sample_values, format_for_prompt, get_schema, load_descriptions

QUESTIONS = Path("data/benchmark/questions.jsonl")

SYSTEM_PROMPT = """You are an expert MariaDB analyst.
Write exactly ONE SQL query that answers the user's question.

Rules:
- Use only the table and columns listed in the schema below.
- Output a single SELECT statement. Never modify data.
- Many columns are stored as VARCHAR, so compare them with quoted strings (for example aktion = '29').
- The data ends on 2026-07-16; treat that date as "today". Dates before the year 2000 (for example 0001-01-01) are placeholders.
- Return only the SQL. No explanation and no markdown.

Important Data Rules:
- Cycle Time (DLZ): To calculate time differences, use `TIMESTAMPDIFF(MINUTE, azeit, bzeit)`. If `bzeit` < `azeit`, the process crossed midnight. You must add 24 hours to the end time.
- First Record: To find the first record for a serial number on a day, use `MIN(CONCAT(datum, ' ', azeit))`.
- Not Exists: If asked for units that never reached a step, use `NOT EXISTS (SELECT 1 FROM ...)`.
- Distinct Units: "How many units/serials" always means `COUNT(DISTINCT serial)`.

Schema:
{schema}
"""


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