# AGENTS.md: Speculative Agent Tool Runtime (SATR)

## 1. Project Overview & Core Mission
The Speculative Agent Tool Runtime (SATR) is a high-performance, asynchronous execution environment designed for LLM-driven code generation. Its mission is to provide a deterministic, sandboxed, and type-safe interface for agents to execute, test, and validate speculative code patches before they are committed to the main codebase.

**Core Mission:** Minimize the "hallucination-to-execution" latency by providing a robust tool-use bridge that enforces strict schema validation, environment isolation, and automated regression testing for all generated artifacts.

## 2. Local PowerShell Commands
All agents must utilize the following PowerShell Core (pwsh) commands for environment management.

*   **Setup:** `.\scripts\init.ps1 -Environment dev` (Installs venv, installs `requirements.txt`, and verifies system dependencies).
*   **Test:** `.\scripts\test.ps1 -Suite unit` (Executes `pytest` with coverage tracking; fails if < 95% coverage).
*   **Run:** `.\scripts\run.ps1 -Module <name>` (Invokes the runtime entry point with strict memory limits).
*   **Lint:** `.\scripts\lint.ps1` (Executes `mypy` for static analysis, `ruff` for formatting, and `bandit` for security auditing).

## 3. Engineering Invariants
Agents must adhere to these invariants at all times. Violation results in immediate task rejection.

*   **Zero-Placeholder Mandate:** Never use `TODO`, `FIXME`, or `...` in production code. Every function must have a complete implementation. If a feature is incomplete, the code must not be committed.
*   **Typing Strictness:** Every function signature must include PEP 484 type hints. Use `from typing import Any, Dict, List, Optional, Union`. Avoid `Any` unless absolutely necessary; prefer `Protocol` or `TypeVar` for generics.
*   **CRLF/LF Preservation:** The repository enforces `LF` line endings. Ensure your environment configuration does not auto-convert to `CRLF`.
*   **Immutability:** Prefer immutable data structures (`NamedTuple`, `dataclass(frozen=True)`) for state management.
*   **Error Handling:** Never use bare `except:` blocks. Catch specific exceptions and log them via the internal `satr.logger` module.

## 4. Self-Healing & Error Recovery Protocol
When an agent encounters a runtime failure, it must follow this protocol:

1.  **Traceback Analysis:** Capture the full stack trace from `stderr`. Do not summarize.
2.  **Contextual Inspection:** Query the `satr.diagnostics` module to retrieve the state of the local tool registry at the time of failure.
3.  **Hypothesis Generation:** Formulate a hypothesis based on the traceback (e.g., "Type mismatch in `ToolRegistry.register`").
4.  **Local Reproduction:** Create a minimal reproduction script in `tests/repro/` that triggers the error.
5.  **Fix & Verify:** Apply the fix, run the reproduction script, and execute `.\scripts\lint.ps1`.
6.  **Cleanup:** Delete the reproduction script before submitting the PR.

## 5. Definition of Done (DoD) Quality Gate
A task is only considered "Done" when the following criteria are met:

1.  **Static Analysis:** `mypy` returns zero errors with `--strict` flag enabled.
2.  **Formatting:** `ruff` reports zero violations.
3.  **Security:** `bandit` reports zero high-severity vulnerabilities.
4.  **Testing:** 100% pass rate on the unit test suite; 95%+ branch coverage.
5.  **Documentation:** All public-facing classes and methods contain Google-style docstrings.
6.  **Integration:** The feature is successfully registered in the `ToolRegistry` and passes the `smoke_test` suite.
7.  **No Dead Code:** The implementation contains no unreachable code or unused imports.