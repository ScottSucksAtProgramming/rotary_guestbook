# Software

## Core Architecture

The Rotary Phone Audio Guestbook is transitioning to a modular, event-driven architecture orchestrated by a central controller. This design promotes separation of concerns, testability, and maintainability.

### 1. Application Controller (`src/rotary_guestbook/app.py`)

- **`AppController`**: The main entry point and orchestrator of the application.
  - Initializes and manages the lifecycle of all other major components.
  - Coordinates interactions between different modules (e.g., phone events, audio processing, web interface).

### 2. Configuration Management (`src/rotary_guestbook/config.py`)

- **`ConfigManager`**: Handles loading, validation, and access to application settings from `config.yaml`.
  - Provides a centralized and type-safe way to manage configuration.

## Key Components

### 1. Audio Interface (`src/rotary_guestbook/audio_interface.py`)
*(Previously `src/audioInterface.py`)*

- Utilizes ALSA's native `aplay`/`arecord` via subprocess calls for audio operations.
- Manages the low-level details of audio playback and recording.
- Provides a clean interface for audio operations to other parts of the system.

### 2. Phone Event Handling & Business Logic (Legacy: `src/rotary_guestbook/audioGuestBook.py`)
*(Previously `src/audioGuestBook.py`; to be refactored into `PhoneEventHandler`, `AudioManager` etc.)*

- Currently, this module contains the main operational logic of the guestbook.
- It handles GPIO pin interactions for hook switch events (on-hook, off-hook).
- Manages the state of the guestbook (e.g., idle, playing greeting, recording).
- **Off-hook sequence:**
    - Plays a welcome message (e.g., `sounds/voicemail.wav`).
    - Plays a beep sound (e.g., `sounds/beep.wav`) to indicate the start of recording.
    - Begins recording the guest's voice message.
- **On-hook sequence (or recording limit reached):**
    - Stops the recording.
    - Saves the message to the `recordings/` directory.
    - If the recording limit (from `config.yaml`) is exceeded, it plays a warning (e.g., `sounds/time_exceeded.wav`) before stopping.
- The behavior adapts based on the `hook_type` (NC/NO) specified in `config.yaml`.

### 3. Web Server (`webserver/server.py`)

- A Flask-based web server providing a user interface for managing recordings and system settings.
- Runs on a configurable port (default: 5000, as specified in `config.yaml`).
- Accessible on the local network via the Raspberry Pi's IP address (e.g., `192.168.1.100:5000`).
- **Features:**
  - Dynamically lists recordings from the `recordings/` directory.
  - Playback of recorded messages directly in the browser.
  - Editing of recorded file names.
  - Bulk, individual, or selectable download of recordings.
  - Deletion of recordings.
  - Configuration of all `config.yaml` parameters via a settings page.
  - Light and dark themes.
- A `.service` file can be used for automatic startup with `systemd`.

![Webserver Home Dark](../images/webserver_home_dark.png)
*Webserver - Home (Dark Theme)*

![Webserver Settings Dark 1](../images/webserver_settings_dark_1.png)
*Webserver - Settings (Dark Theme - Part 1)*

![Webserver Settings Dark 2](../images/webserver_settings_dark_2.png)
*Webserver - Settings (Dark Theme - Part 2)*

![Webserver Home Light](../images/webserver_home_light.png)
*Webserver - Home (Light Theme)*

---

*Note: Path references like `../src/audioInterface.py` will be updated as the project structure evolves with the refactoring.*
