"""Shared, product-neutral contracts for PeerSlate AI experiences.

The paid, spend-capable Azure Foundry adapter is deliberately NOT re-exported
here.  Product modules import this package at web-app startup, and a paid
adapter should not be loaded into the running site just to reach the shared
contracts.  Callers that genuinely need it import it explicitly:

    from services.ai_foundation.azure_foundry import (
        AzureFoundryResponsesProvider, SpendLedger,
    )
"""

from .citation_validator import validate_grounded_answer
from .codec import parse_grounded_answer
from .contracts import (
    AIRequest,
    AnswerClaim,
    AnswerKind,
    AnswerState,
    Audience,
    Citation,
    GroundedAnswer,
    HandoffProposal,
    HandoffReason,
    Purpose,
    SourceVersion,
)
from .evaluation import AnswerExpectation, EvaluationResult, evaluate_answer
from .gateway import AIFoundationGateway, AIProvider, GatewayResult
from .limits import ExecutionLimits
from .observability import AITrace, TraceOutcome

__all__ = [
    "AIFoundationGateway",
    "AIProvider",
    "AIRequest",
    "AITrace",
    "AnswerClaim",
    "AnswerExpectation",
    "AnswerKind",
    "AnswerState",
    "Audience",
    "Citation",
    "EvaluationResult",
    "ExecutionLimits",
    "GatewayResult",
    "GroundedAnswer",
    "HandoffProposal",
    "HandoffReason",
    "Purpose",
    "SourceVersion",
    "TraceOutcome",
    "evaluate_answer",
    "parse_grounded_answer",
    "validate_grounded_answer",
]
