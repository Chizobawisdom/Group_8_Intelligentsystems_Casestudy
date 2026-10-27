from connect import get_engine
from get_schema import add_sample_values, format_for_prompt, get_schema, load_descriptions

engine = get_engine()
schema = add_sample_values(engine, get_schema(engine, ["sw_alle_tabelle"]))
print(format_for_prompt(schema, load_descriptions()))