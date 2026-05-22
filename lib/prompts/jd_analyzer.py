from __future__ import annotations

import asyncio
import json

import streamlit as st
import structlog
from pydantic import ValidationError

from lib.openrouter.chat import chat_complete, get_message_content
from lib.schemas.jd_analysis import JDAnalysis

logger = structlog.get_logger(__name__)

JD_ANALYZER_SYSTEM_PROMPT = """You are a technical recruiter assistant. Analyze the job description and extract structured information.

Return ONLY valid JSON with this exact structure:
{
  "stack": ["list", "of", "technologies"],
  "level": "junior" | "mid" | "senior" | "unknown",
  "suggested_domain": "frontend" | "backend" | "data_ml" | "devops" | "system_design" | "behavioral",
  "key_topics": ["topic1", "topic2", ...],
  "company_type": "startup" | "tech_startup" | "enterprise" | "agency" | "unknown",
  "confidence": 0.0 to 1.0
}

Be precise. Stack should include programming languages, frameworks, tools mentioned. Key topics should reflect what the interview will focus on."""


async def analyze_jd(
    job_description: str,
    model: str = "openai/gpt-5-nano",
) -> JDAnalysis:
    """Parse job description via LLM. Returns JDAnalysis with fallback on error."""
    try:
        response = await chat_complete(
            model=model,
            messages=[
                {"role": "system", "content": JD_ANALYZER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Analyze this job description:\n\n{job_description[:5000]}",
                },
            ],
            temperature=0.1,
            max_tokens=512,
            response_format={"type": "json_object"},
        )
        content = get_message_content(response)
        return JDAnalysis.model_validate_json(content)
    except (ValidationError, KeyError, json.JSONDecodeError) as exc:
        logger.warning("jd_analysis_failed", error=str(exc))
        # Fallback: unknown analysis, caller should handle gracefully
        return JDAnalysis(
            stack=[],
            level="unknown",
            suggested_domain="backend",
            key_topics=[],
            company_type="unknown",
            confidence=0.0,
        )


@st.cache_data(ttl=300, show_spinner=False)
def analyze_jd_cached(jd: str) -> JDAnalysis:
    """Sync wrapper for Streamlit cache. Used for live JD preview."""
    return asyncio.run(analyze_jd(jd))
