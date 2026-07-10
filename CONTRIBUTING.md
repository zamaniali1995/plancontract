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

## Releasing to PyPI

Releases are published from GitHub Actions using [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (no API tokens in CI).

### One-time PyPI setup

1. Open [plancontract publishing settings](https://pypi.org/manage/project/plancontract/settings/publishing/)
2. **Add a new publisher** → GitHub
3. Set:
   - **Owner:** `zamaniali1995`
   - **Repository name:** `plancontract`
   - **Workflow name:** `python-publish.yml`
   - **Environment name:** `pypi`
4. Save

### One-time GitHub setup

1. Repo → **Settings** → **Environments** → **New environment** → name it `pypi`
2. (Optional) Add required reviewers for manual approval before publish
3. Push `.github/workflows/python-publish.yml` to `main`

### Publish a new version

1. Bump version in **both** `pyproject.toml` and `src/plancontract/__init__.py`
2. Update `CHANGELOG.md`
3. Run `make ci`
4. Commit, push to `main`, then tag and push:

```bash
git tag v0.1.1
git push origin v0.1.1
```

5. Watch the [Publish workflow](https://github.com/zamaniali1995/plancontract/actions/workflows/python-publish.yml)

The tag (`v0.1.1`) must match `pyproject.toml` version (`0.1.1`). PyPI does not allow re-uploading the same version.

Optional GitHub Release (notes for users):

```bash
gh release create v0.1.1 --title "v0.1.1" --notes-file CHANGELOG.md
```
