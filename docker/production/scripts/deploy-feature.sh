#!/bin/bash

: '
  [!] Note:

    This script is intended to be used for
    deployment of feature branches that
    are not covered by CI/CD

    Your directory should look similar to this:

      > /root/
        - env_vars.txt
        - deploy-feature.sh
    
    When running this script, the repository will be cloned into your
    /root/ directory and the env_vars.txt will be cloned into the
    appropriate folder

  [!] Arguments:
    -fg | --foreground - [Defaults to False]    - determines whether we deploy in foreground
    -nd | --no-pull    - [Defaults to True]     - determines whether we pull from the repo and remove legacy
    -nc | --no-clean   - [Defaults to True]     - determines whether we prune the workspace after deploying
    -fp | --file-path  - [Defaults to $PWD]     - determines the /root/ file path (otherwise uses CWD)
     -e | --env        - [Defaults to $-FA]     - the environment file to use
     -f | --file       - [Defaults to prod]     - the docker-compose file we use
     -n | --name       - [Defaults to '.._dev'] - the name of the container
     -r | --repo       - [Defaults to cl.git]   - the repository URL
     -b | --branch     - [Defaults to '']       - the repository branch (uses master if null)
     -p | --profile    - [Defaults to live]     - which docker profile to use
'

# Prepare env
http_proxy=http://192.168.10.15:8080;
export http_proxy

https_proxy=http://192.168.10.15:8080;
export https_proxy

# Default params
DeployInForeground=false;
ShouldPull=true;
ShouldClean=true;

RootPath='/root/deploy_DEV_DEMO_DT/';
EnvFileName='env_vars-RO.txt';

Profile='live';
ComposeFile='docker-compose.prod.yaml';
ContainerName='cllro_dev';

RepoBase='https://github.com/SwanseaUniversityMedical/concept-library.git';
RepoBranch='manual-feature-branch';

# Collect CLI args
while [[ "$#" -gt 0 ]]
  do
    case $1 in
      -fg|--foreground) DeployInForeground=true; shift;;
      -nd|--no-pull) ShouldPull=false; shift;;
      -nc|--no-clean) ShouldClean=false; shift;;
      -fp|--file-path) RootPath="$2"; shift;;
      -e|--env) EnvFileName="$2"; shift;;
      -f|--file) ComposeFile="$2"; shift;;
      -n|--name) ContainerName="$2"; shift;;
      -r|--repo) RepoBase="$2"; shift;;
      -b|--branch) RepoBranch="$2"; shift;;
      -p|--profile) Profile="$2"; shift;;
    esac
    shift
done

cd "$RootPath"

# Pull from repo/branch if required
if [ "$ShouldPull" = true ]; then
  echo "==========================================="
  echo "=========== Pulling repository ============"
  echo "==========================================="
  echo $(printf '\nRepository: %s | Branch %s' "$RepoBase" "$RepoBranch")

  rm -rf "$RootPath/concept-library"

  if [ ! -z "$RepoBranch" ]; then
    git clone -b "$RepoBranch" "$RepoBase"
  else
    git clone "$RepoBase"
  fi
fi

# Move env file to appropriate location
cp "$RootPath/$EnvFileName" "$RootPath/concept-library/docker/env_vars.txt"

# Parse environment variables
SERVER_NAME=$(grep SERVER_NAME "$RootPath/$EnvFileName" | cut -d'=' -f 2-)

# Deploy new version
echo "==========================================="
echo "=========== Building application =========="
echo "==========================================="
echo $(printf '\nDeploying %s from %s | In foreground: %s' "$ContainerName" "$ComposeFile" "$DeployInForeground")

cd "$RootPath/concept-library/docker"

## Build the cll/app image
docker build -f production/app.Dockerfile -t cll/app \
  --build-arg http_proxy="$http_proxy" --build-arg https_proxy="$https_proxy" --build-arg server_name="$SERVER_NAME" \
  ..

## Tag our image for other services
docker tag cll/app cll/celery_worker
docker tag cll/app cll/celery_beat

# Kill current app 
echo "==========================================="
echo "=========== Cleaning workspace ============"
echo "==========================================="
echo $(printf '\nCleaning Container %s from %s | Will prune: %s' "$ContainerName" "$ComposeFile" "$ShouldPrune")

docker-compose -p "$ContainerName" -f "$ComposeFile" down --volumes

# Deploy new version
echo "==========================================="
echo "========== Deploying application =========="
echo "==========================================="
echo $(printf '\nDeploying %s from %s | In foreground: %s' "$ContainerName" "$ComposeFile" "$DeployInForeground")

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
