"""Command-line entry points; commands load only their required modules."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("analyze", "figures", "run"),
                        help="Recompute saved results, render figures, or run local inference")
    if not args or args[0] in ("-h", "--help"):
        parser.print_help()
        return
    command = parser.parse_args(args[:1]).command
    if command == "analyze":
        from .analysis import main as analyze
        return analyze(args[1:])
    if command == "figures":
        from .figures import main as figures
        return figures(args[1:])
    run = argparse.ArgumentParser(prog="querygrid run", description="Run the fixed P1 or E study from local, licensed inputs.")
    run.add_argument("--study", choices=("p1", "e"), required=True)
    run.add_argument("--manifest", type=Path, default=Path("data/manifests/plastic_nut.csv"))
    run.add_argument("--data-root", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--checkpoint", type=Path, required=True)
    run.add_argument("--dinov2-repo", type=Path, required=True)
    run.add_argument("--device", default="cuda")
    run.add_argument("--max-wall-seconds", type=float, required=True,
                     help="Explicit runtime budget; stopping does not count as a completed experiment")
    options = run.parse_args(args[1:])
    from .inference import run_study
    result = run_study(**vars(options))
    print(json.dumps(result, indent=2, allow_nan=False))
