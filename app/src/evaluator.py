import json
from pathlib import Path
from sqlalchemy import text
from connect import get_engine

def execute_sql(engine, query):
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            # Sort to ensure row order doesn't affect accuracy
            return sorted([tuple(row) for row in result.fetchall()])
    except Exception as e:
        return f"ERROR: {e}"

def evaluate_file(engine, filepath, system_name):
    """Evaluates a single prediction file and returns the accuracy."""
    preds_file = Path(filepath)
    if not preds_file.exists():
        print(f"⚠️ File not found: {filepath}. Skipping {system_name} evaluation.")
        return 0.0

    predictions = json.loads(preds_file.read_text())
    passed = 0
    
    print(f"\n--- Evaluating {system_name} ---")
    
    for item in predictions:
        gen_res = execute_sql(engine, item["generated_sql"])
        gold_res = execute_sql(engine, item["gold_sql"])

        # Check if both are lists (success) and match exactly
        if gen_res == gold_res and not str(gen_res).startswith("ERROR"):
            passed += 1
            print(f"✅ Q{item['id']}: PASS")
        else:
            print(f"❌ Q{item['id']}: FAIL")
            # Optional: Uncomment the lines below to see the actual errors in the terminal
            # print(f"   Generated: {gen_res}")
            # print(f"   Gold:      {gold_res}")

    accuracy = (passed / len(predictions)) * 100
    print(f"Score for {system_name}: {accuracy:.2f}% ({passed}/{len(predictions)})")
    return accuracy

def main():
    engine = get_engine()
    
    # 1. Evaluate the Baseline
    baseline_acc = evaluate_file(
        engine, 
        "data/benchmark/baseline_predictions.json", 
        "Baseline (Single LLM Call)"
    )
    
    # 2. Evaluate the Agent
    agent_acc = evaluate_file(
        engine, 
        "data/benchmark/agent_predictions.json", # Make sure correction.py saves to this file!
        "Agent (Self-Correction)"
    )
    
    # 3. Print the final comparison
    print("\n=============================================")
    print("🏆 FINAL RESULTS")
    print("=============================================")
    print(f"Baseline Accuracy: {baseline_acc:.2f}%")
    print(f"Agent Accuracy:    {agent_acc:.2f}%")
    
    if agent_acc > baseline_acc:
        print(f"🚀 The Agent improved performance by {agent_acc - baseline_acc:.2f}%!")
    elif agent_acc == baseline_acc:
        print("🤝 Both systems performed equally.")
    else:
        print("📉 The Agent performed worse than the baseline.")

if __name__ == "__main__":
    main()