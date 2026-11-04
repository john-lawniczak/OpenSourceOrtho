"""Validate the wire protocol, model choice, and consent for compatible hosts."""
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest

from orthoplan.ai_chat import answer_chat_payload, build_chat_context, scope_for
from orthoplan.ai_connectors import build_chat_provider, connector_catalog
from orthoplan.evaluation.providers.base import ModelRequest
from orthoplan.evaluation.providers.claude_code_provider import ClaudeCodeProvider
from orthoplan.model import TreatmentPlan


@pytest.mark.parametrize("kind,endpoint,model", [
    ("deepseek", "https://api.deepseek.com", "deepseek-flash"),
    ("glm", "https://api.z.ai/api/paas/v4/", "glm-5.3"),
    ("open-source", "http://localhost:1234/v1", "custom/latest"),
])
def test_compatible_hosts_use_chat_completions(monkeypatch, kind, endpoint, model):
    seen = {}

    class Client:
        def __init__(self, **kwargs):
            seen.update(kwargs)
            self.chat = SimpleNamespace(completions=self)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def create(self, **kwargs):
            seen.update(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="A geometric explanation."))])

    module = ModuleType("openai")
    module.OpenAI = Client
    monkeypatch.setitem(sys.modules, "openai", module)
    provider = build_chat_provider(kind, api_key="test-only", model=model, endpoint=endpoint)
    result = provider.complete(ModelRequest(system="system", prompt="context"))
    assert seen["base_url"] == endpoint
    assert seen["model"] == model
    assert seen["messages"] == [{"role": "system", "content": "system"}, {"role": "user", "content": "context"}]
    assert result.provider == kind
    assert result.text == "A geometric explanation."


@pytest.mark.parametrize("kind", ["deepseek", "glm"])
def test_new_providers_require_consent_and_key(kind):
    result = answer_chat_payload({"provider": kind, "message": "Explain my scans", "plan": {"id": "demo"}})
    assert not result["ok"]
    assert "acknowledge" in " ".join(result["errors"])
    with pytest.raises(ValueError, match="API key"):
        build_chat_provider(kind)
    connector = next(item for item in connector_catalog() if item.kind == kind)
    assert connector.allow_custom_model


def test_workspace_context_explains_scan_structure_and_access_limits():
    plan = TreatmentPlan.model_validate({"id": "context", "scans": [{"arch": "maxillary", "asset": {
        "id": "scan", "format": "stl", "units": "mm", "vertex_count": 30, "face_count": 10,
        "bounds": {"min_xyz": [0, 0, 0], "max_xyz": [40, 35, 15]},
    }}]})
    context = build_chat_context(plan, scope_for("full_plan"))
    scan = context["workspace"]["scans"][0]
    assert scan["format"] == "stl" and scan["faces"] == 10
    assert scan["bounds"]["max_xyz"] == (40, 35, 15)
    assert "raw mesh vertices and triangles" in context["workspace"]["capabilities"]["unavailable"]
    assert "workspace" not in build_chat_context(plan, scope_for("summary"))
    json.dumps(context)


def test_claude_cli_receives_selected_model(monkeypatch):
    commands = []
    monkeypatch.setattr("subprocess.run", lambda command, **kwargs: commands.append(command) or SimpleNamespace(stdout="Explanation"))
    ClaudeCodeProvider(model="sonnet").complete(ModelRequest(system="system", prompt="context"))
    assert commands[0][-2:] == ["--model", "sonnet"]
