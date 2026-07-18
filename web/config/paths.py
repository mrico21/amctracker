from pathlib import Path


class ProjectPaths:
    def __init__(self):
        web_root = Path(__file__).parent.parent
        project_root = web_root.parent
        self.web_root: Path = web_root
        self.project_root: Path = project_root
        self.tracker_root: Path = project_root
        self.tracker_script: Path = project_root / "tracker_multiwatch.py"
        self.watchlist_file: Path = project_root / "watchlist.json"
        self.runs_dir: Path = web_root / "data" / "runs"
        self.latest_run_file: Path = web_root / "data" / "runs" / "latest.json"
        self.job_status_file: Path = web_root / "data" / "runs" / "job_status.json"
        self.settings_file: Path = web_root / "data" / "settings.json"
        self.logs_dir: Path = web_root / "logs"
        self.frontend_dist: Path = web_root / "frontend" / "dist"
