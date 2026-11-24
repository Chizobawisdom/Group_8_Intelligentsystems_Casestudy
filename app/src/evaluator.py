import json
from pathlib import Path
from sqlalchemy import text

from connect import get_engine

BASELINE_PREDICTIONS = Path("data/benchmark/baseline_predictions.json")
AGENT_PREDICTIONS = Path("data/benchmark/agent_predictions.json")
BASELINE_NAME = "Baseline (Single LLM Call)"
AGENT_NAME = "Agent (Self-Correction)"

def execute_sql(engine, query):
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            # Sort to ensure row order doesn't affect accuracy
            return sorted([tuple(row) for row in result.fetchall()])
    except Exception as e:
        return f"ERROR: {e}"

def execution_accuracy(outcomes: list[bool]) -> float:
    return sum(outcomes) / len(outcomes) * 100 if outcomes else 0.0


def evaluate_predictions(
    engine,
    predictions: list[dict],
    system_name: str,
    *,
    reference_results: dict[str, list[tuple] | str] | None = None,
) -> list[bool]:
    outcomes = []
    print(f"\n--- Evaluating {system_name} ---")
    for item in predictions:
        generated = execute_sql(engine, item["generated_sql"])
        reference_sql = item["gold_sql"]
        if reference_results is not None and reference_sql in reference_results:
            expected = reference_results[reference_sql]
        else:
            expected = execute_sql(engine, reference_sql)
            if reference_results is not None:
                reference_results[reference_sql] = expected
        passed = isinstance(generated, list) and generated == expected
        outcomes.append(passed)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"Q{item['id']}: {status}")

    accuracy = execution_accuracy(outcomes)
    print(f"Score for {system_name}: {accuracy:.2f}% ({sum(outcomes)}/{len(outcomes)})")
    return outcomes


def evaluate_file(engine, filepath, system_name) -> float:
    """Evaluate a prediction file and return its execution accuracy."""
    preds_file = Path(filepath)
    if not preds_file.exists():
        print(f"⚠️ File not found: {filepath}. Skipping {system_name} evaluation.")
        return 0.0

    predictions = json.loads(preds_file.read_text(encoding="utf-8"))
    return execution_accuracy(evaluate_predictions(engine, predictions, system_name))


def print_summary(baseline_acc: float, agent_acc: float) -> None:
    print("\n=============================================")
    print("🏆 FINAL RESULTS")
    print("=============================================")
    print(f"Baseline Accuracy: {baseline_acc:.2f}%")
    print(f"Agent Accuracy:    {agent_acc:.2f}%")

    if agent_acc > baseline_acc:
        print(f"🚀 The Agent improved performance by {agent_acc - baseline_acc:.2f} percentage points!")
    elif agent_acc == baseline_acc:
        print("🤝 Both systems performed equally.")
    else:
        print("📉 The Agent performed worse than the baseline.")


def main() -> None:
    engine = get_engine()
    try:
        baseline_acc = evaluate_file(engine, BASELINE_PREDICTIONS, BASELINE_NAME)
        agent_acc = evaluate_file(engine, AGENT_PREDICTIONS, AGENT_NAME)
        print_summary(baseline_acc, agent_acc)
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
