from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrackerRunRequest:
    python_executable: str
    tracker_script: Path
    tracker_root: Path
    runs_dir: Path
    latest_run_file: Path
    timeout_seconds: int
