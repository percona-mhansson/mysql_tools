#!/bin/bash

set -euxo pipefail

image_name=${1:-dev}
container_name=${2:-mydev}
username=${3:-$(whoami)}

home="/home/$username"
script_dir=$(dirname $0)


echo "Setting up container '$container_name' from image '$image_name' for user '$username'"


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
       -v /run/host-services/ssh-auth.sock:/ssh-agent \
       --cap-add=SYS_PTRACE "$image_name" tail -f /dev/null

docker exec -uroot "$container_name" chmod 777 /ssh-agent

copy_files_to_home "$script_dir/.bash_aliases" "$script_dir/.gdbinit"

# Personally, I keep this file in Git and just symlink it
copy_file_to_home "$HOME/.gitconfig"
