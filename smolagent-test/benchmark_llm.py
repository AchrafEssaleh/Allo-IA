
import json
import os
import re
import time
import requests
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

from main import (
    create_agent,
    parse_agent_output,
    create_pdf,
)


# Directories
BASE_DIR = Path(__file__).resolve().parent
DESCRIPTIONS_DIR = BASE_DIR / "descriptions"

API_BASE = "https://llm.ilaas.fr/v1"
API_KEY = os.environ.get("ILAAS_API_KEY")

RESULTS_FILE = BASE_DIR / "benchmark_results.json"


def get_available_models():
    """Retrieve all available model IDs from ILaaS."""

    response = requests.get(
        f"{API_BASE}/models",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )

    try:
        result = response.json()

        models = [
            model["id"]
            for model in result["data"]
            if "id" in model
        ]

        if not models:
            raise ValueError("No models were returned by ILaaS.")

        return models

    except (requests.RequestException, KeyError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"Could not retrieve ILaaS models: {error}"
        ) from error


def sanitize_filename(name):
    """Convert a name into a safe directory/file name."""

    return re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_") or "project"


def generate_documentation(agent, description_path):
    """Generate documentation for one project description."""

    description = description_path.read_text(
        encoding="utf-8"
    ).strip()

    if not description:
        raise ValueError("The project description is empty.")

    task = f"""
    Create a technical project notebook from the description below.

    Use web research only if it adds useful technical information.
    Do not fill gaps with guesses. List important missing information
    explicitly in the documentation.

    PROJECT DESCRIPTION:
    {description}
    """

    # Measure only generation time.
    start_time = time.perf_counter()
    raw_output = agent.run(task)
    generation_time = time.perf_counter() - start_time

    try:
        data = parse_agent_output(raw_output)
        parse_error = None 
    except Exception as e:
        data = raw_output  # Return raw output if parsing fails
        parse_error = str(e)  # Indicate that the output is raw

    return data, parse_error, generation_time


def benchmark_model(model_id, description_files):
    """Run the benchmark for one model across all descriptions."""

    print(f"\n{'=' * 60}")
    print(f"Testing model: {model_id}")
    print(f"{'=' * 60}")

    output_dir = BASE_DIR / f"benchmark_outputs/{sanitize_filename(model_id)}_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []

    # Create one agent for this model.
    agent = create_agent(model_id=model_id)

    for description_path in description_files:

        project_name = sanitize_filename(description_path.stem)

        print(f"\nProcessing: {description_path.name}")

        result = {
            "description": description_path.name,
            "status": "failed",
            "generation_time_seconds": None,
            "parse_error": None,
            "error": None,
        }

        try:
            data, parse_error, generation_time = generate_documentation(
                agent,
                description_path,
            )
            print(f"Generation time: {generation_time:.2f} seconds")

            result.update({
                            "status": "success" if not parse_error else "invalid_json_output",
                            "generation_time_seconds": round(generation_time, 3),
                            "parse_error": parse_error,
                        })

            if not parse_error:
                pdf_path = output_dir / f"{project_name}_documentation.pdf"
                create_pdf(data, pdf_path)
                result["pdf_path"] = str(pdf_path.relative_to(BASE_DIR))
                print(f"PDF document: {pdf_path}")
            else:
                print(f"WARNING: Output could not be parsed for {description_path.name}. PDF not generated.")
                raw_output_path = output_dir / f"{project_name}_raw_output.txt"
                raw_output_path.write_text(data, encoding="utf-8")
                result["raw_output_path"] = str(raw_output_path.relative_to(BASE_DIR))

        except Exception as error:
            result.update({
                "status": "failed",
                "generation_time_seconds": None,
                "error": str(error),
            })
            print(f"FAILED: {error}")

        results.append(result)

    # Calculate average using successful generations only.
    successful_times = [
        result["generation_time_seconds"]
        for result in results
        if result["status"] == "success"
    ]

    average_time = (
        sum(successful_times) / len(successful_times)
        if successful_times else None
    )

    summary = {
        "model_id": model_id,
        "output_directory": str(output_dir.relative_to(BASE_DIR)),
        "total_descriptions": len(description_files),
        "successful_generations": len(successful_times),
        "failed_generations": len(description_files) - len(successful_times),
        "average_generation_time_seconds": (
            round(average_time, 3)
            if average_time is not None else None
        ),
        "results": results,
    }

    if average_time is not None:
        print(f"\nAverage generation time: {average_time:.2f} seconds")
    else:
        print("\nNo successful generations for this model.")

    return summary


def main():
    if not API_KEY:
        raise RuntimeError("ILAAS_API_KEY environment variable is not set in .env file.")

    if not DESCRIPTIONS_DIR.is_dir():
        raise FileNotFoundError(
            f"Descriptions directory not found: {DESCRIPTIONS_DIR}"
        )

    description_files = sorted(DESCRIPTIONS_DIR.glob("*.txt"))

    if not description_files:
        raise ValueError(
            f"No .txt files found in {DESCRIPTIONS_DIR}"
        )

    print(f"Found {len(description_files)} descriptions.")

    # Retrieve all available ILaaS models.
    models = get_available_models()

    print(f"Found {len(models)} available models:")
    for model in models:
        print(f" - {model}")

    benchmark_results = {
        "benchmark_date": datetime.now(timezone.utc).isoformat(),
        "total_models": len(models),
        "total_descriptions": len(description_files),
        "models": [],
    }

    # Run every description against every model.
    for model_id in models:
        try:
            model_results = benchmark_model(
                model_id,
                description_files,
            )

        except Exception as error:
            # For example, agent initialization may fail.
            print(f"\nCould not benchmark {model_id}: {error}")

            model_results = {
                "model_id": model_id,
                "total_descriptions": len(description_files),
                "successful_generations": 0,
                "failed_generations": len(description_files),
                "average_generation_time_seconds": None,
                "initialization_error": str(error),
                "results": [],
            }

        benchmark_results["models"].append(model_results)

        # Save progress after each model in case the benchmark is interrupted.
        RESULTS_FILE.write_text(
            json.dumps(benchmark_results, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )

    print(f"\n{'=' * 60}")
    print("BENCHMARK SUMMARY")
    print(f"{'=' * 60}")

    for result in benchmark_results["models"]:
        average = result["average_generation_time_seconds"]

        print(f"\nModel: {result['model_id']}")
        print(f"Successful: {result['successful_generations']}")
        print(f"Failed: {result['failed_generations']}")

        if average is not None:
            print(f"Average time: {average:.2f} seconds")
        else:
            print("Average time: N/A")

    print(f"\nFull results saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    main()
