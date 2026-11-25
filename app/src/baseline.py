"""Baseline: a single LLM call with the full schema in the prompt.
The LLM is chosen via environment variables (LLM_PROVIDER, LLM_MODEL), not in code.
"""
import json
import os
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from prompter import load_prompt
from langchain_anthropic import ChatAnthropic
from sqlalchemy.engine import Engine
from connect import get_engine
from evaluator import BASELINE_PREDICTIONS
from get_schema import add_sample_values, format_for_prompt, get_schema, load_descriptions

QUESTIONS = Path("data/benchmark/questions.jsonl")
SYSTEM_PROMPT = load_prompt("system_prompt.txt")

def build_llm():
    return ChatAnthropic(model=os.environ["LLM_MODEL"], max_tokens=1024)


def get_schema_text(engine: Engine | None = None) -> str:
    cache = Path("/tmp/schema_cache_nlp2sql.json") if engine is None else None
    if cache is not None and cache.exists():
        schema = json.loads(cache.read_text(encoding="utf-8"))
    else:
        if engine is None:
            engine = get_engine()
        schema = add_sample_values(engine, get_schema(engine))
        if cache is not None:
            cache.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    return format_for_prompt(schema, load_descriptions())


def response_text(content) -> str:
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


def generate_sql(llm, schema_text: str, question: str, *, plan: str | None = None) -> str:
    request = question
    if plan is not None:
        request = (
            f"Original question\n{question}\n\n"
            f"Proposed query plan\n{plan}\n\n"
            "Use the plan as guidance and answer the original question."
        )
    messages = [
        ("system", SYSTEM_PROMPT.format(schema=schema_text)),
        ("human", request),
    ]
    return extract_sql(response_text(llm.invoke(messages).content))


def load_questions() -> list[dict]:
    with QUESTIONS.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def generate_predictions(
    items: list[dict], predict_sql: Callable[[str], str | dict[str, str]], *, max_workers: int = 1
) -> list[dict]:
    def predict_item(item: dict) -> dict:
        print(f"Processing Q{item['id']}...")
        prediction = predict_sql(item["question"])
        if isinstance(prediction, str):
            prediction = {"generated_sql": prediction}
        return {
            "id": item["id"],
            "question": item["question"],
            "gold_sql": item["gold_sql"],
            **prediction,
        }

    if max_workers == 1:
        return [predict_item(item) for item in items]

    executor = ThreadPoolExecutor(max_workers=max_workers)
    try:
        return list(executor.map(predict_item, items))
    finally:
        executor.shutdown(cancel_futures=True)


def save_predictions(path: Path, predictions: list[dict]) -> None:
    path.write_text(json.dumps(predictions, indent=2), encoding="utf-8")
    print(f"Saved predictions to {path.as_posix()}")


def main(n: int | None = None) -> None:
    llm = build_llm()
    schema_text = get_schema_text()
    predictions = generate_predictions(
        load_questions()[:n], lambda question: generate_sql(llm, schema_text, question)
    )
    save_predictions(BASELINE_PREDICTIONS, predictions)


if __name__ == "__main__":
    main()
