"""Nous Research Hermes CLI (`hermes`), signed in locally."""

import json
import re

from .. import ProviderError, run_cli, which
from ... import clis

KIND, LABEL, STREAMING = "cli", "Hermes", False
_SESSION_RE = re.compile(r"^session[_ ]id\s*:\s*\S+$", re.IGNORECASE)


def available(cfg):
    if cfg.get("bin"):
        return {"model": cfg.get("model")} if which(cfg, "hermes") else None
    return {"model": cfg.get("model")} if clis.detect("hermes") else None


def _strip_session_meta(text: str) -> str:
    lines = text.splitlines()
    while lines and (not lines[-1].strip() or _SESSION_RE.match(lines[-1].strip())):
        lines.pop()
    return "\n".join(lines).strip()


def ask(cfg, req):
    argv = [which(cfg, "hermes"), "chat", "-q", req.flat_prompt(), "--oneshot", "--quiet"]
    if cfg.get("model"):
        argv += ["-m", cfg["model"]]
    out = _strip_session_meta(run_cli(argv, req).strip())
    if out.startswith("{"):
        try:
            obj = json.loads(out)
            out = str(obj.get("result") or obj.get("text") or obj.get("response") or out).strip()
        except ValueError:
            pass
    out = _strip_session_meta(out)
    if not out:
        raise ProviderError("hermes: no answer in output")
    return out
