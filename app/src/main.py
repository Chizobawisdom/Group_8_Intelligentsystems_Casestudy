"""Main Orchestrator for the NLP-to-SQL Pipeline.

This script runs the entire workflow:
1. Baseline Generation (Single LLM call)
2. Agentic Generation (Self-correction loop)
3. Evaluation (Compare both against the Gold SQL)
"""
from collections.abc import Callable
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
from correction import run_agent_with_details
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
    engine: Engine | None = None,
    *,
    llm=None,
    schema_text: str | None = None,
    log: Callable[[str], None] = print,
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

        log("[PHASE 1] Running Baseline (Single LLM Call)")
        baseline = generate_predictions(
            questions,
            lambda question: generate_sql(llm, schema_text, question),
            max_workers=BENCHMARK_WORKERS,
            log=log,
        )

        log("\n[PHASE 2] Running Agent (Self-Correction Loop)")

        def predict_agent(question: str) -> dict[str, str]:
            run = run_agent_with_details(engine, llm, schema_text, question, log=log)
            return {**run.as_prediction(), "agent_path": run.path}

        agent = generate_predictions(
            questions,
            predict_agent,
            max_workers=BENCHMARK_WORKERS,
            log=log,
        )
        agent_paths = [prediction.pop("agent_path") for prediction in agent]

        log("\n[PHASE 3] Evaluating Results")
        reference_results = {}
        baseline_outcomes = evaluate_predictions(
            engine, baseline, BASELINE_NAME, reference_results=reference_results, log=log
        )
        agent_outcomes = evaluate_predictions(
            engine, agent, AGENT_NAME, reference_results=reference_results, log=log
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
                    "Agent path": agent_path,
                }
                for item, baseline_passed, agent_passed, agent_path in zip(
                    questions, baseline_outcomes, agent_outcomes, agent_paths, strict=True
                )
            ],
            elapsed_seconds=perf_counter() - started_at,
        )

        if use_cli_connection:
            save_predictions(BASELINE_PREDICTIONS, baseline, log=log)
            save_predictions(AGENT_PREDICTIONS, agent, log=log)

        print_summary(result.baseline_accuracy, result.agent_accuracy, log=log)
        return result
    finally:
        if use_cli_connection:
            engine.dispose()

if __name__ == "__main__":
    main()
