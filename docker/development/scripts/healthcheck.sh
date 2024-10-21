#!/bin/bash

curl --output /dev/null --silent --head --fail ${WEB_HEALTHCHECK_ADDR:-host.docker.internal}:${WEB_HEALTHCHECK_PORT:-8000}/api/v1/health
