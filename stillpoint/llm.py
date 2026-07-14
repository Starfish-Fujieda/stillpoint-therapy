"""LLM backend abstraction for Stillpoint.

Supports multiple LLM providers: Anthropic, OpenAI, OpenRouter, Google,
MiniMax, DeepSeek, Ollama. Reads provider configuration from
config/therapist.yaml.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from stillpoint.config import load_config

logger = logging.getLogger(__name__)

# DeepSeek peak-hour pricing (announced 2026-06-30, effective with the
# official V4 launch in mid-July 2026): API calls during 09:00–12:00
# and 14:00–18:00 Beijing time (UTC+8), every day, are billed at DOUBLE
# the off-peak rate (e.g. V4 Pro output: 6 → 12 yuan / US$1.77 per
# million tokens). Applies to all V4 models.
# Sources: DeepSeek subscriber email as reported by SCMP and TechNode,
# 2026-06-30.
_DEEPSEEK_PEAK_WINDOWS_BEIJING = ((9, 12), (14, 18))
_BEIJING_TZ = timezone(timedelta(hours=8))


def is_deepseek_peak_hours(now: datetime | None = None) -> bool:
    """Return True if `now` falls in DeepSeek's peak-pricing windows.

    Peak windows are 09:00–12:00 and 14:00–18:00 Beijing time (UTC+8),
    daily. During these windows DeepSeek bills V4 API usage at twice
    the off-peak rate.

    Args:
        now: Timezone-aware datetime to check. Defaults to the current
            time.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    beijing = now.astimezone(_BEIJING_TZ)
    return any(
        start <= beijing.hour < end
        for start, end in _DEEPSEEK_PEAK_WINDOWS_BEIJING
    )


def deepseek_peak_warning(llm_config: dict | None = None) -> str:
    """Return a cost warning when DeepSeek is in use during peak hours.

    Returns an empty string when the configured provider is not
    DeepSeek or the current time is off-peak.
    """
    if llm_config is None:
        try:
            llm_config = get_llm_config()
        except Exception:
            return ""
    if llm_config.get("provider") != "deepseek":
        return ""
    if not is_deepseek_peak_hours():
        return ""
    return (
        "⚠️ **DeepSeek peak-hour pricing is in effect** — API usage "
        "is currently billed at **2× the off-peak rate**. Peak hours "
        "are 09:00–12:00 and 14:00–18:00 Beijing time "
        f"({_deepseek_peak_windows_jst()} JST), daily. Chatting "
        "outside these windows costs half as much."
    )


def _deepseek_peak_windows_jst() -> str:
    """Render the peak windows in Japan Standard Time (UTC+9).

    The user is in Japan, so the banner shows the windows in JST
    (Beijing time + 1 hour), e.g. "10:00–13:00 and 15:00–19:00".
    """
    jst = timezone(timedelta(hours=9))
    parts = []
    for start, end in _DEEPSEEK_PEAK_WINDOWS_BEIJING:
        start_jst = datetime(2000, 1, 1, start, 0, tzinfo=_BEIJING_TZ).astimezone(jst)
        end_jst = datetime(2000, 1, 1, end, 0, tzinfo=_BEIJING_TZ).astimezone(jst)
        parts.append(f"{start_jst:%H:%M}–{end_jst:%H:%M}")
    return " and ".join(parts)


def get_llm_config() -> dict:
    """Load LLM configuration from therapist config.

    Returns:
        Dictionary with provider, model, and API key env var name.
    """
    try:
        config = load_config("therapist.yaml")
        return config.get("llm", {})
    except FileNotFoundError:
        # Default to Anthropic
        return {
            "provider": "anthropic",
            "model": "claude-sonnet-4-20250514",
            "api_key_env": "ANTHROPIC_API_KEY",
        }


def send_message(
    system_prompt: str,
    messages: list[dict],
    llm_config: dict | None = None,
) -> str:
    """Send a message to the LLM and return the response.

    Args:
        system_prompt: The system prompt (therapist persona).
        messages: List of message dicts with 'role' and 'content'.
        llm_config: Optional LLM config dict. If None, loaded from config.

    Returns:
        The LLM's response text.

    Raises:
        ValueError: If the provider is not supported.
        RuntimeError: If the API call fails.
    """
    if llm_config is None:
        llm_config = get_llm_config()

    provider = llm_config.get("provider", "anthropic")

    if provider == "anthropic":
        return _send_anthropic(system_prompt, messages, llm_config)
    elif provider == "openai":
        return _send_openai(system_prompt, messages, llm_config)
    elif provider == "google":
        return _send_google(system_prompt, messages, llm_config)
    elif provider == "ollama":
        return _send_ollama(system_prompt, messages, llm_config)
    elif provider == "openrouter":
        return _send_openrouter(system_prompt, messages, llm_config)
    elif provider == "minimax":
        return _send_minimax(system_prompt, messages, llm_config)
    elif provider == "deepseek":
        return _send_deepseek(system_prompt, messages, llm_config)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _send_anthropic(system_prompt: str, messages: list[dict], config: dict) -> str:
    """Send a message via the Anthropic API."""
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "anthropic package not installed. Install with: pip install anthropic"
        )

    api_key_env = config.get("api_key_env", "ANTHROPIC_API_KEY")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(
            f"API key not found. Set the {api_key_env} environment variable."
        )

    model = config.get("model", "claude-sonnet-4-20250514")
    max_tokens = config.get("max_tokens", 4096)

    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text
    except anthropic.APIError as e:
        logger.error("Anthropic API error: %s", e)
        raise RuntimeError(f"Anthropic API error: {e}") from e


def _send_openai(system_prompt: str, messages: list[dict], config: dict) -> str:
    """Send a message via the OpenAI API."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "openai package not installed. Install with: pip install openai"
        )

    api_key_env = config.get("api_key_env", "OPENAI_API_KEY")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(
            f"API key not found. Set the {api_key_env} environment variable."
        )

    model = config.get("model", "gpt-4o")
    base_url = config.get("base_url")

    client = OpenAI(api_key=api_key, base_url=base_url)

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        response = client.chat.completions.create(
            model=model,
            messages=full_messages,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error("OpenAI API error: %s", e)
        raise RuntimeError(f"OpenAI API error: {e}") from e


def _send_google(system_prompt: str, messages: list[dict], config: dict) -> str:
    """Send a message via the Google Generative AI API."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError(
            "google-generativeai package not installed. "
            "Install with: pip install google-generativeai"
        )

    api_key_env = config.get("api_key_env", "GOOGLE_API_KEY")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(
            f"API key not found. Set the {api_key_env} environment variable."
        )

    model_name = config.get("model", "gemini-pro")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,
    )

    # Convert messages to Google's format
    history = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})

    try:
        chat = model.start_chat(history=history[:-1] if history else [])
        last_msg = history[-1]["parts"][0] if history else ""
        response = chat.send_message(last_msg)
        return response.text
    except Exception as e:
        logger.error("Google AI error: %s", e)
        raise RuntimeError(f"Google AI error: {e}") from e


def _send_openrouter(system_prompt: str, messages: list[dict], config: dict) -> str:
    """Send a message via OpenRouter (OpenAI-compatible with attribution headers)."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "openai package not installed. Install with: pip install openai"
        )

    api_key_env = config.get("api_key_env", "OPENROUTER_API_KEY")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(
            f"API key not found. Set the {api_key_env} environment variable."
        )

    model = config.get("model", "anthropic/claude-sonnet-4-5")
    base_url = config.get("base_url", "https://openrouter.ai/api/v1")

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        default_headers={
            "HTTP-Referer": "https://github.com/Starfish-Fujieda/stillpoint-therapy",
            "X-Title": "Stillpoint Therapy",
        },
    )

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        response = client.chat.completions.create(
            model=model,
            messages=full_messages,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error("OpenRouter error: %s", e)
        raise RuntimeError(f"OpenRouter error: {e}") from e


def _send_deepseek(system_prompt: str, messages: list[dict], config: dict) -> str:
    """Send a message via the DeepSeek API (OpenAI-compatible).

    DeepSeek serves an OpenAI-format Chat Completions API on
    https://api.deepseek.com. ``base_url`` and ``model`` are
    overridable in ``therapist.yaml``.

    Peak-hour note: DeepSeek bills 2× during 09:00–12:00 and
    14:00–18:00 Beijing time. The chat UI shows a banner (see
    ``deepseek_peak_warning``); this function also logs a warning so
    non-UI callers are informed.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "openai package not installed. Install with: pip install openai"
        )

    api_key_env = config.get("api_key_env", "DEEPSEEK_API_KEY")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(
            f"API key not found. Set the {api_key_env} environment variable."
        )

    model = config.get("model", "deepseek-chat")
    base_url = config.get("base_url", "https://api.deepseek.com")

    if is_deepseek_peak_hours():
        logger.warning(
            "DeepSeek peak-hour pricing in effect (09:00–12:00 / "
            "14:00–18:00 Beijing time): this request is billed at 2x "
            "the off-peak rate."
        )

    client = OpenAI(api_key=api_key, base_url=base_url)

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        response = client.chat.completions.create(
            model=model,
            messages=full_messages,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error("DeepSeek error: %s", e)
        raise RuntimeError(f"DeepSeek error: {e}") from e


def _send_minimax(system_prompt: str, messages: list[dict], config: dict) -> str:
    """Send a message via the MiniMax API (OpenAI-compatible).

    MiniMax serves an OpenAI-format Chat Completions API on
    https://api.minimax.io/v1. The ``base_url`` and ``model`` are
    overridable in ``therapist.yaml`` so a wrong default is a one-line
    config fix, not a code change.
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "openai package not installed. Install with: pip install openai"
        )

    api_key_env = config.get("api_key_env", "MINIMAX_API_KEY")
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise RuntimeError(
            f"API key not found. Set the {api_key_env} environment variable."
        )

    model = config.get("model", "MiniMax-M3")
    base_url = config.get("base_url", "https://api.minimax.io/v1")

    client = OpenAI(api_key=api_key, base_url=base_url)

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        response = client.chat.completions.create(
            model=model,
            messages=full_messages,
            # MiniMax M3 emits reasoning by default. ``reasoning_split: True``
            # surfaces it in a separate ``reasoning_content`` field on the
            # response message, leaving ``.content`` as the final answer only.
            # That keeps the chat surface clean and lets callers (or a future
            # "show thinking" expander) reach the reasoning on demand.
            # See https://platform.minimax.io/docs/api-reference/text-openai-api
            extra_body={"reasoning_split": True},
        )
        return _format_minimax_response(response, config)
    except Exception as e:
        logger.error("MiniMax error: %s", e)
        raise RuntimeError(f"MiniMax error: {e}") from e


def _format_minimax_response(response, config: dict) -> str:
    """Format a MiniMax response, optionally including the model's reasoning.

    The ``reasoning_split: True`` extra_body keeps the model's chain-of-thought
    in a separate ``reasoning_content`` field on the message. By default we
    return only the final answer (``content``) so the chat surface stays clean.
    If the user opts in via ``config['show_thinking'] = True``, the reasoning
    is included as a collapsible ``<details>`` markdown block ahead of the
    final answer — the user can expand it to inspect the AI's reasoning,
    or leave it collapsed for a clean view.

    If the model didn't emit reasoning (some calls don't, even on M3), the
    toggle has no effect and we return the plain content.
    """
    message = response.choices[0].message
    content = message.content or ""

    if not config.get("show_thinking"):
        return content

    reasoning = getattr(message, "reasoning_content", None)
    if not reasoning:
        return content

    return (
        "<details>\n"
        "<summary>💭 Model thinking</summary>\n\n"
        f"{reasoning.strip()}\n\n"
        f"</details>\n\n{content}"
    )


def _send_ollama(system_prompt: str, messages: list[dict], config: dict) -> str:
    """Send a message via a local Ollama instance."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "openai package not installed (needed for Ollama). "
            "Install with: pip install openai"
        )

    base_url = config.get("base_url", "http://localhost:11434/v1")
    model = config.get("model", "llama3")

    client = OpenAI(api_key="ollama", base_url=base_url)
    full_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        response = client.chat.completions.create(
            model=model,
            messages=full_messages,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error("Ollama error: %s", e)
        raise RuntimeError(f"Ollama error: {e}") from e
