#!/bin/bash

: '
  [!] Note:

    This script is intended to be used for
    deployment of feature branches that
    are not covered by CI/CD

'

# Prepare env
http_proxy=http://192.168.10.15:8080;
export http_proxy

https_proxy=http://192.168.10.15:8080;
export https_proxy

# Default params
DeployInForeground=false;
ShouldPull=true;
ShouldPrune=false;
ShouldClean=true;

RootPath='/root/deploy_DEV_DEMO_DT';
EnvFileName='env_vars-RO.txt';

ContainerName='cllro_dev';
ComposeFile='docker-compose.prod.yaml';

RepoBase='https://github.com/SwanseaUniversityMedical/concept-library.git';
RepoBranch='manual-feature-branch';

# Collect CLI args
while [[ "$#" -gt 0 ]]
  do
    case $1 in
      -fp|--file-path) RootPath="$2"; shift;;
      -fg|--foreground) DeployInForeground=true; shift;;
      -np|--no-pull) ShouldPull=false; shift;;
      -nc|--no-clean) ShouldClean=false; shift;;
      -e|--env) EnvFileName="$2"; shift;;
      -p|--prune) ShouldPrune=true; shift;;
      -f|--file) ComposeFile="$2"; shift;;
      -n|--name) ContainerName="$2"; shift;;
      -r|--repo) RepoBase="$2"; shift;;
      -b|--branch) RepoBranch="$2"; shift;;
    esac
    shift
done

# Pull from repo/branch if required
if [ "$ShouldPull" = true ]; then
  echo "==========================================="
  echo "=========== Pulling repository ============"
  echo "==========================================="
  echo $(printf '\nRepository: %s | Branch %s' "$RepoBase" "$RepoBranch")

  rm -rf "$RootPath/concept-library"
  cd "$RootPath"

  if [ ! -z "$RepoBranch" ]; then
    git clone -b "$RepoBranch" "$RepoBase"
  else
    git clone "$RepoBase"
  fi
fi

# Update environment variables
cat "$RootPath/$EnvFileName" > "$RootPath/concept-library/docker/production/env/app.compose.env"

# Kill current app and prune if required
echo "==========================================="
echo "=========== Cleaning workspace ============"
echo "==========================================="
echo $(printf '\nCleaning Container %s from %s | Will prune: %s' "$ContainerName" "$ComposeFile" "$ShouldPrune")

cd "$RootPath/concept-library/docker"

docker-compose -p "$ContainerName" -f "$ComposeFile" down

if [ "$ShouldPrune" = 'true' ]; then
  docker system prune -f -a --volumes
fi

# Deploy new version
echo "==========================================="
echo "========== Deploying application =========="
echo "==========================================="
echo $(printf '\nDeploying %s from %s | In foreground: %s' "$ContainerName" "$ComposeFile" "$DeployInForeground")

if [ "$DeployInForeground" = 'true' ]; then
  docker-compose -p "$ContainerName" -f "$ComposeFile" up --build
else
  docker-compose -p "$ContainerName" -f "$ComposeFile" up --build -d
fi

# Prune unused containers/images/volumes if we (1) want to cleanup and (2) haven't already done so
if [ "$ShouldClean" = 'true' && "$ShouldPrune" != 'true' ]; then
  docker system prune -f -a --volumes
fi
