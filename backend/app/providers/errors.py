"""Provider-neutral errors. Adapters translate SDK exceptions into these."""


class ProviderError(Exception):
    """Base class: any failure talking to an LLM or embedding provider."""

    def __init__(self, provider: str, message: str) -> None:
        super().__init__(f"{provider}: {message}")
        self.provider = provider


class ProviderQuotaError(ProviderError):
    """Rate limit or quota exhausted (HTTP 429). On the free tier this is expected."""

    def __init__(self, provider: str, message: str, retry_after_s: float | None = None) -> None:
        super().__init__(provider, message)
        self.retry_after_s = retry_after_s


class ProviderUnavailableError(ProviderError):
    """Provider unreachable, timed out, or 5xx after retries."""


class ProviderAuthError(ProviderError):
    """Missing or rejected credentials (HTTP 401/403)."""


class ProviderRequestError(ProviderError):
    """The request itself was rejected (bad model id, bad parameters, HTTP 400/404)."""


class ProviderResponseError(ProviderError):
    """The provider answered, but not with something usable (e.g. invalid JSON)."""
