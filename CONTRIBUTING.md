# Contributing to Ticket Tally

Thank you for your interest in contributing to **Ticket Tally**!

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Development Setup

1. **Fork and Clone the Repository:**
   ```bash
   git clone https://github.com/<your-username>/Trial_Ticket_Tally.git
   cd Trial_Ticket_Tally
   ```

2. **Create a Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Migrations & Tests:**
   ```bash
   flask db upgrade
   pytest -v
   ```

## Pull Request Guidelines

- Create a focused topic branch for your changes (e.g. `feat/feature-name` or `fix/issue-name`).
- Ensure all tests pass (`pytest`) before opening a PR.
- Provide a clear PR title and description explaining the problem and solution.
- Keep commits atomic and well-documented.
