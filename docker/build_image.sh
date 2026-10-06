#!/bin/bash

usage() {
  cat <<EOF
Usage: $(basename "$0") [IMAGE_NAME [USERNAME]]

Build the development Docker image from the Dockerfile in the current directory.

Arguments:
  IMAGE_NAME  Name (tag) of the image to build (default: dev)
  USERNAME    User to create inside the image (default: $(whoami))

Options:
  -h, --help  Show this help and exit
EOF
}

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
esac

image_name=${1:-dev}
username=${2:-$(whoami)}
ssh_key=id_rsa

echo "Building image '$image_name' for user '$username'"

docker build . -t "$image_name" --build-arg username="$username" --build-arg keyfile="$ssh_key"
