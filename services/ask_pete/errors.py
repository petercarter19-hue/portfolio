"""Typed failures for the public Ask Pete backend boundary."""

from services.ai_foundation.errors import AIFoundationError


class AskPeteError(AIFoundationError):
    """Base class for safely classifiable Ask Pete backend failures."""


class PublicSourceManifestError(AskPeteError):
    """The explicit public-AI manifest or its approved source changed."""


class AskPeteResponseError(AskPeteError):
    """A validated foundation answer could not form a public response."""


class AskPeteRequestError(AskPeteError):
    """A public request named an invalid or unauthorized context."""
