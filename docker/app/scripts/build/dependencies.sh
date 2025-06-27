#!/bin/bash

if [ ! -z $HTTP_PROXY ] && [ -e $HTTP_PROXY ]; then
  # Install py deps
  pip --proxy $HTTP_PROXY install --upgrade pip;
  pip --proxy $HTTP_PROXY --no-cache-dir install -r "$1";

  # Config npm proxy
  npm config set proxy "$HTTP_PROXY";
  npm config set https-proxy "$HTTPS_PROXY";
  npm config set registry "http://registry.npmjs.org/";
else
  # Install py deps
  pip install --upgrade pip;
  pip --no-cache-dir install -r "$1";
fi

# Install esbuild / other npm deps
npm install -g config set user root;
npm install -g "esbuild@0.25.2"
