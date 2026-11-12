"""Opt-in live protocol check using synthetic text only; never loads a case."""

import argparse
import os

from orthoplan.ai_connectors import build_chat_provider
from orthoplan.evaluation.providers.base import ModelRequest


def smoke(provider, *, model=None):
    prefix = provider.upper().replace("-", "_")
    adapter = build_chat_provider(
        provider,
        model=model or os.environ.get(f"{prefix}_MODEL"),
        api_key=os.environ.get(f"{prefix}_API_KEY"),
        endpoint=os.environ.get(f"{prefix}_ENDPOINT"),
    )
    response = adapter.complete(
        ModelRequest(
            system="Return only the requested test token.",
            prompt="Return ORTHO_PROTOCOL_OK. This is a synthetic connectivity test.",
        )
    )
    if "ORTHO_PROTOCOL_OK" not in response.text:
        raise RuntimeError("Provider response did not contain the test token")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Explicitly allow an external request and provider charges",
    )
    parser.add_argument(
        "--provider",
        required=True,
        choices=["openai", "deepseek", "glm", "open-source", "claude-code"],
    )
    parser.add_argument("--model")
    args = parser.parse_args()
    if not args.live:
        parser.error("--live is required; no request sent")
    try:
        smoke(args.provider, model=args.model)
    except Exception as exc:
        # No upstream bodies, prompts, URLs, keys or chained exceptions in logs.
        print(f"{args.provider}: FAIL ({type(exc).__name__})")
        return 1
    print(f"{args.provider}: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
