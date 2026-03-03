"""
AI Analyzer service — sends transcript to LLM API for clip / hook extraction.

NEW service (not in original pipeline — replaces the manual step 2).
"""

import json
from pathlib import Path
from typing import Optional

from backend.models import AIAnalysisConfig, LLMProvider


def _load_prompt_template(prompt_type: str, project_root: Path) -> str:
    """Load the prompt template from the project root."""
    filename = f"{prompt_type}_extraction_prompt.txt"
    path = project_root / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding='utf-8')


def _call_openai(prompt: str, transcript_text: str, model: str, api_key: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": transcript_text},
        ],
        temperature=0.3,
        max_tokens=8192,
    )
    return response.choices[0].message.content


def _call_anthropic(prompt: str, transcript_text: str, model: str, api_key: str) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=prompt,
        messages=[
            {"role": "user", "content": transcript_text},
        ],
    )
    return response.content[0].text


def _extract_json(text: str) -> list | dict:
    """Extract JSON from LLM response (handles markdown code blocks)."""
    import re
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from code block
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try finding array
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError("Could not parse JSON from LLM response")


def analyze_transcript(
    transcript_text: str,
    config: AIAnalysisConfig,
    project_root: Path,
) -> dict:
    """
    Send transcript to LLM and return parsed clip/hook data.

    Returns:
        {"clips": [...]} or {"hooks": [...]}
    """
    prompt = _load_prompt_template(config.prompt_type, project_root)

    if not config.api_key:
        raise ValueError("API key is required for AI analysis")

    if config.provider == LLMProvider.OPENAI:
        raw = _call_openai(prompt, transcript_text, config.model, config.api_key)
    elif config.provider == LLMProvider.ANTHROPIC:
        raw = _call_anthropic(prompt, transcript_text, config.model, config.api_key)
    else:
        raise ValueError(f"Unknown provider: {config.provider}")

    parsed = _extract_json(raw)

    # Wrap in expected structure
    if config.prompt_type == "clips":
        if isinstance(parsed, list):
            return {"clips": parsed}
        if isinstance(parsed, dict) and "clips" in parsed:
            return parsed
        return {"clips": parsed if isinstance(parsed, list) else [parsed]}
    else:
        if isinstance(parsed, list):
            return {"hooks": parsed}
        if isinstance(parsed, dict) and "hooks" in parsed:
            return parsed
        return {"hooks": parsed if isinstance(parsed, list) else [parsed]}
