import logging
from collections.abc import Callable

from baseline import response_text

logger = logging.getLogger(__name__)

PLANNER_PROMPT = """Create a brief plan for answering the original question with MariaDB.
Use the supplied schema and give four labeled bullets.
- Output columns: List the requested values and labels needed to identify each result row.
- Row grain: State what one final row represents and which grouping keys it needs.
- Qualifying records: State the required filters, joins, time boundaries, and missing-value rules.
- Precision: State the requested rounding or preserve the calculated precision.
Use the question as the source of these requirements. Keep helper fields and grouping inside
intermediate queries when they are needed. Include only filters that implement the question or
the established schema rules. Exclude placeholder dates before 2000-01-01 unless explicitly
requested.
Mention missing schema information if it prevents answering the question.
Keep the bullets concise. Do not write SQL."""


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
