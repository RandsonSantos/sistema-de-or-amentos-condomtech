#!/bin/bash
gunicorn -c gunicorn/gunicorn.conf.py app:app
chmod +x gunicorn/start.sh
