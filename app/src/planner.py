import logging
from collections.abc import Callable

from baseline import response_text

logger = logging.getLogger(__name__)

PLANNER_PROMPT = """Create a brief plan for answering the original question with MariaDB.
Use the supplied schema. State the needed tables and columns, filters and time boundaries,
what each output row represents, and any required joins, aggregates, or checks for blanks and ties.
Mention missing schema information if it prevents answering the question.
Return at most five concise bullets of implementation guidance. Do not write SQL."""


def plan_query(
    llm, schema_text: str, question: str, *, warn: Callable[[str], None] = logger.warning
) -> str | None:
    messages = [
        ("system", PLANNER_PROMPT),
        ("human", f"Original question\n{question}\n\nDatabase schema\n{schema_text}"),
    ]
    try:
        plan = response_text(llm.invoke(messages).content).strip()
    except Exception as exc:
        warn(f"SQL planner unavailable ({type(exc).__name__}). Using direct SQL generation.")
        return None

    if not plan:
        warn("SQL planner returned an empty plan. Using direct SQL generation.")
        return None
    return plan
