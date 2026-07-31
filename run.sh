set -o allexport && source .env && set +o allexport
uv run gunicorn --bind 0.0.0.0:${PORT} 'src.rpi_system_info.app:create_app()'
