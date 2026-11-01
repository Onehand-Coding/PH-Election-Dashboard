from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import requests

from ph_election_dashboard import geo

ProviderKind = Literal["openai", "anthropic", "gemini"]


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class Provider:
    name: str
    kind: ProviderKind
    base_url: str
    api_key_env: str | None
    default_model: str
    headers: dict[str, str] = field(default_factory=dict)
    key_required: bool = True

    def api_key(self, override: str | None = None) -> str | None:
        if override and override.strip():
            return override.strip()
        if self.api_key_env:
            value = os.getenv(self.api_key_env, "").strip()
            if value:
                return value
        return None

    def configured(self, override: str | None = None) -> bool:
        return not self.key_required or bool(self.api_key(override))


BUILTIN_PROVIDERS: dict[str, Provider] = {
    "gemini": Provider(
        "gemini",
        "gemini",
        "https://generativelanguage.googleapis.com/v1beta",
        "GEMINI_API_KEY",
        "gemini-2.5-flash",
    ),
    "openai": Provider(
        "openai",
        "openai",
        "https://api.openai.com/v1",
        "OPENAI_API_KEY",
        "gpt-4o-mini",
    ),
    "openrouter": Provider(
        "openrouter",
        "openai",
        "https://openrouter.ai/api/v1",
        "OPENROUTER_API_KEY",
        "openai/gpt-4o-mini",
        headers={
            "HTTP-Referer": ("https://github.com/Onehand-Coding/PH-Election-Dashboard"),
            "X-Title": "PH Election Dashboard",
        },
    ),
    "groq": Provider(
        "groq",
        "openai",
        "https://api.groq.com/openai/v1",
        "GROQ_API_KEY",
        "llama-3.3-70b-versatile",
    ),
    "anthropic": Provider(
        "anthropic",
        "anthropic",
        "https://api.anthropic.com/v1",
        "ANTHROPIC_API_KEY",
        "claude-3-5-haiku-latest",
    ),
    "ollama": Provider(
        "ollama",
        "openai",
        "http://localhost:11434/v1",
        None,
        "llama3.1",
        key_required=False,
    ),
}


@dataclass
class SummaryResult:
    text: str
    used_fallback: bool
    error: str | None = None


def load_custom_providers(path: Path) -> dict[str, Provider]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    items = payload.get("providers", []) if isinstance(payload, dict) else []
    providers: dict[str, Provider] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            name = str(item["name"]).strip()
            kind = str(item["kind"]).strip().lower()
            base_url = str(item["base_url"]).strip()
            model = str(item["model"]).strip()
        except KeyError:
            continue
        if not name or kind not in ("openai", "anthropic", "gemini"):
            continue
        key_env = item.get("api_key_env") or None
        providers[name] = Provider(
            name=name,
            kind=kind,  # type: ignore[arg-type]
            base_url=base_url,
            api_key_env=str(key_env) if key_env else None,
            default_model=model,
            headers={
                str(key): str(value)
                for key, value in (item.get("headers") or {}).items()
            },
            key_required=bool(key_env),
        )
    return providers


def available_providers(custom_path: Path | None = None) -> dict[str, Provider]:
    providers = dict(BUILTIN_PROVIDERS)
    if custom_path is not None:
        providers.update(load_custom_providers(custom_path))
    return providers


def _location_filters_text(location_filters: dict[str, str] | None) -> str:
    if not location_filters:
        return ""
    parts = [
        f"{key}: {value}" for key, value in sorted(location_filters.items()) if value
    ]
    return ", ".join(parts)


def build_stats(
    frame: pd.DataFrame,
    election_type: str,
    position_filter: str | None = None,
    location_filters: dict[str, str] | None = None,
) -> dict[str, Any]:
    if frame.empty:
        return {
            "election_type": election_type,
            "position_filter": position_filter,
            "location_filters": location_filters or {},
            "rows": 0,
            "total_votes": 0,
            "positions": [],
            "top_candidates": [],
            "party_shares": [],
            "region_totals": [],
            "map_mapped": 0,
            "map_unmapped": 0,
        }

    levels = geo.available_map_levels(frame)
    if levels:
        mapped_frame, unmapped_labels = geo.aggregate_for_map(frame, levels[0])
        map_mapped = len(mapped_frame)
        map_unmapped = len(unmapped_labels)
    else:
        map_mapped = 0
        map_unmapped = 0

    top = frame.sort_values("total_votes", ascending=False).head(5)
    party_shares = []
    party_frame = frame.dropna(subset=["party"])
    if not party_frame.empty:
        totals = party_frame.groupby("party")["total_votes"].sum()
        total_votes = int(totals.sum())
        if total_votes:
            party_shares = [
                {
                    "party": str(party),
                    "votes": int(votes),
                    "share": round(int(votes) / total_votes * 100, 1),
                }
                for party, votes in totals.sort_values(ascending=False).items()
            ]

    region_totals = []
    if "region" in frame.columns:
        region_frame = frame.dropna(subset=["region"])
        if not region_frame.empty:
            region_totals = [
                {"region": str(region), "votes": int(votes)}
                for region, votes in region_frame.groupby("region")["total_votes"]
                .sum()
                .sort_values(ascending=False)
                .items()
            ]

    return {
        "election_type": election_type,
        "position_filter": position_filter,
        "location_filters": location_filters or {},
        "rows": int(len(frame)),
        "total_votes": int(frame["total_votes"].sum()),
        "positions": sorted(frame["position"].dropna().astype(str).unique().tolist()),
        "top_candidates": [
            {
                "candidate": str(record["candidate_name"]),
                "position": str(record["position"]),
                "party": (None if pd.isna(record["party"]) else str(record["party"])),
                "votes": int(record["total_votes"]),
            }
            for record in top.to_dict("records")
        ],
        "party_shares": party_shares,
        "region_totals": region_totals,
        "map_mapped": map_mapped,
        "map_unmapped": map_unmapped,
    }


def build_prompt(stats: dict[str, Any]) -> str:
    location = _location_filters_text(stats.get("location_filters"))
    lines = [
        "You are writing a short, neutral summary of Philippine election sample data.",
        "Use only the aggregate statistics below. Do not invent candidates, "
        "parties, or totals.",
        "Write 4 to 6 sentences in plain English. Mention the leading "
        "candidates, party shares, and any close race.",
        "",
        f"Election level: {stats.get('election_type', 'unknown')}",
        f"Position filter: {stats.get('position_filter') or 'All'}",
        f"Location filter: {location or 'None'}",
        f"Rows: {stats.get('rows', 0)}",
        f"Total votes: {stats.get('total_votes', 0):,}",
        "",
        "Top candidates:",
    ]
    for item in stats.get("top_candidates", []):
        lines.append(
            f"- {item['candidate']} ({item['position']}, "
            f"{item['party'] or 'no party'}): {item['votes']:,} votes"
        )
    if stats.get("party_shares"):
        lines.append("")
        lines.append("Party vote shares:")
        for item in stats["party_shares"]:
            lines.append(f"- {item['party']}: {item['share']}%")
    if stats.get("region_totals"):
        lines.append("")
        lines.append("Regional totals:")
        for item in stats["region_totals"][:10]:
            lines.append(f"- {item['region']}: {item['votes']:,} votes")
    return "\n".join(lines)


def fallback_summary(stats: dict[str, Any]) -> str:
    if stats.get("rows", 0) == 0:
        return "No data is available for the current selection."
    lines = [
        f"**{str(stats.get('election_type', 'election')).title()} summary**",
    ]
    context = []
    if stats.get("position_filter") and stats["position_filter"] != "All":
        context.append(f"position {stats['position_filter']}")
    location = _location_filters_text(stats.get("location_filters"))
    if location:
        context.append(location)
    if context:
        lines.append("- Context: " + "; ".join(context))
    lines.extend(
        [
            f"- Rows: {stats['rows']:,}",
            f"- Total votes: {stats['total_votes']:,}",
        ]
    )
    if stats.get("top_candidates"):
        lines.append("- Top candidates:")
        for item in stats["top_candidates"][:3]:
            party = f" ({item['party']})" if item.get("party") else ""
            lines.append(f"  - {item['candidate']}{party}: {item['votes']:,} votes")
    if stats.get("party_shares"):
        lines.append("- Party vote share:")
        for item in stats["party_shares"][:4]:
            lines.append(f"  - {item['party']}: {item['share']}%")
    top = stats.get("top_candidates", [])
    if len(top) >= 2 and stats["total_votes"]:
        margin = top[0]["votes"] - top[1]["votes"]
        if margin / stats["total_votes"] < 0.05:
            lines.append(
                f"- Close race: the top two are separated by {margin:,} votes."
            )
    lines.append(
        f"- Map coverage: {stats.get('map_mapped', 0)} mapped label(s), "
        f"{stats.get('map_unmapped', 0)} unmapped label(s)."
    )
    return "\n".join(lines)


def redact(text: str, secret: str | None) -> str:
    if not secret:
        return text
    return text.replace(secret, "***")


def _post(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: int,
) -> dict[str, Any]:
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise ProviderError(type(exc).__name__) from exc
    if response.status_code >= 400:
        raise ProviderError(f"HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderError("Invalid JSON response") from exc


def _generate(
    provider: Provider,
    model: str,
    prompt: str,
    api_key: str | None,
    timeout: int,
) -> str:
    base = provider.base_url.rstrip("/")
    headers = {"Content-Type": "application/json", **provider.headers}

    if provider.kind == "openai":
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You summarize election data accurately and neutrally."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 700,
        }
        data = _post(
            f"{base}/chat/completions",
            headers=headers,
            payload=payload,
            timeout=timeout,
        )
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Malformed OpenAI-compatible response") from exc

    if provider.kind == "anthropic":
        if api_key:
            headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        payload = {
            "model": model,
            "max_tokens": 700,
            "system": "You summarize election data accurately and neutrally.",
            "messages": [{"role": "user", "content": prompt}],
        }
        data = _post(
            f"{base}/messages",
            headers=headers,
            payload=payload,
            timeout=timeout,
        )
        try:
            return str(data["content"][0]["text"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Malformed Anthropic response") from exc

    if provider.kind == "gemini":
        if not api_key:
            raise ProviderError("Missing API key")
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 700,
            },
        }
        data = _post(
            f"{base}/models/{model}:generateContent?key={api_key}",
            headers=headers,
            payload=payload,
            timeout=timeout,
        )
        try:
            return str(data["candidates"][0]["content"]["parts"][0]["text"]).strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("Malformed Gemini response") from exc

    raise ProviderError(f"Unsupported provider kind: {provider.kind}")


def generate_summary(
    frame: pd.DataFrame,
    election_type: str,
    provider: Provider,
    model: str,
    position_filter: str | None = None,
    location_filters: dict[str, str] | None = None,
    api_key_override: str | None = None,
    timeout: int = 30,
) -> SummaryResult:
    stats = build_stats(frame, election_type, position_filter, location_filters)
    fallback = fallback_summary(stats)
    api_key = provider.api_key(api_key_override)
    if not provider.configured(api_key_override):
        return SummaryResult(fallback, used_fallback=True)
    try:
        text = _generate(provider, model, build_prompt(stats), api_key, timeout)
    except ProviderError as exc:
        return SummaryResult(
            fallback,
            used_fallback=True,
            error=redact(str(exc), api_key),
        )
    if not text:
        return SummaryResult(fallback, used_fallback=True, error="Empty response")
    return SummaryResult(text, used_fallback=False)
