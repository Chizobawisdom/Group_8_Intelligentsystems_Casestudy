from collections.abc import Iterator

from sqlglot import exp, parse_one
from sqlglot.errors import SqlglotError


def final_selects(query: exp.Expression) -> Iterator[exp.Select]:
    """Yield only SELECTs that determine the final result, including set-operation branches."""
    if isinstance(query, exp.Select):
        yield query
    elif isinstance(query, (exp.Subquery, exp.Paren)):
        yield from final_selects(query.this)
    elif isinstance(query, exp.SetOperation):
        yield from final_selects(query.this)
        yield from final_selects(query.expression)


def check_output(
    sql_query: str,
    *,
    output_columns: tuple[str, ...] | None,
    rounding_requested: bool | None,
) -> list[str]:
    """Check result shape and explicit rounding when the requested output is known."""
    if output_columns is None and rounding_requested is not False:
        return []
    try:
        query = parse_one(sql_query, read="mysql")
    except SqlglotError:
        return []  # Let MariaDB validate syntax and dialect-specific statements.

    issues = []
    for select in final_selects(query):
        projections = select.expressions
        values = [projection.unalias().unnest() for projection in projections]
        if len(values) == 1 and isinstance(values[0], exp.Literal) and (
            values[0].is_string and values[0].this == "INSUFFICIENT_SCHEMA_INFORMATION"
        ):
            continue
        if output_columns is not None and not any(value.is_star for value in values):
            if len(projections) != len(output_columns):
                expected = ", ".join(output_columns)
                issues.append(
                    f"Return only the requested output ({expected}). "
                    f"The final SELECT returns {len(projections)} values per row. "
                    f"Expected {len(output_columns)}."
                )
        if rounding_requested is False and any(isinstance(value, exp.Round) for value in values):
            issues.append("Remove ROUND from the final output and preserve the calculated precision.")
    return list(dict.fromkeys(issues))
