# Contributing

Thanks for your interest in PlanContract.

## Development setup

```bash
git clone https://github.com/zamaniali1995/plancontract.git
cd plancontract
uv sync
```

Or use the Makefile:

```bash
make sync
```

## Quality gates

Run the same checks as CI before opening a pull request:

```bash
make ci
```

Individual targets:

```bash
make lint
make typecheck
make test
make format-check
```

Optional local hooks:

```bash
uv sync
uv run pre-commit install
uv run pre-commit run --all-files
```

## Tests

- Use pytest with the AAA pattern (arrange, act, assert).
- One primary assertion per test unless a second assertion is required for clarity.
- Mock external services; PlanContract is pure Python with no network I/O.

## Pull requests

- Keep diffs focused and reviewable.
- Update `CHANGELOG.md` for user-visible changes.
- Include tests for behavior changes.
- Ensure `make ci` passes.

## Commit style

Conventional Commits are preferred:

- `feat:` new features
- `fix:` bug fixes
- `docs:` documentation
- `test:` tests
- `ci:` CI or tooling
- `chore:` maintenance
