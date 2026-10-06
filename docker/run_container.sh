#!/bin/bash

set -euo pipefail

usage() {
  cat <<EOF
Usage: $(basename "$0") [IMAGE_NAME [CONTAINER_NAME [USERNAME]]]

Start a detached development container from IMAGE_NAME, mounting ~/gitroot,
~/boost and the host SSH agent into it. Requires a running SSH agent.

Arguments:
  IMAGE_NAME      Image to run (default: dev)
  CONTAINER_NAME  Name of the new container (default: mydev)
  USERNAME        User inside the container (default: $(whoami))

Options:
  -h, --help      Show this help and exit
EOF
}

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
esac

image_name=${1:-dev}
container_name=${2:-mydev}
username=${3:-$(whoami)}

home="/home/$username"

echo "Starting container '$container_name' from image '$image_name' for user '$username'"

# Fail early without a host agent: on Linux Docker would mount /ssh-agent as an
# empty directory, and on macOS the container would get an agent with no keys.
ssh_agent_status=0
ssh-add -l >/dev/null 2>&1 || ssh_agent_status=$?
if [ "$ssh_agent_status" -eq 2 ]; then
  echo "Error: no SSH agent is running on the host; start one with "\
       "'eval \"\$(ssh-agent -s)\" && ssh-add' before running this script." >&2
  exit 1
fi

# Docker Desktop on macOS runs containers in a Linux VM and relays the host
# agent to this path inside the VM; the Mac's own socket can't be mounted.
# On Linux the containers share the host kernel, so mount the agent directly.
if [ "$(uname)" = Darwin ]; then
  ssh_agent_socket=/run/host-services/ssh-auth.sock
else
  ssh_agent_socket=$SSH_AUTH_SOCK
fi

docker run -d --name "$container_name" \
       -v "$HOME/gitroot:$home/gitroot" \
       -v "$HOME/boost:$home/boost" \
       -v "$ssh_agent_socket:/ssh-agent" \
       --cap-add=SYS_PTRACE "$image_name" tail -f /dev/null

docker exec -uroot "$container_name" chmod 777 /ssh-agent
