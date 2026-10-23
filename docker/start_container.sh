container_name=${1:-mydev}

docker start ${container_name} &&
docker exec -u root ${container_name} chmod 666 /ssh-agent
