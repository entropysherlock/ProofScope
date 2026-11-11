"""scope-check: a small command-line front end to the ledger."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .certificate import claim_status, statement_status
from .records import Ledger
from .schema import ValidationError, validate


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="scope-check", description=__doc__)
    p.add_argument("--ledger", default="ledger")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add", help="validate a record (JSON file or '-') and add it to the ledger")
    a.add_argument("file")
    c = sub.add_parser("check", help="validate a record file without adding it")
    c.add_argument("file")
    sub.add_parser("validate", help="validate every record in the ledger")
    s = sub.add_parser("status", help="derived status of a claim or statement id")
    s.add_argument("id")
    ls = sub.add_parser("list", help="list records")
    ls.add_argument("--type")
    args = p.parse_args(argv)
    led = Ledger(args.ledger)
    try:
        if args.cmd in ("add", "check"):
            raw = sys.stdin.read() if args.file == "-" else open(args.file, encoding="utf-8").read()
            rec = json.loads(raw)
            if args.cmd == "check":
                rec.setdefault("schema", "0.1")
                validate(rec)
                print(f"ok: {rec['id']}")
            else:
                print(f"added: {led.add(rec)}")
        elif args.cmd == "validate":
            errs = led.validate_all()
            for e in errs:
                print("ERROR", e)
            print(f"{len(led.all())} records, {len(errs)} errors")
            return 1 if errs else 0
        elif args.cmd == "status":
            fn = claim_status if args.id.startswith("claim:") else statement_status
            print(json.dumps(fn(led, args.id), indent=2))
        elif args.cmd == "list":
            for r in led.all():
                if not args.type or r["type"] == args.type:
                    extra = r.get("kind") or r.get("level") or r.get("faithfulness") or ""
                    print(f"{r['id']}\t{extra}\t{r.get('outcome', '')}")
    except (ValidationError, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
