#!/bin/bash

: '
  Arguments:
    -nc | --no-clean - [Defaults to True]   - determines whether we prune the workspace after deploying
     -p | --prune    - [Defaults to False]  - determines whether we prune after docker-compose down
     -a | --address  - [Defaults to None]   - the registry address we pull from
     -f | --file     - [Defaults to deploy] - the docker-compose file we use
'

# Prepare env
http_proxy=http://192.168.10.15:8080;
export http_proxy

https_proxy=http://192.168.10.15:8080;
export https_proxy

# Constants
ContainerName='cll';

# Default params
ShouldClean=true;
ShouldPrune=false;
LibraryAddress='';
ComposeFile='docker-compose.deploy.yaml';

# Collect CLI args
while [[ "$#" -gt 0 ]]
  do
    case $1 in
      -nc|--no-clean) ShouldClean=false; shift;;
      -p|--prune) ShouldPrune=true; shift;;
      -a|--address) LibraryAddress="$2"; shift;;
      -f|--file) ComposeFile="$2"; shift;;
    esac
    shift
done

if [ -z "$LibraryAddress" ]; then
  echo "ERROR: No library address provided, please set it or pass it as an argument using -a | --address"
  exit 1
fi

# Kill current app and prune if required
echo "==========================================="
echo "=========== Cleaning workspace ============"
echo "==========================================="

docker-compose -p "$ContainerName" -f "$ComposeFile" down

if [ "$ShouldPrune" = 'true' ]; then
  docker system prune -f -a --volumes
fi

# Pull from Harbor / Gitlab
echo "==========================================="
echo "============= Pulling images =============="
echo "==========================================="

docker pull "$LibraryAddress"
docker tag "$LibraryAddress" $(printf '%s/os' "$ContainerName")
docker tag "$LibraryAddress" $(printf '%s/celery_worker' "$ContainerName")
docker tag "$LibraryAddress" $(printf '%s/celery_beat' "$ContainerName")

# Deploy app
echo "==========================================="
echo "========== Deploying application =========="
echo "==========================================="

if [ "$DeployInForeground" = 'true' ]; then
  docker-compose -p "$ContainerName" -f "$ComposeFile" up
else
  docker-compose -p "$ContainerName" -f "$ComposeFile" up -d
fi

# Prune unused containers/images/volumes if we (1) want to cleanup and (2) haven't already done so
if [ "$ShouldClean" = 'true' && "$ShouldPrune" != 'true' ]; then
  docker system prune -f -a --volumes
fi
