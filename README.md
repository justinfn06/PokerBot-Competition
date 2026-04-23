# Poker Bot Framework

This repository provides a Python-based environment for developing and testing poker-playing bots. It includes a game engine, a bot template, and example implementations.

---

## Requirements

- **Python 3.12.2** — Using a different version may result in runtime or compatibility issues.

---

## Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-name>
```

### 2. Configure Python Environment

It is recommended to use a virtual environment.

```bash
python3.12 -m venv venv
```

Activate the environment:

**Windows**
```bash
venv\Scripts\activate
```

**macOS/Linux**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Usage

### Running the Simulation

Execute the main driver script:

```bash
python main.py
```

This runs a game simulation using the bots currently configured in `main.py`.

### Configuring Bots

Bots participating in a match are defined in `main.py`. To test your own bot:

1. Create or modify a bot file (see below)
2. Import your bot into `main.py`
   ```python
   from bots import ConservativeBot, RandomBot, YourBotClassName
   ```
4. Replace or add it to the list of active players
   ```python
   bots = [
        ConservativeBot("Conservative_1"),
        RandomBot("Random_1"),
        RandomBot("Random_2"),
        ConservativeBot("Conservative_2"),
    ]
   ```

---

## Creating a Bot

Use `bot_template.py` as the starting point.

### Steps

1. Copy or rename `bot_template.py`
2. Implement your strategy within the provided structure
3. Ensure your bot adheres to the expected interface defined in the template

Your bot logic should:

- Accept the game state as input
- Return a valid action (e.g., fold, call, raise)
- Execute without errors under all game conditions

---

## Testing

Before using your bot in competition or evaluation:

- Run multiple simulations via `main.py`
- Test against the provided example bots
- Verify stability (no crashes or invalid actions)

---

## Notes

> - Only one bot file should be used per submission or evaluation run
> - The framework assumes all bots conform to the template interface
> - Modifying core engine files is not recommended unless necessary for local testing
