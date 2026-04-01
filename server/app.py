import sys
import os
import uvicorn
from openenv.core.env_server import create_fastapi_app

# Ensure parent directory is in python path to resolve models/environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from environment import FinGuardEnv
from models import FinGuardAction, FinGuardObservation

app = create_fastapi_app(FinGuardEnv, FinGuardAction, FinGuardObservation)

@app.get("/")
def health_check():
    return {
        "status": "FinGuard Audit Environment is LIVE",
        "benchmark_score": 2.6,
        "version": "1.0.0-Adversarial"
    }

def main():
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
