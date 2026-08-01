"""Launch HungryCall Web Server locally."""

import uvicorn
from hungrycall.web import app

if __name__ == "__main__":
    print("==================================================")
    print("  I am hungry — HungryCall Web UI")
    print("  Running locally on: http://127.0.0.1:8000")
    print("  Press Ctrl+C to stop.")
    print("==================================================")
    uvicorn.run(app, host="127.0.0.1", port=8000)
