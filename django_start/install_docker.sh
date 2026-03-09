#!/bin/bash
set -e

echo "🔵 Обновляем систему..."
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common gnupg lsb-release

echo "🔵 Добавляем GPG ключ Docker..."
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "🔵 Добавляем репозиторий Docker..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "🔵 Устанавливаем Docker Engine..."
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

echo "🟢 Docker установлен!"

echo "🔵 Ставим последнюю версию docker-compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

echo "🟢 Docker Compose установлен!"

echo "🔵 Добавляем пользователя $(whoami) в группу docker..."
sudo usermod -aG docker $USER

echo "✅ Всё готово! Теперь перезагрузите терминал (или сделайте 'newgrp docker') чтобы использовать Docker без sudo."
echo "Версия docker:"
docker --version
echo "Версия docker-compose:"
docker-compose --version
