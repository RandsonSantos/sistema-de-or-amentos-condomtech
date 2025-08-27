#!/bin/bash
gunicorn -c gunicorn/gunicorn.conf.py app:app
