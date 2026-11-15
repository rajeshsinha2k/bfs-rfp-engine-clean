import pytest
import sqlite3
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver
from backend.app.db import database
from backend.app.agents import graph
from backend.app import config, main


@pytest.fixture(autouse=True)
def isolated_test_environment(tmp_path, monkeypatch):
    """Isolates SQLite DB, LangGraph checkpoints, and workspaces per test."""
    test_db = tmp_path / "test_rfp_engine.db"
    test_checkpoint_db = tmp_path / "test_checkpoints.db"
    test_workspaces = tmp_path / "rfp_workspaces"
    test_workspaces.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(database, "DB_PATH", test_db)
    monkeypatch.setattr(config, "WORKSPACES_DIR", test_workspaces)
    monkeypatch.setattr(graph, "WORKSPACES_DIR", test_workspaces)
    monkeypatch.setattr(main, "WORKSPACES_DIR", test_workspaces)
    monkeypatch.setattr(graph, "CHECKPOINT_DB", test_checkpoint_db)

    # Re-compile orchestrator bound to the temporary checkpoint database
    test_orchestrator = graph.build_rfp_graph()
    monkeypatch.setattr(graph, "rfp_orchestrator", test_orchestrator)
    monkeypatch.setattr(main, "rfp_orchestrator", test_orchestrator)

    database.init_db()
    yield
