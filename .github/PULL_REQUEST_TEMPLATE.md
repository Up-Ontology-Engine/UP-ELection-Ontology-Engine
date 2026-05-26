# Pull Request Template

## Description

Please include a detailed summary of the changes introduced in this PR. Identify the specific problem being resolved, the technical approach taken, and any key design decisions made.

---

## Type of Change

Please select the options that apply to this change:

- [ ] Bug Fix (non-breaking change which fixes an issue)
- [ ] New Feature (non-breaking change which adds functionality)
- [ ] Breaking Change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Database Schema Migration (adds or modifies SQL/Cypher database components)
- [ ] Performance Tuning or Hardening (optimizes database queries, tasks, or caching)
- [ ] Documentation Update (adds or modifies user or system guides)

---

## Technical Checklist

Before submitting this pull request, please verify that you have completed all of the following:

### Core Code Quality
- [ ] My code follows the code style guidelines defined in `CONTRIBUTING.md`.
- [ ] I have executed code formatting tools locally (`black` and `isort` for Python).
- [ ] I have self-reviewed my changes to ensure there is no unoptimized logic or nested conditional blocks.
- [ ] I have added clear, google-style docstrings and type annotations to all new functions and endpoints.

### Testing and Database
- [ ] I have run the unit test suite locally (`pytest`) and verified that all tests pass.
- [ ] I have written new test scripts in `tests/` covering the newly introduced functions or routes.
- [ ] (If applicable) I have generated a new Alembic migration using `alembic revision --autogenerate -m "description"` and checked the generated DDL manually.
- [ ] (If applicable) I have updated the Neo4j schema definitions and verified that new constraints do not violate existing graph structure integrity.

### Documentation and Links
- [ ] I have updated the relevant documentation files (e.g., `README.md`, `docs/SETUP.md`, `docs/API_REFERENCE.md`) to reflect my changes.
- [ ] I have verified that all relative links resolve correctly by executing the link checker utility.
