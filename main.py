import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.rpi_system_info.app import create_app
from src.rpi_system_info.config import AppConfig

if __name__ == "__main__":
    config = AppConfig.from_env()
    app = create_app(config)
    try:
        app.run(host='0.0.0.0', port=config.PORT, debug=False)
    except KeyboardInterrupt:
        print("Stopped")
    except Exception as e:
        print(f"Failed to start: {e}")
        raise
