#!/bin/bash

SERVER_USER="ubuntu"
SERVER_IP="89.169.179.190"
REMOTE_PATH="/home/ubuntu/beautycity"
VENV_PATH="$REMOTE_PATH/env"

echo "Переносим код на сервер"
rsync -az --exclude 'venv' --exclude '.git' --exclude '__pycache__' ./ "$SERVER_USER@$SERVER_IP:$REMOTE_PATH/"

echo "🔌 Подключаемся по SSH и обновляем проект..."
ssh "$SERVER_USER@$SERVER_IP" << EOF
  cd $REMOTE_PATH
  source $VENV_PATH/bin/activate
  pip install -r requirements.txt
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
  sudo systemctl restart gunicorn
EOF

echo "Деплой завершён!"
