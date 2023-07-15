#!/bin/bash

# Prepare env
http_proxy=http://192.168.10.15:8080;
export http_proxy

https_proxy=http://192.168.10.15:8080;
export https_proxy

# Default params
DeployInForeground=false;
ShouldPull=false;
ShouldPrune=false;

ContainerName='cllro_dev';
ComposeFile='docker-compose.prod.yaml';

RepoBase='https://github.com/SwanseaUniversityMedical/concept-library.git';
RepoBranch='JS/static-ro-dev';

# Collect CLI args
while [[ "$#" -gt 0 ]]
  do
    case $1 in
      -fg|--foreground) DeployInForeground=true; shift;;
      -np|--no-pull) ShouldPull=false; shift;;
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

  rm -rf /root/deploy_DEV_DEMO_DT/concept-library
  cd /root/deploy_DEV_DEMO_DT

  if [ ! -z "$RepoBranch" ]; then
    git clone -b "$RepoBranch" "$RepoBase"
  else
    git clone "$RepoBase"
  fi
fi

# Update environment variables
cat /root/deploy_DEV_DEMO_DT/env_vars-RO.txt > /root/deploy_DEV_DEMO_DT/concept-library/docker/production/env/app.compose.env

# Kill current app and cleanup if required
echo "==========================================="
echo "=========== Cleaning workspace ============"
echo "==========================================="
echo $(printf '\nCleaning Container %s from %s | Will prune: %s' "$ContainerName" "$ComposeFile" "$ShouldPrune")

cd /root/deploy_DEV_DEMO_DT/concept-library/docker

docker-compose -p "$ContainerName" -f "$ComposeFile" down --rmi all -v

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
