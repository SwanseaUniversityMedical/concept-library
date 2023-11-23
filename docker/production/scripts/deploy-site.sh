#!/bin/bash

: '
  [!] Note:

    This file is intended for automated deployment via the Harbor CI/CD
    pipeline

    The environment file should be located within the same directory as the
    docker-compose file

    i.e. both should be in `/root/` or some other directory:

      > /root/
        - deploy-site.sh
        - docker-compose.prod.yaml
        - env_vars.txt

  [!] Arguments:
    -fg | --foreground - [Defaults to False] - determines whether we deploy in foreground
    -nc | --no-clean   - [Defaults to True]  - determines whether we prune the workspace after deploying
    -fp | --file-path  - [Defaults to $PWD]  - determines the /root/ file path (otherwise uses CWD)
     -a | --address    - [Defaults to None]  - the registry address we pull from
     -f | --file       - [Defaults to prod]  - the docker-compose file we use
     -p | --profile    - [Defaults to live]  - which docker profile to use
'

# Prepare env
http_proxy=http://192.168.10.15:8080;
export http_proxy

https_proxy=http://192.168.10.15:8080;
export https_proxy

# Constants
ContainerName='cll';

# Default params
DeployInForeground=false;
ShouldClean=true;

Profile='live';
LibraryAddress='';

RootPath='/root/';
ComposeFile='docker-compose.prod.yaml';
export app_port=80;

# Collect CLI args
while [[ "$#" -gt 0 ]]
  do
    case $1 in
      -fg|--foreground) DeployInForeground=true; shift;;
      -nc|--no-clean) ShouldClean=false; shift;;
      -fp|--file-path) RootPath="$2"; shift;;
      -a|--address) LibraryAddress="$2"; shift;;
      -f|--file) ComposeFile="$2"; shift;;
      -p|--profile) Profile="$2"; shift;;
    esac
    shift
done

if [ -z "$LibraryAddress" ]; then
  echo "ERROR: No library address provided, please set it or pass it as an argument using -a | --address"
  exit 1
fi

# Pull from Harbor / Gitlab
echo "==========================================="
echo "============= Pulling images =============="
echo "==========================================="

docker pull "$LibraryAddress"
docker tag "$LibraryAddress" $(printf '%s/app' "$ContainerName")
docker tag "$LibraryAddress" $(printf '%s/celery_worker' "$ContainerName")
docker tag "$LibraryAddress" $(printf '%s/celery_beat' "$ContainerName")

# Kill current app and prune if required
echo "==========================================="
echo "=========== Cleaning workspace ============"
echo "==========================================="

cd "$RootPath"

docker-compose -p "$ContainerName" -f "$ComposeFile" down --volumes

# Deploy app
echo "==========================================="
echo "========== Deploying application =========="
echo "==========================================="

if [ "$DeployInForeground" = 'true' ]; then
  if [ ! -z "$Profile" ]; then
    docker-compose -p "$ContainerName" -f "$ComposeFile" --profile "$Profile" up
  else
    docker-compose -p "$ContainerName" -f "$ComposeFile" up
  fi
else
  if [ ! -z "$Profile" ]; then
    docker-compose -p "$ContainerName" -f "$ComposeFile" --profile "$Profile" up -d
  else
    docker-compose -p "$ContainerName" -f "$ComposeFile" up -d
  fi
fi

# Prune unused containers/images/volumes if we (1) want to cleanup and (2) haven't already done so
if [ "$ShouldClean" = 'true' ]; then
  docker system prune -f -a --volumes
fi
