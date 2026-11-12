"""Actionable OpenAI errors without exposing upstream bodies or credentials."""


def openai_error_message(error: Exception) -> str:
    status = getattr(error, "status_code", None)
    kind = type(error).__name__
    code = getattr(error, "code", None)
    if status == 401 and code == "invalid_api_key":
        return ("OpenAI reports invalid_api_key (401). In Connection settings, paste a complete, "
                "active API key. Use the secret value shown when creating the key at platform.openai.com.")
    if status == 401 or kind == "AuthenticationError":
        return ("OpenAI rejected authentication (401). In Settings → OpenAI, paste a complete, "
                "active API key from platform.openai.com. If it still fails, check the key's "
                "project access and IP restrictions, or create a replacement key.")
    if status == 403:
        return "OpenAI denied access (403). Check your API key's project permissions and account access."
    if status == 404 or code == "model_not_found":
        return "OpenAI could not access the selected model. Check its model ID and your project's model access in Settings."
    if status == 429:
        if code in {"insufficient_quota", "credit_balance_exhausted", "organization_spend_limit_exceeded",
                    "project_spend_limit_exceeded", "organization_usage_limit_reached"}:
            return "OpenAI API credits or usage limits were reached. Check API billing and project limits before retrying."
        return "OpenAI rate limit reached (429). Wait briefly before retrying."
    if kind in {"APIConnectionError", "APITimeoutError", "TimeoutError"}:
        return "Could not reach OpenAI in time. Check your connection and retry."
    return "OpenAIProvider request failed; check the selected model and request settings, then retry."
