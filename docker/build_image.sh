#!/bin/bash

username=$(whoami)
ssh_key=id_rsa
docker_args=()

usage() {
  cat <<USAGE
Usage: $(basename "$0") [-u USERNAME] [DOCKER_BUILD_ARGS...]

Build the development Docker image from the Dockerfile in the current directory.

Options:
  -u, --username USERNAME   User to create inside the image (default: $username)
  -h, --help                Show this help and exit

Any other arguments (and everything after --) are passed on to docker build.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    -u|--username)
      [ -n "${2:-}" ] || { echo "error: $1 requires an argument" >&2; usage >&2; exit 1; }
      username=$2; shift 2 ;;
    --username=*) username=${1#*=}; shift ;;
    -u*) username=${1#-u}; shift ;;
    -h|--help) usage; exit 0 ;;
    --) shift; docker_args+=("$@"); break ;;
    *) docker_args+=("$1"); shift ;;
  esac
done

echo "Building image '$image_name' for user '$username'"

docker build . --build-arg username="$username" --build-arg keyfile="$ssh_key" "${docker_args[@]}"
