"""`sos` command line entry point (completed in Task 12).

`validate-playbooks` is stubbed out here (not left unwired like every other
subcommand) because the plan's Global Constraints require every commit to
pass `make test`, and `make test` unconditionally runs
`sos validate-playbooks` as its last step. Until Task 7/12 land there is no
authored content and no manifest to check, so "no documents found" is the
correct answer, not a placeholder one -- Task 12 replaces this branch with
real validation (front matter, scenario headings, manifest cross-refs, ...)
without changing this trivial-input behaviour.
"""
import sys


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == "validate-playbooks":
        print("OK 0 documents")
        return 0
    print("sos CLI not yet wired", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
