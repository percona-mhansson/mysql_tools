#!/bin/bash

image_name=dev
username=$(whoami)
ssh_key=id_rsa
docker_args=()

usage() {
  cat <<USAGE
Usage: $(basename "$0") [-t IMAGE_NAME] [-u USERNAME] [DOCKER_BUILD_ARGS...]

Build the development Docker image from the Dockerfile in the current directory.

Options:
  -t, --tag IMAGE_NAME      Name (tag) of the image to build (default: $image_name)
  -u, --username USERNAME   User to create inside the image (default: $username)
  -h, --help                Show this help and exit

Any other arguments (and everything after --) are passed on to docker build.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    -t|--tag)
      [ -n "${2:-}" ] || { echo "error: $1 requires an argument" >&2; usage >&2; exit 1; }
      image_name=$2; shift 2 ;;
    --tag=*) image_name=${1#*=}; shift ;;
    -t*) image_name=${1#-t}; shift ;;
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

docker build . -t "$image_name" --build-arg username="$username" --build-arg keyfile="$ssh_key" "${docker_args[@]}"
