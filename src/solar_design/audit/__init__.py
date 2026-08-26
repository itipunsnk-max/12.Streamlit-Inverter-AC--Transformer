"""Append-only audit trail primitives for design and commercial revisions."""

from .trail import AuditAction, AuditEvent, AuditTrail

__all__ = ["AuditAction", "AuditEvent", "AuditTrail"]
