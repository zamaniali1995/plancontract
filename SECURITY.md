# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | yes |

## Reporting a vulnerability

Please report security issues privately. Do not open a public GitHub issue for vulnerabilities.

1. Email the maintainer with a description of the issue and steps to reproduce.
2. Include affected versions and any suggested mitigations.
3. Allow reasonable time for a fix before public disclosure.

PlanContract is a schema and validation library with no network, authentication, or persistence layer. Most issues are expected to be denial-of-service via malformed input or logic bugs in validation.

## Scope

In scope:

- Validation bypasses that accept structurally invalid plans
- Dependency graph logic errors (cycles, incorrect waves)
- CLI crashes on malformed JSON that should be handled gracefully

Out of scope:

- Issues in downstream agent frameworks or LLM outputs
- General prompt injection in consuming applications
