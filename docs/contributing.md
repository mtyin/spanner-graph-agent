# How to Contribute

We would love to accept your patches and contributions to this project.

## Before you begin

### Sign our Contributor License Agreement

Contributions to this project must be accompanied by a
[Contributor License Agreement](https://cla.developers.google.com/about) (CLA).
You (or your employer) retain the copyright to your contribution; this simply
gives us permission to use and redistribute your contributions as part of the
project.

If you or your current employer have already signed the Google CLA (even if it
was for a different project), you probably don't need to do it again.

Visit <https://cla.developers.google.com/> to see your current agreements or to
sign a new one.

### Review our Community Guidelines

This project follows [Google's Open Source Community
Guidelines](https://opensource.google/conduct/).

## Development Setup

To contribute to this project, you'll need to set up your development environment.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/mtyin/spanner-graph-agent.git
    cd spanner-graph-agent
    ```

2.  **Set up a virtual environment:**
    We recommend using a virtual environment to manage your dependencies.
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    Install the project in editable mode with the `dev` dependencies. This will install all the necessary packages for development, including `pre-commit`.
    ```bash
    pip install -e .[dev]
    ```

4.  **Install pre-commit hooks:**
    This project uses `pre-commit` to enforce code style and quality. Install the hooks to ensure your commits meet the project's standards.
    ```bash
    pre-commit install
    ```

## Running Tests

To make sure your changes don't break anything, you should run the test suite.

1.  **Install test dependencies:**
    The test dependencies are included in the `dev` extras, which you should have already installed. If not, you can install them separately:
    ```bash
    pip install .[test]
    ```

2.  **Run pytest:**
    ```bash
    pytest
    ```

## Contribution process

### Code Reviews

All submissions, including submissions by project members, require review. We
use [GitHub pull requests](https://docs.github.com/articles/about-pull-requests)
for this purpose.
