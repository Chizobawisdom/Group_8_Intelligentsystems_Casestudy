import logging

from baseline import response_text

logger = logging.getLogger(__name__)

PLANNER_PROMPT = """Create a brief plan for answering the original question with MariaDB.
Use the supplied schema. State the needed tables and columns, filters and time boundaries,
what each output row represents, and any required joins, aggregates, or checks for blanks and ties.
Mention missing schema information if it prevents answering the question.
Return at most five concise bullets of implementation guidance. Do not write SQL."""


def plan_query(llm, schema_text: str, question: str) -> str | None:
    messages = [
        ("system", PLANNER_PROMPT),
        ("human", f"Original question\n{question}\n\nDatabase schema\n{schema_text}"),
    ]
    try:
        plan = response_text(llm.invoke(messages).content).strip()
    except Exception as exc:
        logger.warning("SQL planner unavailable (%s); using direct SQL generation.", type(exc).__name__)
        return None

    if not plan:
        logger.warning("SQL planner returned an empty plan; using direct SQL generation.")
        return None
    return plan
