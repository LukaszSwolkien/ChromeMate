# AI Agent Instructions

---

# Code Generation

## Principles

1. **Minimal changes** - Only implement what's requested, nothing more
2. **Follow existing patterns** - Match codebase style, conventions, and abstractions
3. **Edit over create** - Prefer modifying existing files over creating new ones
4. **Reuse abstractions** - Use existing utilities, don't duplicate functionality

## Avoid Over-Engineering

- Don't add features not explicitly requested
- Don't add error handling for scenarios that can't happen
- Don't create abstractions for one-time use
- Don't refactor surrounding code unless asked
- Don't add "improvements" beyond the task

---

# Code Review

When reviewing code, check for these issues:

| Issue | Look For | Fix |
|-------|----------|-----|
| Magic numbers | Hardcoded values in logic | Extract to named constants |
| Duplicated logic | Same code in multiple places | Extract to shared function/module |
| Dead code | Unused parameters, variables, imports | Remove |
| Missing validation | User inputs not checked | Add boundary checks |
| Resource leaks | Objects not cleaned up | Add proper cleanup/disposal |
| Repeated initialization | Same setup on every call | Cache or initialize once |
| Poor error handling | Silent failures, missing logs | Add logging and user feedback |
| Placeholders | `yourusername`, `TODO`, `FIXME`, `TBD`, `HACK` | Replace with real values or remove |
| Hardcoded names | Domain names, usernames, paths in logic | Move to config or CLI options |
| Stale README | New features/options not documented | Update README.md with current usage |
| Verbose README | Redundant examples, excessive text | Keep concise - one example per concept |

**Prioritize issues by impact**: security > correctness > performance > maintainability.

---

# Debugging

1. **Reproduce first** - Confirm the issue exists and understand exact conditions
2. **Add logging** - Trace data flow at key points (inputs, transformations, outputs)
3. **Verify assumptions** - Check paths, values, conditions that "should" work
4. **Check platform differences** - File paths, bundling, environment variables
5. **Fix root cause** - Don't mask symptoms with defensive code

---

# Refactoring

| Goal | Action |
|------|--------|
| Remove duplication | Extract shared logic to dedicated module |
| Eliminate magic numbers | Move to named constants in central location |
| Reduce coupling | Make dependencies explicit, optional sections truly optional |
| Simplify | Remove unused code, merge redundant abstractions |

**Keep changes minimal** - refactor only what's needed, don't over-engineer.

---

# Unit Tests

## Before Writing Tests

1. **Understand domain constraints** - Ask about valid value ranges, physical limits, business rules
2. **Review existing tests** - Check for duplicates before creating new tests
3. **Identify testable logic** - Focus on code with behavior, not trivial getters/constants

---

## Test Requirements

Every test you create MUST:

- [ ] Use **realistic inputs** that can occur in production
- [ ] Test **actual logic**, not trivial code (getters, constants)
- [ ] Be **unique** - no overlap with existing test coverage
- [ ] Have **meaningful assertions** that verify behavior
- [ ] Follow naming: `test_<unit>_<scenario>_<expected_outcome>`
- [ ] Use **Arrange-Act-Assert** structure

---

## Self-Review Before Submitting

After creating tests, verify each one:

1. Can these input values actually occur in the real system?
2. Does this test duplicate existing coverage?
3. Does this test verify meaningful behavior?
4. Are assertions testing the right thing?

If you find issues, fix them before presenting the tests.

# Commits

Format: `<type>: <summary>` (one-liner, max 72 chars)

| Type | Use |
|------|-----|
| feat | New feature |
| fix | Bug fix |
| refactor | Code change (no new feature, no bug fix) |
| test | Add or fix tests |
| docs | Documentation only |

---

# Documentation

## Principles

1. **No emojis** - Professional tone only
2. **Concise** - One sentence per concept, no filler text
3. **No duplication** - Don't repeat information across sections
4. **Actionable** - Every section should help the reader do something
5. **Concrete examples** - Show, don't just tell

## Structure

- Use headers to organize content hierarchically
- Use tables for structured data (parameters, mappings, comparisons)
- Use bullet lists for sequential steps or related items
- Use code blocks for examples with realistic values

## Avoid

- Verbose explanations when a table suffices
- Repeating the same information in different words
- Generic placeholder values - use self-documenting names (e.g., `OldProfile` not `Profile 1`)
- Documentation that describes obvious code behavior
- Examples that don't make sense in domain context (verify the example workflow is realistic)

---

# Releasing

## GitHub Release Workflow

1. **Update version** in project config (e.g., `pyproject.toml`, `package.json`, `Cargo.toml`)
2. **Commit** version bump: `git commit -am "chore: bump version to X.Y.Z"`
3. **Tag**: `git tag vX.Y.Z`
4. **Push**: `git push origin main --tags`
5. **Create release** at `https://github.com/<owner>/<repo>/releases/new`
   - Select the tag
   - Add release notes (see template below)
   - Attach build artifacts
   - Publish

## Release Notes Template

```markdown
## <Project> vX.Y.Z

<One-line summary of the release>

### Installation
<Platform-specific installation steps>

### Changes
- <Change 1>
- <Change 2>

### Breaking Changes
- <If any>
```

## Unsigned macOS Binary Notes

For unsigned binaries, include Gatekeeper bypass instructions:
```
Bypass Gatekeeper (first run):
- Right-click → Open → Open, or
- `xattr -d com.apple.quarantine <binary>`
```