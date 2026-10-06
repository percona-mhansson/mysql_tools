#!/bin/bash

set -euo pipefail

image_name=${1:-dev}
container_name=${2:-mydev}
username=${3:-$(whoami)}

home="/home/$username"
script_dir=$(dirname $0)

echo "Setting up container '$container_name' from image '$image_name' for user '$username'"


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


copy_file() {
  source=$1
  target=$2
  docker cp -L "${source}" "${container_name}:$target" -q
  docker exec -uroot "$container_name" chown "$username:$username" "$target"
}

copy_file_to_home() {
  source=$1
  target=${home}/$(basename $1)
  docker cp -L "${source}" "${container_name}:$target" -q
  docker exec -uroot "$container_name" chown "$username:$username" "$target"
}

copy_files_to_home() {
  files=$@
  for file in $files; do
    copy_file_to_home "$file"
  done
}

docker run -d --name "$container_name" \
       -v "$HOME/gitroot:$home/gitroot" \
       -v "$HOME/boost:$home/boost" \
       -v "$ssh_agent_socket:/ssh-agent" \
       --cap-add=SYS_PTRACE "$image_name" tail -f /dev/null

docker exec -uroot "$container_name" chmod 777 /ssh-agent

copy_files_to_home "$script_dir/.bash_aliases" "$script_dir/.gdbinit"

# Personally, I keep this file in Git and just symlink it
copy_file_to_home "$HOME/.gitconfig"
