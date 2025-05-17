**Phase 0: Project Setup & CI Foundation**

1.  **Initialize Project Structure:**
    *   Create the directory structure as outlined in `context.md`:
        *   `rotary-guestbook/`
        *   `docs/` (with subdirectories)
        *   `src/guestbook/`
        *   `tests/unit/`
        *   `tests/integration/`
        *   `.github/workflows/`
    *   Create placeholder files like `README.md`, `.flake8`, `pyproject.toml`, `setup.cfg`, `requirements.txt`, `config.yaml.example`, and `start.sh`.

2.  **Setup `pyproject.toml`:**
    *   Configure `black`, `isort`, and `mypy` settings.
    *   Example for `mypy` (to enforce strictness from the start):
        ```toml
        [tool.mypy]
        python_version = "3.10" # Or your target Python version
        warn_return_any = true
        warn_unused_configs = true
        disallow_untyped_defs = true
        disallow_incomplete_defs = true
        check_untyped_defs = true
        no_implicit_optional = true
        strict_equality = true
        strict_optional = true
        # Add other strict flags as desired
        ```

3.  **Setup `.flake8`:**
    *   Configure `max-line-length = 88` and any other Flake8 plugins or settings.

4.  **Setup Pre-commit Hooks:**
    *   Create a `.pre-commit-config.yaml` file.
    *   Add hooks for `black`, `isort`, `flake8`, `mypy`, and `interrogate` as specified in `context.md`. This will ensure code quality from the very first commit.

5.  **Basic CI/CD Pipeline (`.github/workflows/ci.yml`):**
    *   Implement a basic GitHub Actions workflow that:
        *   Checks out the code.
        *   Sets up Python.
        *   Installs dependencies (from `requirements.txt` and `setup.cfg` for editable install).
        *   Runs linters and type checkers (pre-commit hooks essentially: `black --check`, `isort --check-only`, `flake8`, `mypy src/guestbook tests`).
        *   Runs `interrogate --min-coverage 100` (initially, you might set a lower coverage goal for `interrogate` and `pytest --cov` until code is written).
        *   Includes a placeholder for running tests (e.g., `pytest tests`).

**Phase 1: Core Services Implementation & Testing**

For each module below, follow this pattern:
    a.  Create the file (e.g., `src/guestbook/errors.py`).
    b.  Define the classes/functions with full docstrings (Google style).
    c.  Write unit tests in the corresponding `tests/unit/` file (e.g., `tests/unit/test_errors.py`). Aim for high test coverage.
    d.  Ensure all pre-commit checks pass.

1.  **`src/guestbook/errors.py`:**
    *   **Goal:** Define custom application exceptions.
    *   **Implementation:** Create base `GuestbookError` and specific errors like `ConfigError`, `AudioError`, `HardwareError`, `ArchiveError`.
    *   **Testing (`tests/unit/test_errors.py`):** Test that exceptions can be raised and caught, and that they store messages correctly.

2.  **`src/guestbook/config.py` (ConfigManager):**
    *   **Goal:** Manage application configuration.
    *   **Implementation:**
        *   Class `ConfigManager` to load settings from a YAML file (e.g., `config.yaml`).
        *   Use Pydantic or dataclasses for typed configuration models to validate and provide easy access to settings.
        *   Method to load config, perhaps with defaults from `config.yaml.example`.
        *   Properties or methods to access specific configuration values.
    *   **Testing (`tests/unit/test_config.py`):**
        *   Test loading valid and invalid config files.
        *   Test default value handling.
        *   Test access to different config sections and values.
        *   Mock filesystem operations (`open`, `yaml.safe_load`).

3.  **`src/guestbook/logger.py`:**
    *   **Goal:** Centralized logging setup.
    *   **Implementation:**
        *   Function `setup_logging(config: ConfigManager)` that configures a root logger.
        *   Use `logging.config.dictConfig` or manually configure handlers (console, rotating file).
        *   Logging levels, format, and file paths should be driven by `ConfigManager`.
    *   **Testing (`tests/unit/test_logger.py`):**
        *   Test that `setup_logging` configures handlers and formatters as expected.
        *   Verify log messages are written to the correct destinations (can use `unittest.mock.patch` on `logging` handlers or check for log file creation/content if simple).
        *   Test different log levels.

**Phase 2: Core Application Logic & Interfaces**

1.  **`src/guestbook/app.py` (AppController - Initial Skeleton):**
    *   **Goal:** Application entry point and orchestrator.
    *   **Implementation (Initial):**
        *   Define `AppController` class.
        *   Constructor `__init__` should type hint dependencies: `ConfigManager`, and placeholders for `PhoneEventHandler`, `AudioManager`, etc.
        *   Implement a basic `run()` method that, for now, might just initialize dependencies and log that it's starting.
    *   **Testing (`tests/unit/test_app.py`):**
        *   Test `AppController` instantiation with mocked dependencies.
        *   Test the basic `run()` method (e.g., ensure it calls a `start()` method on a mock service).

2.  **Define Core Interfaces (Abstract Base Classes - ABCs):**
    *   Based on `context.md` and potential needs, create ABCs in appropriate files or a new `interfaces.py` if preferred.
    *   **`src/guestbook/audio.py` (AudioBackend Interface):**
        *   `AbstractAudioBackend(abc.ABC)`:
            *   `@abc.abstractmethod def play_greeting(self): pass`
            *   `@abc.abstractmethod def start_recording(self, filename: str): pass`
            *   `@abc.abstractmethod def stop_recording(self): pass`
            *   `@abc.abstractmethod def convert_to_mp3(self, input_wav: str, output_mp3: str): pass` (or similar processing methods)
    *   **`src/guestbook/archive.py` (StorageBackend Interface):**
        *   `AbstractStorageBackend(abc.ABC)`:
            *   `@abc.abstractmethod def save_message(self, audio_file_path: str, metadata: dict) -> str: pass` (returns message ID or path)
            *   `@abc.abstractmethod def get_message(self, message_id: str) -> Optional[Tuple[str, dict]]: pass` (returns audio_file_path, metadata)
            *   `@abc.abstractmethod def list_messages(self) -> List[dict]: pass`
    *   **`src/guestbook/phone.py` (PhoneHardwareInterface - if abstracting hardware interaction):**
        *   `AbstractPhoneHardware(abc.ABC)`:
            *   `@abc.abstractmethod def wait_for_hook_event(self) -> HookEvent: pass` (e.g., `HookEvent.OFF_HOOK`, `HookEvent.ON_HOOK`)
            *   `@abc.abstractmethod def is_receiver_off_hook(self) -> bool: pass`
            *   Define `HookEvent` Enum.
    *   **Testing:** For ABCs, tests aren't typically about direct functionality but might involve ensuring concrete classes implement all abstract methods (though `mypy` and Python's runtime will catch this).

**Phase 3: Implementing Core Feature Modules**

For each module, implement the concrete class based on its interface (if applicable) and `context.md`.

1.  **`src/guestbook/audio.py` (AudioManager & Concrete Backend):**
    *   **Goal:** Manage audio playback and recording.
    *   **Implementation:**
        *   `AudioManager` class:
            *   Takes an `AbstractAudioBackend` and `ConfigManager` in its constructor.
            *   Orchestrates audio operations (e.g., play welcome, record message).
        *   Concrete `PyAudioBackend(AbstractAudioBackend)` (or `AlsaBackend`, `SounddeviceBackend`):
            *   Implements the methods defined in `AbstractAudioBackend` using a specific audio library (e.g., PyAudio, python-sounddevice). This will involve interacting with system audio.
            *   Handles audio format conversions if necessary (e.g., WAV to MP3 using `pydub` or `subprocess` calls to `ffmpeg`/`lame`).
    *   **Testing (`tests/unit/test_audio.py`):**
        *   Test `AudioManager` logic by mocking the `AbstractAudioBackend`.
        *   Test the concrete backend. This is trickier as it interacts with hardware/OS.
            *   Mock the underlying audio libraries (e.g., `pyaudio.PyAudio`, `sounddevice.Stream`).
            *   For subprocess calls (like `ffmpeg`), mock `subprocess.run`.
            *   Focus on the logic *within* your backend class (e.g., correct parameters passed to underlying libraries, file handling).
        *   Integration tests (`tests/integration/test_audio_hw.py`) will be crucial here, run on the actual Raspberry Pi.

2.  **`src/guestbook/archive.py` (MessageArchiver & Concrete Backend):**
    *   **Goal:** Save and retrieve audio messages.
    *   **Implementation:**
        *   `MessageArchiver` class:
            *   Takes an `AbstractStorageBackend` and `ConfigManager`.
            *   Manages metadata, generates filenames/IDs.
        *   Concrete `FileSystemStorageBackend(AbstractStorageBackend)`:
            *   Saves messages to the local filesystem in a structured way (e.g., `recordings/<timestamp>.mp3`).
            *   May store metadata in a simple way (e.g., JSON file alongside, or in filename if simple).
    *   **Testing (`tests/unit/test_archive.py`):**
        *   Test `MessageArchiver` logic with a mocked `AbstractStorageBackend`.
        *   Test `FileSystemStorageBackend` by mocking filesystem calls (`os.path.exists`, `open`, `os.makedirs`, `shutil.move`, etc.) using `unittest.mock.patch` or `pyfakefs`.

3.  **`src/guestbook/phone.py` (PhoneEventHandler & Concrete Hardware):**
    *   **Goal:** Handle phone hardware events (hook switch, rotary dial).
    *   **Implementation:**
        *   `PhoneEventHandler` class:
            *   Takes `AbstractPhoneHardware`, `AudioManager`, `MessageArchiver`, `ConfigManager`.
            *   Contains the state machine logic:
                *   Waiting for off-hook.
                *   Playing greeting.
                *   Waiting for hang-up to start recording (or a specific dial sequence).
                *   Recording.
                *   Playing thank you/saving message.
                *   Returning to on-hook state.
        *   Concrete `RPiGPIOPhoneHardware(AbstractPhoneHardware)` (or similar):
            *   Uses `RPi.GPIO` (or `gpiozero`) to detect hook switch events.
            *   (Optional) Implement rotary dial decoding if part of the project scope. This is complex and might be a separate module.
    *   **Testing (`tests/unit/test_phone.py`):**
        *   Test `PhoneEventHandler` state transitions and interactions with mocked `AudioManager`, `MessageArchiver`, and `AbstractPhoneHardware`. This will be a complex state machine to test thoroughly.
        *   Test `RPiGPIOPhoneHardware` by mocking the `RPi.GPIO` library.
        *   Integration tests (`tests/integration/test_phone_hw.py`) for actual GPIO interaction on the Pi.

**Phase 4: Web Interface, Health Monitoring, and Application Assembly**

1.  **`src/guestbook/web.py` (WebInterface - Flask):**
    *   **Goal:** Provide a web UI for message playback, system status.
    *   **Implementation:**
        *   Flask app.
        *   Routes for listing messages, playing messages (streaming or direct link), viewing system health.
        *   Inject `MessageArchiver`, `SystemHealthMonitor`, `ConfigManager`.
    *   **Testing (`tests/unit/test_web.py`):**
        *   Use Flask's test client (`app.test_client()`).
        *   Mock the injected services.
        *   Test routes return correct status codes, content types, and basic HTML structure or JSON data.

2.  **`src/guestbook/health.py` (SystemHealthMonitor):**
    *   **Goal:** Monitor system health (disk space, audio device status, etc.).
    *   **Implementation:**
        *   `SystemHealthMonitor` class.
        *   Methods to check various aspects (e.g., `check_disk_space()`, `check_audio_interface()`).
        *   Integrates with logging and potentially the web UI.
        *   Takes `ConfigManager`.
    *   **Testing (`tests/unit/test_health.py`):**
        *   Mock system calls (`shutil.disk_usage`, `subprocess.run` for `aplay -l` or similar).
        *   Test logic for determining health status based on mocked return values.

3.  **`src/guestbook/app.py` (AppController - Full Implementation):**
    *   **Goal:** Tie all components together.
    *   **Implementation:**
        *   In `__init__`, instantiate all concrete dependencies (or have them passed in from a main script/`start.sh`).
            *   `config = ConfigManager()`
            *   `setup_logging(config)`
            *   `audio_backend = PyAudioBackend(config)` (or similar)
            *   `audio_manager = AudioManager(audio_backend, config)`
            *   `storage_backend = FileSystemStorageBackend(config)`
            *   `message_archiver = MessageArchiver(storage_backend, config)`
            *   `phone_hardware = RPiGPIOPhoneHardware(config)` (or whatever hardware interface you use)
            *   `phone_event_handler = PhoneEventHandler(phone_hardware, audio_manager, message_archiver, config)`
            *   `health_monitor = SystemHealthMonitor(config)`
            *   `web_interface = WebInterface(message_archiver, health_monitor, config)` (if Flask runs in a separate thread/process, manage its lifecycle).
        *   The `run()` method will start the main application loop, likely driven by `phone_event_handler.listen_for_events()` or similar.
        *   Handle graceful shutdown (e.g., on `KeyboardInterrupt`).
    *   **Testing (`tests/unit/test_app.py`):**
        *   Focus on the orchestration: does `AppController.run()` correctly initialize and start the main components (e.g., call a `listen()` method on `PhoneEventHandler`, start the web server thread)?
        *   Mock all direct dependencies of `AppController`.

**Phase 5: Documentation, Packaging & Deployment Scripts**

1.  **Documentation (`docs/`):**
    *   Write `architecture.rst` (class diagrams, sequence diagrams).
    *   Write `usage.rst` (installation, configuration, running).
    *   Configure Sphinx (`conf.py`) to use `autodoc` to pull from docstrings.
    *   Build docs: `cd docs && make html`.

2.  **Packaging (`setup.cfg`, `pyproject.toml`):**
    *   Ensure metadata for packaging is complete.
    *   Test building a wheel: `python -m build`.

3.  **`start.sh` Script:**
    *   Activates virtual environment (if applicable).
    *   Navigates to the project directory.
    *   Runs the main application (`python -m src.guestbook.app` or similar if you make `app.py` executable and add a `if __name__ == "__main__":` block).

4.  **Final CI/CD Polish:**
    *   Ensure `pytest --cov=guestbook --cov-fail-under=90` (or your target) passes.
    *   Ensure `interrogate --min-coverage 100` passes.
    *   Consider adding a step to build and publish docs to GitHub Pages.
    *   Consider adding a release workflow (tagging, building wheel, publishing to PyPI).

**Throughout the process:**

*   **Commit frequently** with clear messages.
*   **Run pre-commit hooks** before each commit.
*   **Run tests** often.
*   **Refactor within modules** as you go if you see opportunities for improvement (e.g., breaking down large methods, improving clarity) that don't require changing interfaces yet.

This is a comprehensive plan. We'll take it step-by-step.

Since `src/guestbook/` doesn't exist, our immediate first step is **Phase 0: Project Setup & CI Foundation**.

Would you like to start by creating the basic directory structure and some of the initial configuration files like `pyproject.toml` and `.pre-commit-config.yaml`? I can guide you on the content for those.
