#!/bin/bash

curl -L --output /dev/null --silent --head --fail ${WEB_HEALTHCHECK_ADDR:-app}:${WEB_HEALTHCHECK_PORT:-80}/api/v1/health
