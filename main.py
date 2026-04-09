import prompts
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import json
from reasoner import MACReasoner
import subprocess
import sys
import copy
import random
import z3
import argparse
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

if __name__ == "__main__":
    # Parse runtime configuration for the model backend and dataset.
    assert (
        z3 is not None
    ), "z3-solver library is required for runtime evaluation. Please install it via 'pip install z3-solver'."

    parser = argparse.ArgumentParser(description="MAC-Reasoner")
    parser.add_argument(
        "--base_url",
        type=str,
        required=False,
        help="API base URL",
        default="https://api.openai.com/v1",
    )
    parser.add_argument("--api_key", type=str, required=True, help="API key")
    parser.add_argument("--model_name", type=str, required=True, help="Model name")
    parser.add_argument(
        "--max_tokens",
        type=int,
        required=False,
        help="Maximum tokens",
        default=1024 * 12,
    )
    parser.add_argument("--dataset", type=str, required=True, help="Dataset name")
    parser.add_argument(
        "--Gemini", action="store_true", default=False, help="Use Gemini API"
    )

    args = parser.parse_args()

    # Store run outputs under results/ using the dataset and model identifier.
    resultsPath = (
        Path("results") / f"{args.dataset}-{args.model_name.replace('/', '_')}.json"
    )
    resultsPath.parent.mkdir(parents=True, exist_ok=True)

    # Load evaluation samples and few-shot examples for the Translator stage.
    with open(f"data/{args.dataset}/test.json", "r", encoding="utf-8") as f:
        datas = json.load(f)
    with open(f"data/{args.dataset}/few-shots.json", "r", encoding="utf-8") as f:
        examples = json.load(f)

    # Initialize either the OpenAI-compatible backend or the Gemini backend.
    if args.Gemini:
        os.environ["GOOGLE_API_KEY"] = args.api_key
        llm = ChatGoogleGenerativeAI(
            model=args.model_name,
            max_tokens=args.max_tokens,
            streaming=True,
        )
    else:
        llm = ChatOpenAI(
            model=args.model_name,
            streaming=True,
            max_completion_tokens=args.max_tokens,
            api_key=args.api_key,
            base_url=args.base_url,
        )

    # Run the MAC-Reasoner pipeline and write per-sample outputs to disk.
    elise = MACReasoner(
        llm=llm,
        datas=datas,
        max_workers=20,
        examples=examples,
    )
    results = elise.work()

    with resultsPath.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
