"""Main Orchestrator for the NLP-to-SQL Pipeline.

This script runs the entire workflow:
1. Baseline Generation (Single LLM call)
2. Agentic Generation (Self-correction loop)
3. Evaluation (Compare both against the Gold SQL)
"""
import sys
from baseline import main as run_baseline
from correction import main as run_agent
from evaluator import main as run_evaluator

def main():
    print("=" * 60)
    print("🚀 STARTING NLP-TO-SQL WORKFLOW")
    print("=" * 60)

    print("\n[PHASE 1] Running Baseline (Single LLM Call)...")
    run_baseline() 
    
    print("\n[PHASE 2] Running Agent (Self-Correction Loop)...")
    run_agent()

    print("\n[PHASE 3] Evaluating Results...")
    run_evaluator()

    print("\n" + "=" * 60)
    print("🏁 WORKFLOW COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()