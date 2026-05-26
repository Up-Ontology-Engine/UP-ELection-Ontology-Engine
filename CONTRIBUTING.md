# Contributing Guidelines

This document outlines the contribution workflows, coding conventions, testing guidelines, and commit standards for the UP Vidhan Sabha Election Ontology Engine development team.

---

## Code Quality and Standards

All code contributions must meet our quality criteria before they can be merged.

### Python Code Style
We adhere strictly to the PEP 8 specification.
- **Formatting:** Code formatting is managed via `black` and `isort`.
- **Typing:** Type hints must be used on all new function signatures and class definitions.
- **Complexity:** Avoid deep nesting. Prefer flat guards and immediate exit blocks. Keep functions focused on a single responsibility.
- **Docstrings:** All public functions, modules, and API route handlers must include descriptive docstrings using the Google docstring format.

### TypeScript and React (Frontend) Code Style
The Next.js 14 application is structured using the React App Router model.
- **Formatting:** Enforced via `Prettier` and `ESLint` using the project's configurations.
- **Components:** Functional components must be typed using TypeScript.
- **casing:** Directory structures and file names under `app/` must be lowercase (e.g., `booths/page.tsx` and `heatmap/page.tsx`). Component names must use PascalCase (e.g., `BoothCard`).
- **caching:** When data-fetching on client views, leverage ISR (`revalidate`) configurations to avoid database overload.

---

## Local Development Workflow

To submit changes, set up your local environment and run the test suite:

### 1. Set Up Your Environment
Ensure you have Python 3.11+ installed and configure your virtual environment:

```bash
# Clone the repository
git clone git@github.com:Aryan-en/UP-ELection-Ontology-Engine.git
cd UP-ELection-Ontology-Engine

# Initialize the virtual environment
python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
```

### 2. Run Quality Checks Locally
Before submitting a pull request, verify that your code passes all lint and unit tests:

```bash
# Run the test suite
pytest

# Format the Python code
black pipeline/ backend/ tests/
isort pipeline/ backend/ tests/

# Run the frontend linter
cd frontend/nextjs
npm run lint
```

---

## Git and Branching Guidelines

### Branch Naming Conventions
Create descriptive branch names prefixing the ticket type:
- `feature/` for new capabilities (e.g., `feature/booth-metrics-export`)
- `bugfix/` for resolving issues (e.g., `bugfix/bhashini-error-handling`)
- `hotfix/` for critical production hotfixes (e.g., `hotfix/pgbouncer-connection-timeout`)
- `refactor/` for non-functional codebase restructuring (e.g., `refactor/pipeline-aggregation`)

### Pull Request (PR) Requirements
*   **Keep PRs Small:** Target a single feature or bug per pull request. Large, multi-thousand-line PRs will be rejected.
*   **Test Coverage:** Any new logic or database functions must be accompanied by matching unit or integration tests under the `tests/` directory.
*   **Passing CI:** The automated CI/CD pipeline (GitHub Actions) runs security scans (Trivy), database migration checks, and unit tests. All checks must pass before review.
