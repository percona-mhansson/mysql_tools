#!/bin/bash

set -euo pipefail

usage() {
  cat <<EOF
Usage: $(basename "$0") [IMAGE_NAME [CONTAINER_NAME [USERNAME]]]

Start a detached development container from IMAGE_NAME, mount ~/gitroot,
~/boost and the host SSH agent into it, and copy .bash_aliases, .gdbinit and
~/.gitconfig into the user's home directory. Requires a running SSH agent.

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
script_dir=$(dirname "$0")

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

echo "Setting up container '$container_name' from image '$image_name' for user '$username'"

"$script_dir/run_container.sh" "$image_name" "$container_name" "$username"

copy_files_to_home "$script_dir/.bash_aliases" "$script_dir/.gdbinit"

# Personally, I keep this file in Git and just symlink it
copy_file_to_home "$HOME/.gitconfig"
copy_file_to_home "$script_dir/.gitconfig-percona"
docker exec -u"$username" "$container_name" bash -c "echo '[filter \"codeformat\"]
	clean = clang-format-15 --assume-filename=%f --style=file' >> $home/.gitconfig"
