import logging
from openenv.core.env_server import create_fastapi_app
from environment import FinGuardEnv
from models import FinGuardAction, FinGuardObservation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("Initializing FinGuard environment backend via OpenEnv ASGI wrapper...")

# Initialize the bare python environment
env = FinGuardEnv()

# Wrap the python class into a standard FastAPI ASGI application expected by Uvicorn
app = create_fastapi_app(env, FinGuardAction, FinGuardObservation)
