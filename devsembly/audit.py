from __future__ import annotations

from contextvars import ContextVar, Token

AuditActor = tuple[str, str]
DEFAULT_AUDIT_ACTOR: AuditActor = ("service", "genesis-control-plane")
_current_actor: ContextVar[AuditActor] = ContextVar(
    "devsembly_audit_actor", default=DEFAULT_AUDIT_ACTOR
)


def current_audit_actor() -> AuditActor:
    return _current_actor.get()


def set_current_audit_actor(actor_type: str, actor_id: str) -> Token[AuditActor]:
    return _current_actor.set((actor_type, actor_id))


def reset_current_audit_actor(token: Token[AuditActor]) -> None:
    _current_actor.reset(token)
