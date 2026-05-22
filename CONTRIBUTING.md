# Contributing to TAGS

We welcome contributions from the research community! Whether you are reporting a bug, suggesting a new metric, or improving the documentation, your help is appreciated.

## How to Contribute

### Reporting Bugs
If you find a bug, please open a [GitHub Issue](https://github.com/saidfathalla/tags/issues) and include:
* A brief description of the issue.
* The RDF file you were processing (or a small sample).
* The error message or unexpected behavior.

### Pull Requests
1. **Fork** the repository.
2. **Create a branch** for your feature: `git checkout -b feature/new-metric`.
3. **Write code** following the existing style.
4. **Run tests** to ensure no regressions: `pytest`.
5. **Submit a Pull Request** describing your changes.

### Code Style
* Please keep code clean and documented.
* If adding a new metric, ensure you update the `analyze_knowledge_graph` function in `tags.py` and document it in the README.

## Community Expectations
This project follows a professional and inclusive conduct. Please be respectful in all discussions and pull request reviews.
