from collections.abc import Callable
from dataclasses import dataclass, replace

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
from sql_checks import check_output

AGENT_SQL_INSTRUCTIONS = """Use the original question to determine the final result.
Return only the requested values and labels needed to identify each result row.
Keep helper columns and diagnostics out of the final SELECT. Group at the requested level
without splitting rows by extra dimensions. Add filters only when required by the question,
its calculation, or the established schema rules. Do not exclude unrelated null or blank values.
Keep calculated precision unless the user asks for rounding or truncation."""

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
    validation_error: str | None = None

    def as_prediction(self) -> dict[str, str]:
        prediction = {"generated_sql": self.sql}
        if self.validation_error is not None:
            prediction["validation_error"] = self.validation_error
        return prediction


def run_agent_with_details(
    engine,
    llm,
    schema_text: str,
    question: str,
    *,
    on_stage: Callable[[str], None] | None = None,
    log: Callable[[str], None] = print,
) -> AgentRun:
    def report(stage: str) -> None:
        if on_stage is not None:
            on_stage(stage)

    def draft(request: str, *, plan: str | None = None) -> str:
        return generate_sql(llm, schema_text, request, plan=plan, instructions=AGENT_SQL_INSTRUCTIONS)

    complex_question = is_complex_question(question)
    plan = None
    if complex_question:
        report("Plan")
        plan = plan_query(llm, schema_text, question, warn=log)

    report("Generate SQL")
    sql_query = draft(question, plan=plan)
    needs_review = complex_question or is_complex_sql(sql_query)

    if needs_review and not complex_question:
        # Some questions only reveal their complexity in the first SQL draft.
        report("Plan after first draft")
        plan = plan_query(llm, schema_text, question, warn=log)
        if plan is not None:
            report("Regenerate SQL")
            sql_query = draft(question, plan=plan)

    path = "Direct"
    review = None
    if needs_review:
        if plan is None:
            path = "Planning unavailable"
        else:
            path = "Planned" if complex_question else "Planned after first draft"
        report("Review")
        review = review_sql(llm, schema_text, question, sql_query, warn=log)
        output_issues = check_output(
            sql_query, output_columns=review.output_columns, rounding_requested=review.rounding_requested
        )
        if output_issues:
            feedback_lines = [review.feedback] if review.feedback else []
            feedback_lines.extend(f"- {issue}" for issue in output_issues)
            review = replace(review, status="Revision requested", feedback="\n".join(feedback_lines))

    if review is not None and review.feedback is not None:
        log("Agent revising SQL after critic review.")
        feedback = f"Critic feedback\n{review.feedback}"
        revision = "Revision after review"
    else:
        report("Execute")
        success, error_msg = execute_sql(engine, sql_query)
        if success:
            return AgentRun(sql_query, path, plan, review)
        log("Agent retrying SQL after a database error.")
        feedback = f"Database error\n{error_msg}"
        revision = "Retry after a database error"

    correction_prompt = (
        f"Original question\n{question}\n\n"
        f"Previous SQL\n{sql_query}\n\n"
        f"{feedback}\n\n"
        "Revise the SQL to answer the original question and address every issue in the feedback. "
        "Preserve the parts that already satisfy the question. Output only the corrected SQL."
    )
    report(revision)
    revised_sql = draft(correction_prompt)
    if review is not None:
        remaining_issues = check_output(
            revised_sql, output_columns=review.output_columns, rounding_requested=review.rounding_requested
        )
        if remaining_issues:
            validation_error = " ".join(remaining_issues)
            log(f"Revised SQL failed output validation. {validation_error}")
            return AgentRun(revised_sql, path, plan, review, revision, validation_error=validation_error)
    report("Execute")
    success, error_msg = execute_sql(engine, revised_sql)
    if success:
        log("Agent successfully revised the SQL.")
    else:
        log(f"Revised SQL failed with database error {error_msg}")
    return AgentRun(revised_sql, path, plan, review, revision)


def run_correction_agent(engine, llm, schema_text, question) -> str:
    run = run_agent_with_details(engine, llm, schema_text, question)
    if run.validation_error is not None:
        raise ValueError(run.validation_error)
    return run.sql

def main(n: int | None = None) -> None:
    engine = get_engine()
    try:
        llm = build_llm()
        schema_text = get_schema_text()
        predictions = generate_predictions(
            load_questions()[:n],
            lambda question: run_agent_with_details(engine, llm, schema_text, question).as_prediction(),
        )
        save_predictions(AGENT_PREDICTIONS, predictions)
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
