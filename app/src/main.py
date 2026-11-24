"""Main Orchestrator for the NLP-to-SQL Pipeline.

This script runs the entire workflow:
1. Baseline Generation (Single LLM call)
2. Agentic Generation (Self-correction loop)
3. Evaluation (Compare both against the Gold SQL)
"""
from dataclasses import dataclass
from time import perf_counter

from sqlalchemy.engine import Engine

from baseline import (
    build_llm,
    generate_predictions,
    generate_sql,
    get_schema_text,
    load_questions,
    save_predictions,
)
from connect import get_engine
from correction import run_correction_agent
from evaluator import (
    AGENT_NAME,
    AGENT_PREDICTIONS,
    BASELINE_NAME,
    BASELINE_PREDICTIONS,
    evaluate_predictions,
    execution_accuracy,
    print_summary,
)

BENCHMARK_WORKERS = 2


@dataclass
class BenchmarkResult:
    baseline_accuracy: float
    agent_accuracy: float
    question_results: list[dict]
    elapsed_seconds: float


def main(
    engine: Engine | None = None, *, llm=None, schema_text: str | None = None
) -> BenchmarkResult:
    """Run the benchmark, writing prediction files when using the CLI connection."""
    started_at = perf_counter()
    use_cli_connection = engine is None
    if engine is None:
        engine = get_engine()

    try:
        questions = load_questions()
        if not questions:
            raise ValueError("No benchmark questions were found.")
        if llm is None:
            llm = build_llm()
        if schema_text is None:
            schema_text = get_schema_text() if use_cli_connection else get_schema_text(engine)

        print("[PHASE 1] Running Baseline (Single LLM Call)")
        baseline = generate_predictions(
            questions,
            lambda question: generate_sql(llm, schema_text, question),
            max_workers=BENCHMARK_WORKERS,
        )

        print("\n[PHASE 2] Running Agent (Self-Correction Loop)")
        agent = generate_predictions(
            questions,
            lambda question: run_correction_agent(engine, llm, schema_text, question),
            max_workers=BENCHMARK_WORKERS,
        )

        print("\n[PHASE 3] Evaluating Results")
        reference_results = {}
        baseline_outcomes = evaluate_predictions(
            engine, baseline, BASELINE_NAME, reference_results=reference_results
        )
        agent_outcomes = evaluate_predictions(
            engine, agent, AGENT_NAME, reference_results=reference_results
        )
        result = BenchmarkResult(
            baseline_accuracy=execution_accuracy(baseline_outcomes),
            agent_accuracy=execution_accuracy(agent_outcomes),
            question_results=[
                {
                    "Question ID": item["id"],
                    "Question": item["question"],
                    "Baseline": "Pass" if baseline_passed else "Fail",
                    "Agent": "Pass" if agent_passed else "Fail",
                }
                for item, baseline_passed, agent_passed in zip(
                    questions, baseline_outcomes, agent_outcomes, strict=True
                )
            ],
            elapsed_seconds=perf_counter() - started_at,
        )

        if use_cli_connection:
            save_predictions(BASELINE_PREDICTIONS, baseline)
            save_predictions(AGENT_PREDICTIONS, agent)

        print_summary(result.baseline_accuracy, result.agent_accuracy)
        return result
    finally:
        if use_cli_connection:
            engine.dispose()

if __name__ == "__main__":
    main()
