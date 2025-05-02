#!/bin/sh

apk update && \
    apk add \
        yq \
        kubectl

echo $KUBECONFIG | base64 -d > ./kubeconfig

echo "Init deployment done"