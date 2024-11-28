#!/bin/bash

: ' TODO: docs '

#> Base env & container params
## 1. Proxy-related
http_proxy='http://192.168.10.15:8080';
export http_proxy;

https_proxy='http://192.168.10.15:8080';
export https_proxy;

## 2. App-related
app_port='80';
export app_port;

cll_host_binding='0.0.0.0';
export cll_host_binding;

cll_grace_period='3s';
export cll_grace_period;

cll_log_path='/cl_log';
export cll_log_path;

## 3. Redis-related
redis_port=
export redis_image;
redis_image='redis:7.0-bullseye';
export redis_image;



#> Default params
## 1. Command behaviour
###  - Specifies the cwd (defaults to script directory)
RootPath=$(realpath `dirname $0`);
###  - Specifies whether to prune containers, images & volumes after building
ShouldClean=true;
###  - Specifies whether to run containers in the background / foreground
DetachedMode=true;

## 2. Image registry target(s)
###  - Image registry URL
LibraryAddress='';

## 3. Docker preferences
###  - Specifies the Docker profile to use (if any)
Profile='';
###  - Specifies the Docker project name to use
ProjectName='main_demo';
###  - Specifies the image name
ImageName='cll/app:latest';

## 3. Docker target(s)
###  - Specifies the environment file to use; can either be an
###    absolute path or a path relative to the `RootPath`
EnvFile='env_vars.txt';
###  - Specifies the docker-compose file target; can either be an
###    absolute path or a path relative to the `RootPath`
ComposeFile='docker-compose.prod.yaml';


# Utils
rm_dangling() {
  for trg in "$@"
  do
    case $trg in
      images)
        docker image --filter "dangling=true" --format '{{ .CreatedAt }}\t{{ .ID }}\t{{ .Repository }}:{{ .Tag }}' \
          | cut -d$'\t' -f 2 \
          | xargs docker image rm --force
        ;;

      volumes)
        docker volume --filter "dangling=true" --format '{{ .CreatedAt }}\t{{ .ID }}\t{{ .Repository }}:{{ .Tag }}' \
          | cut -d$'\t' -f 2 \
          | xargs docker volume rm --force
        ;;

      all)
        docker system prune -f
        ;;

      *)
        echo "invalid danling arg: $trg" >&2
        ;;
    esac
  done
}

is_relative() {
  local trg="$1";
  if [ "$trg" = "${trg#/}" ]; then
    return 0;
  fi

  return 1;
}


# Set CWD
if is_relative $RootPath; then
  RootPath=$(realpath $RootPath);
fi

cd "$RootPath";


# Resolve compose file
if is_relative $ComposeFile; then
  ComposeFile=$( echo $ComposeFile | sed -e 's/^\.\///' );
  ComposeFile="$RootPath/$ComposeFile";
fi


# Copy env file
if is_relative $EnvFile; then
  EnvFile=$( echo $EnvFile | sed -e 's/^\.\///' );
  EnvFile="$RootPath/$EnvFile";
fi


# Parse & export variables
SERVER_NAME=$(grep SERVER_NAME "$EnvFile" | cut -d'=' -f 2-);
export SERVER_NAME;

cll_app_image=$ImageName;
export cll_app_image;


# Pull the cll/app image
docker pull $LibraryAddress;
docker tag $LibraryAddress $(printf '%s' "$ImageName")


# Kill current app
docker-compose -p "$ProjectName" -f "$ComposeFile" --profile "*" down --volumes;


# Start the containers
declare -a args;
args=("-p" $ProjectName "-f" "$ComposeFile")

if [ ! -z "$Profile" ]; then
  args+=("--profile" "$Profile");
fi
args+=("up");

if [ "$DetachedMode" = true ]; then
  args+=("-d");
fi

docker-compose ${args[@]};


# Prune unused containers/images/volumes if we want to cleanup
if [ "$ShouldClean" = true ]; then
  rm_dangling "all";
fi


# List containers
docker ps -a;
