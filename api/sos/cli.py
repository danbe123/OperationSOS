"""`sos` command line entry point (completed in Task 12)."""
import sys


def main(argv: list[str] | None = None) -> int:
    print("sos CLI not yet wired", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
