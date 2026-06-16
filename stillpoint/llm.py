"""LLM backend abstraction for Stillpoint.

Supports multiple LLM providers: Anthropic, OpenAI, OpenRouter, Google,
MiniMax, Ollama. Reads provider configuration from config/therapist.yaml.
"""

import logging
import os

from stillpoint.config import load_config

logger = logging.getLogger(__name__)


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
