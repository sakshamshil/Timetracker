# project/timetrack/core/deploy.py
"""Deployment backends for publishing the dashboard to a static host."""

import re
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple

from ..models import SyncConfig


class DeployBackend(ABC):
    """Abstract base class for dashboard deployment backends."""

    name: str = ""

    @abstractmethod
    def deploy(self, directory: Path, prod: bool = True) -> Tuple[bool, str]:
        """Deploy ``directory`` and return ``(success, url_or_error)``."""
        raise NotImplementedError

    def preflight(self) -> Tuple[bool, str]:
        """Check that this backend can deploy before any prompts.

        Returns:
            ``(ok, message)`` — ``ok`` is False with a clear, actionable
            message when the backend is not ready (e.g. missing CLI).
        """
        return True, ""


class VercelBackend(DeployBackend):
    """Deploy the dashboard to Vercel via the ``vercel`` CLI."""

    name = "vercel"

    def __init__(self, project: str, token: Optional[str] = None, domain: Optional[str] = None):
        self.project = project
        self.token = token
        self.domain = domain

    def _vercel(self, *args: str) -> Tuple[bool, str]:
        if shutil.which("vercel") is None:
            return False, (
                "The 'vercel' CLI is not installed. Install it with "
                "'npm i -g vercel' and run 'vercel login' (or set VERCEL_TOKEN)."
            )
        env = None
        if self.token:
            import os

            env = dict(os.environ, VERCEL_TOKEN=self.token)
        try:
            result = subprocess.run(
                ["vercel", *args],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
        except Exception as e:  # pragma: no cover - defensive
            return False, f"Failed to run vercel: {e}"

        out = (result.stdout or "") + (result.stderr or "")
        if result.returncode != 0:
            return False, out.strip() or "vercel exited with an error."
        return True, out

    def preflight(self) -> Tuple[bool, str]:
        if shutil.which("vercel") is None:
            return (
                False,
                "The 'vercel' CLI is not installed. Install it first:\n"
                "  npm i -g vercel\n"
                "  then: vercel login   (or set VERCEL_TOKEN)",
            )
        return True, ""

    def deploy(self, directory: Path, prod: bool = True) -> Tuple[bool, str]:
        # Attach a custom domain on first deploy (best effort).
        if self.domain:
            ok, msg = self._vercel("domains", "add", self.domain)
            if not ok and "already" not in msg.lower():
                # Non-fatal: report but continue; verification may be manual.
                pass

        args = ["deploy", "--name", self.project, str(directory)]
        if prod:
            args.append("--prod")
        args.append("--yes")

        ok, out = self._vercel(*args)
        if not ok:
            return False, out

        url = self._extract_url(out)
        if not url and self.domain:
            url = f"https://{self.domain}"
        if not url:
            return False, "Deployed, but could not parse the URL from vercel output."
        return True, url

    @staticmethod
    def _extract_url(out: str) -> Optional[str]:
        # Vercel prints the deployment URL, but its version/telemetry
        # banner can land on the same (unterminated) line as the URL
        # (e.g. "...vercel.appVercel CLI 55.0.0..."). The deploy URL
        # always ends in ".vercel.app", so match up to that boundary;
        # the caller falls back to the custom domain when absent.
        match = re.search(r"https://[^\s'\"]*?\.vercel\.app", out)
        return match.group(0) if match else None


def get_backend(config: SyncConfig) -> DeployBackend:
    """Return the deploy backend described by ``config``.

    Args:
        config: The sync configuration.

    Returns:
        A DeployBackend instance.

    Raises:
        ValueError: if the host is not supported.
    """
    if config.host == "vercel":
        return VercelBackend(
            project=config.project, token=config.token, domain=config.domain
        )
    raise ValueError(f"Unsupported deploy host: {config.host}")
