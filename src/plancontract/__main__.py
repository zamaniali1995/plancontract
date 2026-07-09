"""Allow ``python -m plancontract`` as a CLI entry point."""

from plancontract.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
