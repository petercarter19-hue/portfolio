"""Typed failures for the shared AI boundary."""


class AIFoundationError(RuntimeError):
    """Base class for a safely classifiable foundation failure."""


class SourceAuthorizationError(AIFoundationError):
    """A source was stale, from another subject, or outside request scope."""


class GroundingValidationError(AIFoundationError):
    """An answer's citation linkage or support-state structure was invalid."""


class AnswerContractError(AIFoundationError):
    """A provider response did not satisfy the bounded structured contract."""


class ExecutionLimitError(AIFoundationError):
    """A request exceeded a product-neutral execution safeguard."""


class ProviderUnavailableError(AIFoundationError):
    """The configured provider could not complete the bounded request."""
