## Engineering Plan: Rotary Phone Audio Guestbook

## Background
The Rotary Phone Audio Guestbook project aims to create a unique and nostalgic experience for capturing audio messages, memories, and well-wishes. By repurposing a classic rotary dial telephone, this system will allow users to interact with a familiar vintage interface to leave personalized voice recordings. The project is designed to run on a Raspberry Pi, making it a compact and versatile solution for events, installations, or personal use.

The core functionality involves an interactive audio experience. When a user picks up the handset, they will be greeted with a pre-recorded message. After the greeting, the system will prompt them to leave their own message, which will be recorded and stored digitally. The goal is to seamlessly blend the charm of analog hardware with modern digital recording and storage capabilities, creating a delightful and memorable way for people to share their thoughts and voices. Future enhancements may include options for message playback and remote access to the collected audio archive.

**Target Audience:** Software engineers tasked with implementing and maintaining the project.  
**Python Version:** 3.10+ (development on 3.12)  
**OS:** Raspberry Pi OS (Bullseye or later)  
**CI/CD:** GitHub Actions  
**Documentation Hosting:** GitHub Pages / Read the Docs  
**Branching Model:** Feature-branch workflow
* * *

### 1. Project Structure & Folder Layout
    
    
    rotary-guestbook/
    ├── docs/                   # Sphinx documentation source
    │   ├── _static/
    │   ├── _templates/
    │   ├── conf.py
    │   ├── index.rst
    │   ├── architecture.rst   # diagrams & design overview
    │   └── usage.rst          # user & deployment guides
    │
    ├── src/                    # Production code
    │   └── rotary_guestbook/
    │       ├── __init__.py
    │       ├── app.py          # AppController entry point
    │       ├── phone.py        # PhoneEventHandler
    │       ├── door.py         # DoorSensorHandler (optional)
    │       ├── audio.py        # AudioManager + backends
    │       ├── archive.py      # MessageArchiver
    │       ├── config.py       # ConfigManager
    │       ├── health.py       # SystemHealthMonitor
    │       ├── web.py          # WebInterface (Flask)
    │       ├── logger.py       # Logging module configuration
    │       └── errors.py       # Custom error definitions and handlers
    │
    ├── tests/                  # Unit & integration tests
    │   ├── unit/               # Mocked dependencies
    │   └── integration/        # Hardware-in-the-loop tests
    │
    ├── .github/
    │   └── workflows/
    │       └── ci.yml          # Lint, tests, coverage, docstring checks
    │
    ├── .flake8                 # Flake8 configuration
    ├── pyproject.toml          # Black, isort, mypy configs
    ├── setup.cfg               # Packaging metadata
    ├── requirements.txt        # Pin runtime deps
    ├── config.yaml.example     # Default config
    ├── start.sh                # Boot script
    └── README.md
    

* * *

### 2. Coding Guidelines & Style

- **Formatter:** Black (via pre-commit)
- **Import Sorting:** isort (aligned with Black)
- **Linting:** Flake8 (max line length 88)
- **Typing:** mypy with strict flags (`--strict`)
- **Docstring Coverage:** interrogate with 100% coverage enforced
- **IDE:** Pylance for VS Code with `python.analysis.typeCheckingMode = 'strict'`
- **Pre-commit Hooks:**

    - `black --check`

    - `isort --check-only`

    - `flake8`

    - `mypy`

    - `interrogate --min-coverage 100`

**Enforce via GitHub Actions** on push/PR.
* * *

### 3. Docstring Conventions (Google style, Sphinx-compatible)

Every public module, class, and function must include docstrings:
    
    
    """
    Brief one-line summary.
    
    Longer description if needed.
    
    Args:
        param1 (str): Description of param1.
        param2 (int): Description of param2.
    
    Returns:
        bool: What the return value means.
    
    Raises:
        ValueError: When X condition fails.
    """
    

- Use `:param name:`, `:return:`, `:raises:` tags in `.rst` if manually documenting.
- Sphinx `autodoc` will pull directly from code.
* * *

### 4. Logging & Error Handling Modules

- **`src/rotary_guestbook/logger.py`**
    - Implements centralized logging setup for the application.
    - Configures a root logger with both rotating file handler and console output.
    - Driven by `ConfigManager` (level, format, file, rotation).
    - Fully tested with 100% coverage and robust error handling.
- **`src/rotary_guestbook/errors.py`**

    - Defines custom exceptions (e.g., `ConfigError`, `AudioError`, `HardwareError`).

    - Centralizes error messages and codes.
- **Error Handling Strategy:**

    - Catch and log exceptions at boundaries (e.g., in `AppController.run()`).

    - Provide user-friendly error messages in web UI.

    - Trigger `SystemHealthMonitor` alerts on critical failures.
* * *

### 5. Documentation & Diagrams

Within `docs/architecture.rst` include:

- **Class diagrams** (Mermaid or embedded images) for each component.
- **Sequence diagrams** for: recording flow, playback flow, AP access flow, health-check flow.

Within `docs/usage.rst`:

- **Hardware wiring diagram** reference
- **Installation & setup** steps
- **Configuration** explanation (`config.yaml` fields)
- **Running services** (`systemd` units)

Build docs with:
    
    
    cd docs && make html
    

* * *

### 6. Testing & Coverage

- **Unit Tests:** in `tests/unit` using `pytest` + `pytest-mock` to mock GPIO, subprocess, filesystem.
- **Integration Tests:** in `tests/integration`, run on Pi with real GPIO & audio interface.
- **End-to-End (E2E):** Optional `tests/e2e` using a Raspberry Pi testbed; use `pexpect` to run `app.py` and simulate events.
- **Coverage Enforcement:** `pytest --cov=rotary_guestbook --cov-fail-under=90` and `interrogate --min-coverage 100`.

Sample `ci.yml` steps:
    
    
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with: {python-version: '3.12'}
    - run: pip install -r requirements.txt
    - run: pip install -e .
    - run: pytest --maxfail=1 --disable-warnings --cov=rotary_guestbook --cov-fail-under=90
    - run: flake8
    - run: mypy src/rotary_guestbook
    - run: interrogate --min-coverage 100
    

* * *

### 7. CI/CD & Deployment

- **GitHub Actions** handles lint, tests, coverage, docstring checks on PRs.
- **Releases:** Tag versions (v1.0.0, etc.); build a `wheel` and publish to PyPI if desired.
- **Systemd Service Files:** Place in `deploy/` folder; document how to `cp` and `systemctl enable`.
- **Auto-update:** Provide an `update.sh` script that `git pull && pip install -e . && systemctl restart ...`.
* * *

### 8. Maintenance & Extensibility

- **Feature modules:** Follow OCP by coding to interfaces (e.g. `AudioBackend`, `StorageBackend`).
- **Dependency Injection:** Pass in `ConfigManager`, `GPIOHandler`, etc., to `AppController`.
- **Plugin hooks:** Allow third-party extensions (e.g. new storage sync) by defining clear abstract base classes.
- **Versioning:** Follow semver; maintain changelog in `CHANGELOG.md`.
* * *

**This plan ensures any engineer can build, test, and maintain a production-grade, robust rotary phone audio guestbook with full docstring coverage, logging, error handling, and CI/CD best practices.**

# Project Context (Update)

- The configuration system (`config.py`) is now implemented using Pydantic v2 models for all sections (audio, hardware, web, logging, system).
- All configuration is strictly validated at load time, and errors are reported clearly.
- The example config file (`config.yaml.example`) matches the new structure and validation rules.
- 100% test coverage for the configuration system, with comprehensive unit tests.
- No linter or deprecation warnings remain for this module.