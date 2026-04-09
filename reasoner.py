import threading
import prompts
import traceback
import concurrent.futures
import utils
import json
from tqdm import tqdm
from collections import Counter
import sys
import random
import math
import time
import re
import copy
from typing import Optional


class MACReasoner:
    """Coordinate the Translator, Refiner, Summarizer, and Reasoner stages."""

    def __init__(
        self,
        llm,
        datas,
        max_workers: int = 20,
        max_fix_attempts: int = 5,
        examples: Optional[list] = None,
    ):
        self.llm = llm
        self.datas = datas
        self.prompts_gen = prompts.PromptGenerator

        if examples:
            self.chain_prompt = self.prompts_gen.generate_solver_prompt(
                examples=examples
            )
        self.fix_prompt = self.prompts_gen.generate_fix_prompt()
        self.cot_prompt = self.prompts_gen.generate_COT_prompt()
        self.faith_prompt = self.prompts_gen.generate_reasoning_prompt()
        self.summary_prompt = self.prompts_gen.generate_summary_prompt()

        self.max_workers = max_workers
        self.max_fix_attempts = max_fix_attempts
        self.lock = threading.Lock()
        self.results = []

    def work(self):
        """Run the full MAC-Reasoner workflow over a dataset split."""

        def thread_task(data):
            result = self.handle(data)
            return result

        success_count = 0
        with tqdm(total=len(self.datas), desc="Processing", file=sys.stdout) as pbar:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_workers
            ) as executor:
                futures = []
                for data in self.datas:
                    future = executor.submit(lambda d: thread_task(d), data)
                    # Advance the progress bar as soon as one sample completes.
                    future.add_done_callback(lambda _: pbar.update(1))
                    futures.append(future)

                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    if res is None:
                        raise Exception("Error occurred in thread_task")
                    with self.lock:
                        self.results.append(res)
                        success_count += 1 if res["is_correct"] else 0
                    success_rate = success_count / (pbar.n or 1)
                    pbar.set_description(
                        f"Success: {success_count}/{pbar.n} ({success_rate:.0%})"
                    )

        return self.results

    def handle(self, data):
        """Process one sample through translation, refinement, summarization, and reasoning."""

        input_data = {
            "CONTEXT": str(data["context"]),
            "QUESTION": str(data["question"]),
            "OPTIONS": "\n".join(data["options"]),
        }
        # Translator: generate an initial symbolic program for the problem.
        resp = self.llm.invoke(self.chain_prompt.format(**input_data))
        if hasattr(resp, "content"):
            content = resp.content
        elif hasattr(resp, "text"):
            content = resp.text
        else:
            content = str(resp)

        stdout, stderr = utils.z3_exec(content)
        if stderr:
            # Refiner: repair the symbolic program until it can be executed and checked.
            for _ in range(self.max_fix_attempts):
                fix_input = {
                    "ERROR_MESSAGE": stderr,
                    "CODE": utils.extract_python_code(content),
                    "CONTEXT": str(data["context"]),
                    "QUESTION": str(data["question"]),
                    "OPTIONS": "\n".join(data["options"]),
                }

                resp = self.llm.invoke(self.fix_prompt.format(**fix_input))
                if hasattr(resp, "content"):
                    content = resp.content
                elif hasattr(resp, "text"):
                    content = resp.text
                else:
                    content = str(resp)

                stdout, stderr = utils.z3_exec(content)
                if not stderr:
                    break

        if stderr:
            # If no usable Logic-Augmented Context can be obtained, fall back to direct CoT.
            cot_res = self.COT(data)

            res = {
                **data,
                "response": cot_res["response"],
                "is_correct": cot_res["is_correct"],
                "backup": 1,
                "reasoner": cot_res,
            }
        else:
            code = utils.extract_python_code(content)
            reasoner_content = self._reasoning(data, code)

            temp_answer = utils.extract_answer(reasoner_content)
            res = {
                **data,
                "response": reasoner_content,
                "is_correct": temp_answer == data["answer"],
                "backup": 0,
            }
        return res

    def COT(self, data):
        """Answer one sample with the fallback CoT path."""
        input_data = {
            "CONTEXT": str(data["context"]),
            "QUESTION": str(data["question"]),
            "OPTIONS": "\n".join(data["options"]),
        }

        resp = self.llm.invoke(self.cot_prompt.format(**input_data))
        if hasattr(resp, "content"):
            content = resp.content
        elif hasattr(resp, "text"):
            content = resp.text
        else:
            content = str(resp)

        res = {
            **data,
            "response": content,
            "cot_answer": utils.extract_answer(content),
            "is_correct": utils.extract_answer(content) == data["answer"],
        }
        return res

    def _summary_solver(self, data, code: Optional[str] = None):
        """Build a natural-language Logic-Augmented Context from tracked symbolic evidence."""
        if code is None:
            code = utils.extract_python_code(data["response"])
        solver_info = utils.track_solver(code)
        input_data = {
            "CONTEXT": str(data["context"]),
            "QUESTION": str(data["question"]),
            "OPTIONS": "\n".join(data["options"]),
            "solver": code,
            "solver_info": solver_info,
        }

        resp = self.llm.invoke(self.summary_prompt.format(**input_data))
        if hasattr(resp, "content"):
            content = resp.content
        elif hasattr(resp, "text"):
            content = resp.text
        else:
            content = str(resp)

        return content

    def _reasoning(self, data, code: Optional[str] = None):
        """Generate final reasoning conditioned on the cleaned Logic-Augmented Context."""
        solver_summary = self._summary_solver(data, code)

        clean_text = utils.clean_response(solver_summary)

        input_data = {
            "CONTEXT": str(data["context"]),
            "QUESTION": str(data["question"]),
            "OPTIONS": "\n".join(data["options"]),
            "solver_summary": clean_text,
        }

        resp = self.llm.invoke(self.faith_prompt.format(**input_data))
        if hasattr(resp, "content"):
            content = resp.content
        elif hasattr(resp, "text"):
            content = resp.text
        else:
            content = str(resp)

        return content
