#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

export FLASK_APP=run:app
export FLASK_CONFIG=production

flask db upgrade
