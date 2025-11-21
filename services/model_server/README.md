# Model Server Setup Guide

This is a Python FastAPI service for the generative genomics model server.

## Prerequisites

- Python 3.10+ (matches Dockerfile and CI configuration)
- pip (Python package manager)

## Setup Instructions

### 1. Create a Virtual Environment

A virtual environment isolates your project dependencies from your system Python. **Important:** The existing `venv/` directory should be ignored by git (now in `.gitignore`). You can recreate it with:

```bash
cd services/model_server
python3.10 -m venv venv
```

If you don't have Python 3.10 specifically, you can use `python3` (but note that Docker/CI use 3.10):

```bash
python3 -m venv venv
```

### 2. Activate the Virtual Environment

**On Linux/Mac:**
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt when activated.

### 3. Install Dependencies

With the virtual environment activated:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- FastAPI (web framework)
- uvicorn (ASGI server)
- torch (PyTorch for ML models)
- numpy (numerical computing)
- pydantic (data validation)
- pytest (testing framework)

### 4. Verify Installation

Run the tests to make sure everything works:

```bash
# From the project root
pytest

# Or from services/model_server directory
pytest app/tests/
```

### 5. Run the Server Locally

```bash
# Make sure venv is activated
cd services/model_server
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

The `--reload` flag enables auto-reload on code changes (useful for development).

### 6. Test the API

Once running, you can test the health endpoint:

```bash
curl http://localhost:8001/health
```

## Project Structure

```
services/model_server/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app and routes
│   ├── inference.py     # Model inference logic
│   ├── model/
│   │   └── model.py     # PyTorch model definitions
│   └── tests/
│       ├── __init__.py
│       └── test_inference.py
├── Dockerfile           # Container build config
├── requirements.txt     # Python dependencies
└── venv/               # Virtual environment (gitignored)
```

## Common Commands

- **Activate venv:** `source venv/bin/activate`
- **Deactivate venv:** `deactivate`
- **Run tests:** `pytest`
- **Run server:** `uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload`
- **Install new package:** `pip install <package>` then update `requirements.txt`

## Notes

- Always activate the virtual environment before working on this project
- The Dockerfile uses Python 3.10, so try to match that locally if possible
- Don't commit the `venv/` directory (it's in `.gitignore`)

