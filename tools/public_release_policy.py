"""Select committed release files; dataset consent is an explicit file allowlist."""
from __future__ import annotations

import fnmatch
import json
from pathlib import PurePosixPath
import subprocess


def git(repo, *args, env=None, data=None):
    return subprocess.check_output(["git", "-C", str(repo), *args], env=env, input=data)


def release_paths(repo, source):
    policy = json.loads(git(repo, "show", f"{source}:public-release.json"))
    if policy["schema"] != 1:
        raise ValueError("Unsupported release policy")
    entries = {}
    for record in git(repo, "ls-tree", "-rz", source).split(b"\0"):
        if record:
            metadata, name = record.split(b"\t", 1)
            entries[name.decode()] = metadata.decode().split()[0]
    allowed = set()
    for name in entries:
        parts = PurePosixPath(name).parts
        if len(parts) != 3 or parts[0] != "datasets" or parts[2] != "consent.json":
            continue
        consent = json.loads(git(repo, "show", f"{source}:{name}"))
        if not consent.get("consent_acknowledged") or not consent.get("phi_removed"):
            continue
        for asset in consent["public_assets"]:
            path = PurePosixPath(asset)
            if path.is_absolute() or any(p.startswith(".") for p in path.parts) or "\\" in asset:
                raise ValueError(f"Unsafe public asset: {asset}")
            full = str(PurePosixPath(name).parent / path)
            if full not in entries:
                raise ValueError(f"Missing approved asset: {full}")
            allowed.add(full)
    selected, excluded = [], []
    for name, mode in entries.items():
        parts = PurePosixPath(name).parts
        denied = any(fnmatch.fnmatchcase(name.lower(), p.lower()) for p in policy["exclude"])
        dataset = len(parts) >= 3 and parts[0] == "datasets" and parts[1].startswith("spec-")
        if denied or (dataset and name not in allowed):
            excluded.append(name)
        else:
            if mode not in {"100644", "100755"}:
                raise ValueError(f"Release requires regular tracked files: {name}")
            selected.append(name)
    return selected, excluded
