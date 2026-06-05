<!--
PR title must start with a type tag, e.g.:
  Fix: reject zero movement caps before division
Tags: Add | Fix | Change | Remove | Refactor | Docs | Test | Perf | Build
See CONTRIBUTING.md.
-->

## Type

<!-- Tick exactly one; it should match your PR title tag. -->

- [ ] Add (new feature/rule/endpoint)
- [ ] Fix (bug fix)
- [ ] Change (behavior change)
- [ ] Remove (deletion)
- [ ] Refactor (no behavior change)
- [ ] Docs
- [ ] Test
- [ ] Perf
- [ ] Build (CI/packaging/deps)

## Summary

<!-- What does this change and why? Link any related issue (Closes #123). -->

## How it was tested

<!-- Commands run and what you observed. -->

## Checklist

- [ ] PR title uses a type tag (`Add:`, `Fix:`, ...).
- [ ] `pytest -q` passes.
- [ ] `python tools/check_maintainability.py --strict` passes.
- [ ] `cd ui && node --test` passes.
- [ ] New behavior and any fixed regression have tests.
- [ ] No patient data; no verdict language; mechanics stay in deterministic rules.
- [ ] Docs updated if behavior or provider behavior changed.
