from __future__ import annotations  # lazy annotations

from typing import Optional


class ThinkerWaveError(Exception):
    def __init__(self, code: str, message: str, status: Optional[int] = None) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


class InvalidKeyError(ThinkerWaveError): ...
class AccountDisabledError(ThinkerWaveError): ...
class NotInvitedError(ThinkerWaveError): ...
class CreditExhaustedError(ThinkerWaveError): ...
class NotFoundError(ThinkerWaveError): ...
class InvalidRequestError(ThinkerWaveError): ...
class UnavailableError(ThinkerWaveError): ...


class RateLimitedError(ThinkerWaveError):
    def __init__(self, code: str, message: str, status: Optional[int] = None, retry_after: Optional[float] = None):
        super().__init__(code, message, status)
        self.retry_after = retry_after


class RunLimitError(RateLimitedError): ...


_BY_CODE = {"invalid_key": InvalidKeyError, "account_disabled": AccountDisabledError,
            "not_invited": NotInvitedError, "credit_exhausted": CreditExhaustedError,
            "not_found": NotFoundError, "invalid_request": InvalidRequestError,
            "rate_limited": RateLimitedError, "run_limit": RunLimitError, "unavailable": UnavailableError}


def error_for(status: int, body: object, headers: dict) -> ThinkerWaveError:
    err = body.get("error") if isinstance(body, dict) else None
    code = err.get("code") if isinstance(err, dict) else None
    message = err.get("message") if isinstance(err, dict) else None
    cls = _BY_CODE.get(code or "", ThinkerWaveError)
    msg = message or f"HTTP {status}"
    if issubclass(cls, RateLimitedError):
        ra = headers.get("retry-after")
        return cls(code or "rate_limited", msg, status, float(ra) if ra and ra.replace(".", "", 1).isdigit() else None)
    return cls(code or "error", msg, status)
