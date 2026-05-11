"""
Remote local-model analysis over an OpenAI-compatible Ollama endpoint.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, Optional

import aiohttp

from app.core.config import settings


class LocalModelAnalysisService:
    """Ask a small local model to summarize the retrieved facts for a stock idea."""

    prompt_version = "local-thesis-v1"

    def __init__(self) -> None:
        self.base_url = (settings.LOCAL_LLM_BASE_URL or "").rstrip("/")
        self.model = settings.LOCAL_LLM_MODEL
        self.provider = settings.LOCAL_LLM_PROVIDER or "openai-compatible"
        self.timeout_seconds = max(settings.LOCAL_LLM_TIMEOUT_SECONDS, 5)
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        if self.enabled() and self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None

    def enabled(self) -> bool:
        return bool(settings.ENABLE_LOCAL_LLM and self.base_url and self.model)

    async def analyze_prediction(self, idea: Dict[str, Any]) -> Dict[str, Any]:
        """Return a concise structured read of the available facts for one idea."""
        if not self.enabled():
            raise RuntimeError("Local model analysis is not enabled.")
        parsed = await self.request_structured_json(
            system_prompt=(
                "You are a careful stock research assistant. Use only the supplied facts. "
                "Fill the JSON schema accurately and concisely."
            ),
            user_prompt=self._build_prompt(idea),
            schema={
                "type": "object",
                "properties": {
                    "thesisSummary": {"type": "string"},
                    "verdict": {
                        "type": "string",
                        "enum": ["supports", "mixed", "contradicts"],
                    },
                    "keySupport": {"type": "array", "items": {"type": "string"}},
                    "keyRisks": {"type": "array", "items": {"type": "string"}},
                    "confidenceAdjustment": {
                        "type": "string",
                        "enum": ["increase", "neutral", "decrease"],
                    },
                    "watchNextSession": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "thesisSummary",
                    "verdict",
                    "keySupport",
                    "keyRisks",
                    "confidenceAdjustment",
                    "watchNextSession",
                ],
            },
            prompt_version=self.prompt_version,
            max_tokens=220,
            temperature=0.0,
        )

        return {
            "provider": self.provider,
            "model": self.model,
            "promptVersion": self.prompt_version,
            "generatedAt": datetime.utcnow().isoformat(),
            "thesisSummary": parsed.get("thesisSummary"),
            "verdict": parsed.get("verdict"),
            "keySupport": parsed.get("keySupport") or [],
            "keyRisks": parsed.get("keyRisks") or [],
            "confidenceAdjustment": parsed.get("confidenceAdjustment"),
            "watchNextSession": parsed.get("watchNextSession") or [],
        }

    async def request_structured_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any],
        *,
        prompt_version: str,
        max_tokens: int = 220,
        temperature: float = 0.0,
    ) -> Dict[str, Any]:
        if not self.enabled():
            raise RuntimeError("Local model analysis is not enabled.")
        if not self.session:
            raise RuntimeError("LocalModelAnalysisService must be used as async context manager")

        if self.provider.lower() == "ollama":
            return await self._request_with_ollama_native(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                schema=schema,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        return await self._request_with_openai_compat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            prompt_version=prompt_version,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def _request_with_openai_compat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        prompt_version: str,
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        request_payload = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "think": False,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{system_prompt} "
                        f"Return valid JSON only. Prompt version: {prompt_version}."
                    ),
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        }

        async with self.session.post(
            f"{self.base_url}/chat/completions",
            json=request_payload,
        ) as response:
            response.raise_for_status()
            payload = await response.json()

        message = (((payload.get("choices") or [{}])[0]).get("message") or {})
        content = message.get("content") or ""
        return self._parse_json(content)

    async def _request_with_ollama_native(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema: Dict[str, Any],
        max_tokens: int,
        temperature: float,
    ) -> Dict[str, Any]:
        request_payload = {
            "model": self.model,
            "stream": False,
            "think": False,
            "format": schema,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        }

        ollama_base = self.base_url[:-3] if self.base_url.endswith("/v1") else self.base_url
        async with self.session.post(
            f"{ollama_base}/api/chat",
            json=request_payload,
        ) as response:
            response.raise_for_status()
            payload = await response.json()

        message = payload.get("message") or {}
        content = message.get("content") or ""
        return self._parse_json(content)

    def _build_prompt(self, idea: Dict[str, Any]) -> str:
        evidence = []
        for item in (idea.get("supportingEvidence") or [])[:4]:
            evidence.append(
                {
                    "title": item.get("title"),
                    "summary": item.get("summary"),
                    "source": item.get("source"),
                    "url": item.get("url"),
                    "confidence": item.get("confidence"),
                }
            )

        compact = {
            "symbol": idea.get("symbol"),
            "companyName": idea.get("companyName"),
            "direction": idea.get("direction"),
            "topic": idea.get("topic"),
            "catalyst": idea.get("catalyst"),
            "score": idea.get("score"),
            "confidence": idea.get("confidence"),
            "reasoning": (idea.get("reasoning") or [])[:4],
            "metrics": idea.get("metrics") or {},
            "supportingEvidence": evidence,
        }
        return (
            "Analyze this stock idea using only the provided information.\n"
            "Keep it short and practical. Do not add any outside facts.\n"
            "Allowed verdict values: supports, mixed, contradicts.\n"
            "Allowed confidenceAdjustment values: increase, neutral, decrease.\n"
            f"IDEA_JSON:\n{json.dumps(compact, ensure_ascii=True)}"
        )

    @staticmethod
    def _parse_json(content: str) -> Dict[str, Any]:
        content = content.strip()
        if not content:
            return {}

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", content, re.DOTALL)
        if fenced_match:
            return json.loads(fenced_match.group(1))

        first = content.find("{")
        last = content.rfind("}")
        if first != -1 and last != -1 and last > first:
            return json.loads(content[first : last + 1])

        raise ValueError("Local model did not return parseable JSON.")
