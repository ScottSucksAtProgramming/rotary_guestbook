# Rotary Phone Audio Guestbook

A production-grade rotary phone audio guestbook system that allows users to leave voice messages through a classic rotary dial telephone interface.

## Features

- Interactive audio experience with vintage rotary phone interface
- Digital recording and storage of voice messages
- Web interface for message playback and system status
- Robust error handling and logging
- Comprehensive testing coverage
- Production-grade architecture following SOLID principles

## Requirements

- Python 3.10 or higher
- Raspberry Pi (tested on Raspberry Pi OS Bullseye or later)
- Rotary phone hardware (see `docs/hardware.md` for wiring details)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/scottkostolni/rotary_guestbook.git
   cd rotary_guestbook
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install the package in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

5. Copy the example configuration:
   ```bash
   cp config.yaml.example config.yaml
   ```

6. Edit `config.yaml` with your settings.

## Usage

1. Start the application:
   ```bash
   ./start.sh
   ```

2. Access the web interface at `http://localhost:5000`

## Development

- Run tests: `pytest`
- Check code style: `pre-commit run --all-files`
- Build documentation: `cd docs && make html`

## Documentation

- [Hardware Setup](docs/hardware.md)
- [Software Architecture](docs/software.md)
- [Configuration Guide](docs/configuration.md)
- [Development Guide](docs/development.md)

## License

MIT License - see LICENSE file for details
