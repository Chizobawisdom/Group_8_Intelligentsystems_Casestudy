import json
from pathlib import Path
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def get_schema(engine: Engine, tables: list[str] | None = None) -> dict:
    insp = inspect(engine)
    names = tables or insp.get_table_names()  # views: insp.get_view_names()
    schema = {}
    for table in names:
        schema[table] = {
            "columns": [
                {
                    "name": c["name"],
                    "type": str(c["type"]),
                    "nullable": c["nullable"],
                }
                for c in insp.get_columns(table)
            ],
            "primary_key": insp.get_pk_constraint(table).get("constrained_columns", []),
            "foreign_keys": [
                {
                    "columns": fk["constrained_columns"],
                    "references": f'{fk["referred_table"]}({", ".join(fk["referred_columns"])})',
                }
                for fk in insp.get_foreign_keys(table)
            ],
        }
    return schema


def add_sample_values(engine: Engine, schema: dict, n: int = 3) -> dict:
    # Names come from the inspector, not from user input, so f-strings are safe here
    with engine.connect() as conn:
        for table, info in schema.items():
            for col in info["columns"]:
                name = col["name"]
                rows = conn.execute(
                    text(f"SELECT DISTINCT `{name}` FROM `{table}` WHERE `{name}` IS NOT NULL LIMIT {n}")
                ).fetchall()
                col["examples"] = [str(r[0])[:50] for r in rows]
    return schema


def load_descriptions(path: str = "data/schema/column_descriptions.json") -> dict:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def format_for_prompt(schema: dict, descriptions: dict | None = None) -> str:
    descriptions = descriptions or {}
    lines = []
    for table, info in schema.items():
        pk = ", ".join(info["primary_key"]) or "none"
        lines.append(f"Table {table} (primary key: {pk})")
        for col in info["columns"]:
            desc = descriptions.get(table, {}).get(col["name"], "")
            desc_part = f" - {desc}" if desc else ""
            ex = col.get("examples")
            ex_part = f" (e.g. {', '.join(ex)})" if ex else ""
            lines.append(f"- {col['name']} {col['type']}{desc_part}{ex_part}")
        lines.append("")
    return "\n".join(lines)


