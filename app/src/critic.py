import json
import logging
from collections.abc import Callable
from dataclasses import dataclass

from baseline import response_text

logger = logging.getLogger(__name__)

CRITIC_PROMPT = """Review the proposed MariaDB SQL against the original question and schema.
First derive the expected output columns, row grain, qualifying records, and precision directly
from the original question. Then compare the SQL with those requirements.
Flag extra or missing final output columns, extra grouping keys that change what a row represents,
filters that exclude records without a reason in the question, and rounding the user did not request.
Check date boundaries, distinct counts, event ordering, blanks, and ties when relevant.
Accept equivalent SQL and helper fields, grouping, and filters in intermediate queries when they
implement the requested result. Exclude placeholder dates before 2000-01-01 unless explicitly
requested. Keep unrelated null and blank values in the result population.
When the schema is insufficient, accept a query that reports insufficient schema information.

Return only a JSON object with these fields:
- "output_columns": an array of final column descriptions, with one item per requested column.
  Use null if the column count is unclear, all columns are requested, or the schema is insufficient.
- "rounding_requested": true if the question asks for rounding, truncation, or a fixed precision.
  Use false when it asks for the calculated value without a precision restriction. Use null
  when the intended precision is ambiguous or the schema is insufficient.
- "issues": an array of concise strings. Include every confirmed mismatch and its needed change.
  Use an empty array when the SQL satisfies the question."""


@dataclass(frozen=True)
class SQLReview:
    status: str
    feedback: str | None = None
    output_columns: tuple[str, ...] | None = None
    rounding_requested: bool | None = None


def parse_review(verdict: str) -> SQLReview | None:
    if verdict.startswith("```") and verdict.endswith("```"):
        verdict = verdict.partition("\n")[2][:-3].strip()
    try:
        payload = json.loads(verdict)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None

    issues = payload.get("issues")
    if not isinstance(issues, list) or any(
        not isinstance(issue, str) or not issue.strip() for issue in issues
    ):
        return None

    columns = payload.get("output_columns")
    output_columns = None
    if isinstance(columns, list) and columns:
        if all(isinstance(column, str) and column.strip() for column in columns):
            output_columns = tuple(column.strip() for column in columns)
    rounding = payload.get("rounding_requested")
    feedback = "\n".join(f"- {issue.strip()}" for issue in issues) or None
    return SQLReview(
        status="Revision requested" if feedback else "No issues flagged",
        feedback=feedback,
        output_columns=output_columns,
        rounding_requested=rounding if isinstance(rounding, bool) else None,
    )


def review_sql(
    llm, schema_text: str, question: str, sql_query: str, *, warn: Callable[[str], None] = logger.warning
) -> SQLReview:
    review_input = (
        f"Original question\n{question}\n\n"
        f"Database schema\n{schema_text}\n\n"
        f"Proposed SQL\n{sql_query}"
    )
    messages = [
        ("system", CRITIC_PROMPT),
        ("human", review_input),
    ]
    try:
        verdict = response_text(llm.invoke(messages).content).strip()
    except Exception as exc:
        warn(f"SQL critic unavailable ({type(exc).__name__}). Using database validation.")
        return SQLReview("Review unavailable")

    review = parse_review(verdict)
    if review is not None:
        return review

    warn("SQL critic returned an invalid verdict. Using database validation.")
    return SQLReview("Review unavailable")
