import logging
from collections.abc import Callable
from dataclasses import dataclass

from baseline import response_text

logger = logging.getLogger(__name__)

CRITIC_PROMPT = """Review the proposed MariaDB SQL against the original question and schema.
Check the requested filters, date boundaries, grouping, distinct counts, event ordering,
and handling of blank values and ties. Accept equivalent SQL formulations.
If the schema lacks required information, accept a query that reports insufficient schema information.
Reply exactly APPROVE if the SQL answers the question.
Otherwise reply REVISE: followed by one concrete issue and the needed change.
Return only the verdict and any feedback."""


@dataclass(frozen=True)
class SQLReview:
    status: str
    feedback: str | None = None


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

    if verdict.upper() == "APPROVE":
        return SQLReview("No issues flagged")
    label, separator, issue = verdict.partition(":")
    if label.strip().upper() == "REVISE" and separator and issue.strip():
        return SQLReview("Revision requested", issue.strip())

    warn("SQL critic returned an invalid verdict. Using database validation.")
    return SQLReview("Review unavailable")
