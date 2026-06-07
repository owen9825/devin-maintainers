echo "Starting Docker services (Redis)…"
sudo systemctl start docker
docker compose --file ./docker-compose.yml up
echo "Now start running some workers"