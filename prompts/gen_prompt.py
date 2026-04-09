"""Factories for prompt templates used across the MAC-Reasoner stages."""

import json
from langchain_core.prompts import (
    ChatPromptTemplate,
    FewShotChatMessagePromptTemplate,
    HumanMessagePromptTemplate,
    AIMessagePromptTemplate,
    SystemMessagePromptTemplate,
    PromptTemplate,
)
from prompts.prompts import *


class PromptGenerator:
    """Build reusable prompt templates for Translator, Refiner, Summarizer, and Reasoner."""

    @staticmethod
    def generate_solver_prompt(examples):
        """Create the few-shot Translator prompt for symbolic program generation."""
        few_shot_prompt = FewShotChatMessagePromptTemplate(
            examples=examples,
            # Format each few-shot example as one human/AI exchange.
            example_prompt=(
                HumanMessagePromptTemplate.from_template("{input}")
                + AIMessagePromptTemplate.from_template("{output}")
            ),
        )
        return (
            SystemMessagePromptTemplate.from_template(reasoner_system_prompt)
            + few_shot_prompt
            + HumanMessagePromptTemplate.from_template(reasoner_user_prompt)
        )

    @staticmethod
    def generate_COT_prompt():
        """Create the fallback zero-shot chain-of-thought prompt."""
        return PromptTemplate(
            template=zero_COT_prompt,
            input_variables=["CONTEXT", "QUESTION", "CHOICES"],
        )

    @staticmethod
    def generate_fix_prompt():
        """Create the Refiner prompt used to repair failed symbolic programs."""
        return ChatPromptTemplate.from_messages(
            [("system", fix_system_prompt), ("user", fix_user_prompt)]
        )

    @staticmethod
    def generate_summary_prompt():
        """Create the Summarizer prompt that converts symbolic evidence into natural language."""
        return PromptTemplate(
            template=summary_prompt,
            input_variables=[
                "CONTEXT",
                "QUESTION",
                "CHOICES",
                "solver",
                "solver_info",
                "solution",
            ],
        )

    @staticmethod
    def generate_reasoning_prompt():
        """Create the Reasoner prompt that uses the Logic-Augmented Context as private support."""
        return PromptTemplate(
            template=reasoning_prompt,
            input_variables=["CONTEXT", "QUESTION", "CHOICES", "solver_summary"],
        )
