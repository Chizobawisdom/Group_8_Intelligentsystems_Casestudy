from collections.abc import Callable
from dataclasses import dataclass

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
from critic import SQLReview, review_sql
from evaluator import AGENT_PREDICTIONS
from planner import plan_query
from query_complexity import is_complex_question, is_complex_sql

def execute_sql(engine, query):
    try:
        with engine.connect() as conn:
            conn.execute(text(query))
        return True, "Success"
    except Exception as e:
        return False, str(e)

@dataclass(frozen=True)
class AgentRun:
    sql: str
    path: str
    plan: str | None
    review: SQLReview | None
    revision: str | None = None


def run_agent_with_details(
    engine, llm, schema_text: str, question: str, *, on_stage: Callable[[str], None] | None = None
) -> AgentRun:
    def report(stage: str) -> None:
        if on_stage is not None:
            on_stage(stage)

    complex_question = is_complex_question(question)
    plan = None
    if complex_question:
        report("Plan")
        plan = plan_query(llm, schema_text, question)

    report("Generate SQL")
    sql_query = generate_sql(llm, schema_text, question, plan=plan)
    needs_review = complex_question or is_complex_sql(sql_query)

    if needs_review and not complex_question:
        # Some questions only reveal their complexity in the first SQL draft.
        report("Plan after first draft")
        plan = plan_query(llm, schema_text, question)
        if plan is not None:
            report("Regenerate SQL")
            sql_query = generate_sql(llm, schema_text, question, plan=plan)

    path = "Direct"
    review = None
    if needs_review:
        if plan is None:
            path = "Planning unavailable"
        else:
            path = "Planned" if complex_question else "Planned after first draft"
        report("Review")
        review = review_sql(llm, schema_text, question, sql_query)

    if review is not None and review.feedback is not None:
        print("Agent revising SQL after critic review.")
        feedback = f"Critic feedback\n{review.feedback}"
        revision = "Revision after review"
    else:
        report("Execute")
        success, error_msg = execute_sql(engine, sql_query)
        if success:
            return AgentRun(sql_query, path, plan, review)
        print("Agent retrying SQL after a database error.")
        feedback = f"Database error\n{error_msg}"
        revision = "Retry after a database error"

    correction_prompt = (
        f"Original question\n{question}\n\n"
        f"Previous SQL\n{sql_query}\n\n"
        f"{feedback}\n\n"
        "Revise the SQL to answer the original question and address the feedback. "
        "Output only the corrected SQL."
    )
    report(revision)
    revised_sql = generate_sql(llm, schema_text, correction_prompt)
    report("Execute")
    success, error_msg = execute_sql(engine, revised_sql)
    if success:
        print("Agent successfully revised the SQL.")
    else:
        print(f"Revised SQL failed with database error {error_msg}")
    return AgentRun(revised_sql, path, plan, review, revision)


def run_correction_agent(engine, llm, schema_text, question) -> str:
    return run_agent_with_details(engine, llm, schema_text, question).sql

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
