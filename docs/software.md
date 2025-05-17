# Software

## Core Architecture

The Rotary Phone Audio Guestbook is built upon a modular, event-driven architecture orchestrated by a central controller. This design promotes separation of concerns, testability, and maintainability through the use of well-defined interfaces (Abstract Base Classes - ABCs) and dependency injection.

### 1. Application Controller (`src/rotary_guestbook/app.py`)

- **`AppController`**: The main entry point and orchestrator of the application.
  - Initializes and manages the lifecycle of all other major components.
  - Coordinates interactions between different modules by injecting concrete implementations of the defined interfaces.

### 2. Configuration Management (`src/rotary_guestbook/config.py`)

- **`ConfigManager`**: Handles loading, validation (using Pydantic), and access to application settings from `config.yaml`.
  - Provides a centralized and type-safe way to manage configuration for all modules.

### 3. Core Interfaces

To ensure a decoupled and extensible system, the following core interfaces (ABCs) are defined:

#### a. Audio Backend (`src/rotary_guestbook/audio.py`)

- **`AbstractAudioBackend`**: Defines the contract for all audio operations.
  - `play_greeting()`: Plays the welcome message.
  - `start_recording(filename: str)`: Initiates audio recording to a file.
  - `stop_recording()`: Halts the current recording.
  - `convert_to_mp3(input_wav: str, output_mp3: str)`: Handles audio format conversion.
- Concrete implementations (e.g., `PyAudioBackend`, `AlsaBackend`) will provide the specific logic for these operations, interacting with system audio libraries or tools like `ffmpeg`/`lame`.

#### b. Storage Backend (`src/rotary_guestbook/archive.py`)

- **`AbstractStorageBackend`**: Defines the contract for message persistence.
  - `save_message(audio_file_path: str, metadata: dict) -> str`: Saves a recorded message and its associated metadata.
  - `get_message(message_id: str) -> Optional[Tuple[str, dict]]`: Retrieves a specific message.
  - `list_messages() -> List[dict]`: Lists all stored messages.
- Concrete implementations (e.g., `FileSystemStorageBackend`) will manage how and where messages are stored (e.g., local filesystem, cloud storage).

#### c. Phone Hardware (`src/rotary_guestbook/phone.py`)

- **`AbstractPhoneHardware`**: Defines the contract for interacting with the physical phone hardware.
  - `wait_for_hook_event() -> HookEvent`: Blocks until a hook event (on-hook/off-hook) is detected.
  - `is_receiver_off_hook() -> bool`: Checks the current state of the hook.
- **`HookEvent` (Enum)**: Represents phone events (`ON_HOOK`, `OFF_HOOK`).
- Concrete implementations (e.g., `RPiGPIOPhoneHardware`) will handle the specifics of GPIO pin monitoring or other hardware interaction methods.

### 4. Key Components (to be implemented/refactored)

These components will utilize the interfaces above and the `ConfigManager`.

#### a. Audio Manager (`src/rotary_guestbook/audio.py`)

- **`AudioManager`**: Orchestrates high-level audio tasks (e.g., "play welcome and record message sequence").
  - Takes an `AbstractAudioBackend` and `ConfigManager`.
  - Will replace parts of the logic previously in `audioGuestBook.py`.

#### b. Message Archiver (`src/rotary_guestbook/archive.py`)

- **`MessageArchiver`**: Manages the lifecycle of messages, including metadata generation and interaction with the storage backend.
  - Takes an `AbstractStorageBackend` and `ConfigManager`.

#### c. Phone Event Handler (`src/rotary_guestbook/phone.py`)

- **`PhoneEventHandler`**: Contains the core state machine and business logic of the guestbook.
  - Responds to hardware events from `AbstractPhoneHardware`.
  - Uses `AudioManager` to play sounds and record messages.
  - Uses `MessageArchiver` to save messages.
  - Takes `AbstractPhoneHardware`, `AudioManager`, `MessageArchiver`, and `ConfigManager`.
  - This will be the primary consumer of the defined interfaces and will encapsulate most of the application's operational logic, replacing the bulk of `audioGuestBook.py`.

### 5. Web Server (`webserver/server.py`)

- A Flask-based web server providing a user interface for:
  - Listing and playing back recorded messages (interacting with `MessageArchiver`).
  - Viewing system status and health (potentially via a `SystemHealthMonitor`).
  - (Potentially) Modifying parts of the application configuration.
- Runs on a configurable port (default: 5000, as specified in `config.yaml`).
- Accessible on the local network via the Raspberry Pi's IP address.
- A `.service` file can be used for automatic startup with `systemd`.

### 6. System Health Monitor (`src/rotary_guestbook/health.py`)

- **`SystemHealthMonitor`**: (To be implemented) Responsible for checking system vitals like disk space, audio device status, etc.
  - Provides information to the web interface and logs critical issues.
  - Takes `ConfigManager`.

## Legacy Components (to be phased out or refactored)

- `src/rotary_guestbook/audio_interface.py` (functionality absorbed by `AbstractAudioBackend` implementations and `AudioManager`).
- `src/rotary_guestbook/audioGuestBook.py` (logic to be distributed among `PhoneEventHandler`, `AudioManager`, and `MessageArchiver`).

---

*Note: The architecture promotes a clean separation between abstract interfaces and their concrete implementations, facilitating testing and future modifications.*
