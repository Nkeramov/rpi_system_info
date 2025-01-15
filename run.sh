source .venv/bin/activate
set -o allexport && source .env && set +o allexport
gunicorn --bind 0.0.0.0:${PORT} main:app
