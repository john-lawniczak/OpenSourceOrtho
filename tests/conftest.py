"""Never read or mutate the maintainer's local research review history in tests."""

import pytest


@pytest.fixture(autouse=True)
def isolate_research_store(tmp_path, monkeypatch):
    monkeypatch.setenv("ORTHOPLAN_RESEARCH_STORE", str(tmp_path / "research"))
