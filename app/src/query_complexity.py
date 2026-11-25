import re


COMPLEX_QUESTION = re.compile(
    r"\b(?:strictly (?:before|after)|"
    r"(?:before|after) (?:an? |the )?(?:action|step|scan|record|event)s?|"
    r"(?:first|last|next) (?:record|event|scan|occurrence|step|action)|"
    r"both actions?|count in both|cumulative(?:ly)?|running total|"
    r"more than once|no (?:record|event|scan) (?:at|for|with)|never (?:have|had|recorded)|"
    r"(?:busiest|highest|lowest|most frequent) [^?.\n]*\bfor each|"
    r"at least (?:two|\d+) (?:distinct )?(?:revisions|workstations)|"
    r"(?:two|\d+) or more (?:distinct )?(?:workstations|actions|steps)|"
    r"percent(?:age)?s?|ratio|(?:failure|success|defect) rate|"
    r"first[- ]pass|cross(?:es|ing)? midnight)\b|\d\s*%",
    re.IGNORECASE,
)

COMPLEX_SQL = re.compile(
    r"^\s*WITH\b|\b(?:JOIN|HAVING|UNION)\b|\bOVER\s*\(|\(\s*SELECT\b|"
    r"\bCOUNT\s*\(\s*DISTINCT\s+(?:CASE\b|IF\s*\()",
    re.IGNORECASE,
)

SQL_LITERALS = re.compile(
    r"'(?:''|\\.|[^'\\])*'"
    r'|"(?:""|\\.|[^"\\])*"'
    r"|`(?:``|[^`])*`"
)


def is_complex_question(question: str) -> bool:
    return COMPLEX_QUESTION.search(question) is not None


def is_complex_sql(sql_query: str) -> bool:
    return COMPLEX_SQL.search(SQL_LITERALS.sub(" ", sql_query)) is not None
