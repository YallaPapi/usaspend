"""
Research utilities using Perplexity API for implementation guidance.
"""

import os
import requests
from typing import Dict, Any


PERPLEXITY_MODELS = {
    "sonar": "llama-3.1-sonar-small-128k-online",
    "sonar-pro": "llama-3.1-sonar-large-128k-online"
}

DEFAULT_MODEL = "sonar-pro"


def research_with_perplexity(query: str, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    Research implementation approaches using Perplexity API.
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY not found in environment")

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": PERPLEXITY_MODELS.get(model, PERPLEXITY_MODELS[DEFAULT_MODEL]),
        "messages": [
            {
                "role": "system",
                "content": "You are a technical expert specializing in API integrations, data pipelines, and financial data sources. Provide practical, implementable solutions with specific code examples where appropriate."
            },
            {
                "role": "user",
                "content": query
            }
        ],
        "temperature": 0.2,
        "max_tokens": 2000
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Research API error: {e}")
        return {"error": str(e)}


def get_sec_form_d_research() -> str:
    """Research SEC Form D bulk data feed implementation."""
    query = """
    Provide a detailed implementation guide for fetching SEC Form D filings data:

    1. What are the best APIs/data sources for historical SEC Form D data?
    2. EDGAR bulk data feeds vs REST API vs RSS feeds - which is most suitable for backfilling 3 years of data?
    3. Provide specific URLs, file formats, and parsing requirements for Form D data
    4. Rate limiting, authentication, and commercial use requirements
    5. Sample code structure for fetching and parsing Form D filings
    6. Data mapping from Form D fields to company/funding event schema

    Focus on practical implementation details for a data pipeline project.
    """

    result = research_with_perplexity(query)
    if "error" not in result:
        return result.get("choices", [{}])[0].get("message", {}).get("content", "Research failed")
    return result["error"]


def get_sbir_research() -> str:
    """Research SBIR/STTR data sources and APIs."""
    query = """
    Provide a comprehensive guide for implementing SBIR/STTR data ingestion:

    1. What are the official APIs and data sources for SBIR/STTR funding data?
    2. SBIR.gov API capabilities, endpoints, and authentication requirements
    3. Data.gov or other government open data portals for SBIR data
    4. Best practices for fetching historical SBIR award data (3+ years)
    5. Data format, pagination, and rate limiting considerations
    6. Sample implementation code for SBIR data retrieval
    7. Mapping SBIR fields to unified funding event schema

    Include specific URLs and practical implementation approaches.
    """

    result = research_with_perplexity(query)
    if "error" not in result:
        return result.get("choices", [{}])[0].get("message", {}).get("content", "Research failed")
    return result["error"]