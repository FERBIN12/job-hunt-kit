"""Check that every board slug in the presets (or given YAML files) resolves.

    python -m jobkit.verify_boards                  # all presets
    python -m jobkit.verify_boards presets/software.yaml profile/me/targets.yaml

Exit 1 if any slug is broken. A board that resolves with zero openings is fine.
"""
import sys
from pathlib import Path

import yaml

from . import boards
from .profile import ROOT


def main(argv=None) -> int:
    files = [Path(a) for a in (argv if argv is not None else sys.argv[1:])] or sorted((ROOT / "presets").glob("*.yaml"))
    bad = 0
    for f in files:
        comps = (yaml.safe_load(f.read_text()) or {}).get("companies") or []
        ok = 0
        for c in comps:
            posts, err = boards.FETCHERS[c["board"]](c["slug"], c.get("name", ""))
            if err:
                bad += 1
                print(f"  BROKEN {f.name}: {c.get('name')} ({c['board']}:{c['slug']}): {err}")
            else:
                ok += 1
        print(f"{f.name}: {ok}/{len(comps)} boards resolve")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
