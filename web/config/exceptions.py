import uuid


class WatchlistNotFoundError(Exception):
    def __init__(self, id: uuid.UUID):
        self.id = id
        super().__init__(f"Watchlist not found: {id}")


class WatchlistFileError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class TrackerRunError(Exception):
    """Base for all exceptions raised during tracker execution or output reading."""
    pass


class TrackerNotFoundError(TrackerRunError):
    pass


class TrackerLaunchError(TrackerRunError):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class TrackerTimeoutError(TrackerRunError):
    def __init__(self, timeout_seconds: int):
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Tracker timed out after {timeout_seconds}s")


class TrackerExecutionError(TrackerRunError):
    def __init__(self, exit_code: int, stderr: str):
        self.exit_code = exit_code
        self.stderr = stderr
        super().__init__(f"Tracker exited with code {exit_code}")


class RunOutputMissingError(TrackerRunError):
    pass


class RunOutputInvalidError(TrackerRunError):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class RunAlreadyInProgressError(Exception):
    pass


class NoRunsYetError(Exception):
    pass


class RunArchiveError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class SettingsValidationError(Exception):
    def __init__(self, field: str, detail: str):
        self.field = field
        self.detail = detail
        super().__init__(f"{field}: {detail}")


class HistoryRunNotFoundError(Exception):
    def __init__(self, run_id: uuid.UUID):
        self.run_id = run_id
        super().__init__(f"Run not found: {run_id}")
