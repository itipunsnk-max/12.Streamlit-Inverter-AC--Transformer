"""Small adapter between Streamlit session state and the pure coordinator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from .state import WorkspaceCoordinator, WorkspaceState

STATE_KEY = "workspace_state"


def initialize_workspace(release_dir: str | Path) -> WorkspaceState:
    if STATE_KEY not in st.session_state:
        st.session_state[STATE_KEY] = WorkspaceCoordinator(release_dir).initial_state()
    state = st.session_state.get(STATE_KEY)
    if not isinstance(state, WorkspaceState):
        raise RuntimeError("WorkspaceState could not be initialized")
    return state


def get_workspace_state() -> WorkspaceState:
    state = st.session_state.get(STATE_KEY)
    if not isinstance(state, WorkspaceState):
        raise RuntimeError("WorkspaceState has not been initialized by app.py")
    return state


def save_workspace_state(state: WorkspaceState) -> None:
    st.session_state[STATE_KEY] = state


def update_inputs(values: dict[str, Any]) -> WorkspaceState:
    state = get_workspace_state()
    updated = WorkspaceCoordinator(state.release_dir).save_inputs(state, values)
    save_workspace_state(updated)
    return updated


def run_workflow() -> WorkspaceState:
    state = get_workspace_state()
    updated = WorkspaceCoordinator(state.release_dir).run_workflow(state)
    save_workspace_state(updated)
    return updated
