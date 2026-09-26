"""LLM planner over OpenRouter. OWNER: David.

plan(packet, *, model=None) -> contracts.PlannerResult

The model chooses an allowed config + rationale citing evidence ids from the
packet. It never computes or reports metrics. See docs/CONTRACTS.md.

Pure function: no database writes. The worker logs the call and the result.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable

from dotenv import dotenv_values, load_dotenv

from harness import contracts as C

load_dotenv()


def _env(key: str, default: str | None = None) -> str | None:
    """os.environ, but an EMPTY exported var falls back to .env (load_dotenv never overrides it)."""
    return os.environ.get(key) or dotenv_values().get(key) or default

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "anthropic/claude-sonnet-5"
FALLBACK_MODEL = "deterministic-fallback"
MAX_TOKENS = 600


def _default_client():
    from openai import OpenAI
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=_env("OPENROUTER_API_KEY"), timeout=60)


# Tests replace this with a fake client factory.
client_factory: Callable[[], Any] = _default_client


SYSTEM_PROMPT = """You are the planner for an automated EEG decoding campaign. Each turn you choose ONE next experiment, or stop.

Objective: maximize validation balanced accuracy for imagined both-fists (T1) vs both-feet (T2) on PhysioNet eegmmidb, under the CURRENT goal constraints in the packet. Chance is 0.5.

Rules:
- Propose only a config from the allowed surface (packet.surface). Every config needs method, band, window, channels, plus C for bandpower_lr or n_components for csp_lda.
- Only propose configs that are ELIGIBLE: the channel set's count must be <= goal.constraints.max_channels.
- Only propose configs that have NOT been tried. Every tried config is listed in tried; never propose one of those.
- Cite evidence by id in evidence_ids. Use only ids that appear in the packet: experiment_id values, memory_id values, or source_ids of retrieved memories.
- Never state a metric number that is not in the packet. You do not compute results; code does.
- Rationale: at most 2 sentences.
- Keep optimizing until the budget is spent. The job is relentless optimization within budget, not stopping at a good-enough result.
- stop is ONLY valid when goal.budget.remaining is 0 or no eligible untried config exists. Any other stop is rejected.
- If nearby variants of the incumbent look exhausted, explore a different method, band, or window rather than stopping. Unexplored regions of the surface are worth a budget slot.

Always answer with exactly one tool call."""


def _config_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "method": {"type": "string", "enum": list(C.METHODS)},
            "band": {"type": "string", "enum": list(C.BANDS)},
            "window": {"type": "string", "enum": list(C.WINDOWS)},
            "channels": {"type": "string", "enum": list(C.CHANNEL_SETS)},
            "C": {"type": "number", "enum": list(C.LR_C), "description": "bandpower_lr only"},
            "n_components": {"type": "integer", "enum": list(C.CSP_COMPONENTS), "description": "csp_lda only"},
        },
        "required": ["method", "band", "window", "channels"],
    }


TOOLS = [
    {"type": "function", "function": {
        "name": "propose_experiment",
        "description": "Queue one experiment from the allowed surface.",
        "parameters": {
            "type": "object",
            "properties": {
                "config": _config_schema(),
                "rationale": {"type": "string", "description": "At most 2 sentences. No metrics absent from the packet."},
                "evidence_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["config", "rationale", "evidence_ids"],
        },
    }},
    {"type": "function", "function": {
        "name": "stop",
        "description": "End the campaign: nothing eligible and untried is worth running.",
        "parameters": {
            "type": "object",
            "properties": {
                "rationale": {"type": "string"},
                "evidence_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["rationale", "evidence_ids"],
        },
    }},
]


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def packet_evidence_ids(packet: dict) -> set[str]:
    ids: set[str] = set()
    inc = packet.get("incumbent")
    if inc and inc.get("experiment_id"):
        ids.add(inc["experiment_id"])
    for row in (packet.get("pending", []) + packet.get("recent", [])
                + packet.get("leaders", []) + packet.get("laggards", [])):
        if row.get("experiment_id"):
            ids.add(row["experiment_id"])
    for m in packet.get("retrieved", []):
        if m.get("memory_id"):
            ids.add(m["memory_id"])
        ids.update(m.get("source_ids") or [])
    return ids


def validate(packet: dict, name: str, args: dict) -> tuple[dict | None, str | None]:
    """Return (normalized config or None for stop, error message or None)."""
    if name not in ("propose_experiment", "stop"):
        return None, f"unknown tool {name!r}; call propose_experiment or stop"
    ev = args.get("evidence_ids") or []
    if not isinstance(ev, list) or not all(isinstance(x, str) for x in ev):
        return None, "evidence_ids must be a list of id strings"
    unknown = sorted(set(ev) - packet_evidence_ids(packet))
    if unknown:
        return None, f"evidence ids not in the packet: {unknown}. Cite only ids that appear in the packet."
    if name == "stop":
        remaining = (packet.get("goal", {}).get("budget") or {}).get("remaining")
        if remaining == 0 or fallback_config(packet) is None:
            return None, None
        return None, (f"stop is not allowed: {remaining} experiments remain in the budget and eligible untried "
                      "configs exist. Propose one. If nearby variants look exhausted, explore a different "
                      "method, band, or window.")
    try:
        cfg = C.normalize_config(args.get("config"))
    except ValueError as e:
        return None, f"config is outside the allowed surface: {e}"
    constraints = packet["goal"]["constraints"]
    if not C.is_eligible(cfg, constraints):
        return None, (f"config uses {C.CHANNEL_COUNTS[cfg['channels']]} channels but the current goal allows "
                      f"max_channels={constraints['max_channels']}; choose an eligible channel set")
    if C.experiment_key(packet["protocol_id"], cfg) in set(packet.get("tried_keys", [])):
        return None, f"config already tried: {C.config_label(cfg)}; choose an untried config"
    return cfg, None


def fallback_config(packet: dict) -> dict | None:
    """First config in all_configs() order that is eligible and untried."""
    tried = set(packet.get("tried_keys", []))
    constraints = packet["goal"]["constraints"]
    for cfg in C.all_configs():
        if C.is_eligible(cfg, constraints) and C.experiment_key(packet["protocol_id"], cfg) not in tried:
            return cfg
    return None


# --------------------------------------------------------------------------
# LLM call
# --------------------------------------------------------------------------

def _user_message(packet: dict) -> str:
    """Every packet field except tried_keys (opaque hashes) and packet_id. `tried` carries the same
    experiments as readable labels, so the model can see what was already run."""
    view = {k: v for k, v in packet.items() if k not in ("tried_keys", "packet_id")}
    return "Evidence packet (JSON):\n" + json.dumps(view, default=str)


def _get(obj: Any, key: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    val = getattr(obj, key, None)
    if val is None:
        extra = getattr(obj, "model_extra", None) or {}
        val = extra.get(key)
    return val


def _parse(resp) -> tuple[str | None, dict, Any, str | None]:
    """Return (tool name, args, raw assistant message, error)."""
    msg = resp.choices[0].message
    calls = msg.tool_calls or []
    if not calls:
        return None, {}, msg, "no tool call returned; call propose_experiment or stop"
    call = calls[0]
    try:
        args = json.loads(call.function.arguments or "{}")
    except json.JSONDecodeError as e:
        return call.function.name, {}, msg, f"tool arguments are not valid JSON: {e}"
    return call.function.name, args, msg, None


def _repair_messages(msg, error: str) -> list[dict]:
    calls = msg.tool_calls or []
    if not calls:
        return [{"role": "assistant", "content": msg.content or ""},
                {"role": "user", "content": f"Invalid: {error} Try once more."}]
    call = calls[0]
    return [
        {"role": "assistant", "content": msg.content or "", "tool_calls": [{
            "id": call.id, "type": "function",
            "function": {"name": call.function.name, "arguments": call.function.arguments},
        }]},
        {"role": "tool", "tool_call_id": call.id, "content": f"REJECTED: {error} Try once more."},
    ]


def _estimate_tokens(messages: list[dict]) -> int:
    return len(json.dumps(messages, default=str)) // 4


def plan(packet: dict, *, model: str | None = None) -> dict:
    model = model or _env("PLANNER_MODEL", DEFAULT_MODEL)
    usage = {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    provider_usage = False
    request_id: str | None = None
    resp_model = model

    def result(action, cfg, rationale, ev, *, fallback_reason=None):
        if provider_usage:
            u = {**usage, "source": "provider"}
        else:
            u = {"input_tokens": _estimate_tokens(messages), "output_tokens": None, "cost_usd": None,
                 "source": "estimate"}
        return {
            "action": action, "config": cfg, "rationale": rationale, "evidence_ids": ev,
            "model": FALLBACK_MODEL if fallback_reason else resp_model, "request_id": request_id,
            "usage": u, "fallback_used": fallback_reason is not None, "fallback_reason": fallback_reason,
        }

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": _user_message(packet)}]

    if fallback_config(packet) is None:
        return result("stop", None, "No eligible untried config remains on the allowed surface.", [])
    if (packet.get("goal", {}).get("budget") or {}).get("remaining") == 0:
        return result("stop", None, "Experiment budget is spent.", [])

    last_error = "not called"
    try:
        client = client_factory()
        for attempt in range(2):
            resp = client.chat.completions.create(
                model=model, messages=messages, tools=TOOLS, tool_choice="required",
                max_tokens=MAX_TOKENS, extra_body={"usage": {"include": True}},
            )
            request_id = getattr(resp, "id", None) or request_id
            resp_model = getattr(resp, "model", None) or resp_model
            u = getattr(resp, "usage", None)
            if u is not None:
                provider_usage = True
                usage["input_tokens"] += _get(u, "prompt_tokens") or 0
                usage["output_tokens"] += _get(u, "completion_tokens") or 0
                usage["cost_usd"] += float(_get(u, "cost") or 0.0)
            name, args, msg, err = _parse(resp)
            if err is None:
                cfg, err = validate(packet, name, args)
            if err is None:
                rationale = str(args.get("rationale", ""))
                ev = list(args.get("evidence_ids") or [])
                if name == "stop":
                    return result("stop", None, rationale, ev)
                return result("propose", cfg, rationale, ev)
            last_error = err
            if attempt == 0:
                messages += _repair_messages(msg, err)
    except Exception as e:  # network, auth, provider errors: never raise into the worker
        last_error = f"{type(e).__name__}: {e}"

    cfg = fallback_config(packet)
    reason = f"planner failed validation or call after repair: {last_error}"
    return result("propose", cfg, f"Deterministic fallback: first eligible untried config ({C.config_label(cfg)}).",
                  [], fallback_reason=reason)
