#!/bin/sh
set -e

uvicorn main:app --host 127.0.0.1 --port 8000 &
exec nginx -g 'daemon off;'
