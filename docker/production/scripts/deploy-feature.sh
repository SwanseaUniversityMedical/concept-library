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
###  - Specifies whether to remove the current repo and
###    pull a completely clean branch
CleanPull=false;
###  - Determines if the command will attempt to pull the branch
###    from the repository
ShouldPull=true;
###  - Specifies whether to prune containers, images & volumes after building
ShouldClean=true;
###  - Specifies whether to run containers in the background / foreground
DetachedMode=true;

## 2. Repository target(s)
###  - Specifies the repository file path; can either be an
###    absolute path or a path relative to the `RootPath`
RepoTarget='./concept-library';
###  - Specifies the repository remote target
RepoBase='https://github.com/SwanseaUniversityMedical/concept-library.git';
###  - Specifies the repository branch target
RepoBranch='Development';

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
EnvFile='env_vars-FA.txt';
###  - Specifies the docker-compose file target (within `$RepoTarget/docker`)
ComposeFile='docker-compose.prod.yaml';


# Utils
is_out_of_date() {(
  local v0='';
  local v1='';
  if [ $# -eq 0 ]; then
    v0="$( git rev-parse HEAD 1> echo $? 2> /dev/null | echo '-1' )";
    v1="$( git rev-parse '@{u}' 1> echo $? 2> /dev/null | echo '-1' )";
    if [ "$v0" = "$v1" ]; then
      return 0;
    fi

    return 1;
  fi

  local trg="$1";
  trg=$(realpath -s "$trg")

  if [ ! -d "$trg" ]; then
    return 1;
  fi

  cd $trg;

  v0="$( git rev-parse HEAD 1> echo $? 2> /dev/null | echo '-1' )";
  v1="$( git rev-parse '@{u}' 1> echo $? 2> /dev/null | echo '-1' )";
  if [ "$v0" = "-1" ] || [ "$v1" = "-1" ]; then
    return 1;
  elif [ "$v0" = "$v1" ]; then
    return 0;
  fi

  return 1;
)}

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


# Resolve repository
if is_relative $RepoTarget; then
  RepoTarget=$( echo $RepoTarget | sed -e 's/^\.\///' );
  repo_fpath="$RootPath/$RepoTarget";
fi

repo_exists=$( [ -d $repo_fpath ] && echo true || echo false );
repo_dir=$(dirname $repo_fpath);

if [ "$repo_exists" = false ] || [ "$CleanPull" = true ]; then
  [ "$repo_exists" = true ] && rm -rf "$repo_fpath";

  (
    cd $repo_dir;
    if [ ! -z "$RepoBranch" ]; then
      git clone -b "$RepoBranch" "$RepoBase";
    else
      git clone "$RepoBase";
    fi
  )
elif [ "$ShouldPull" = true ]; then
  (
    cd $repo_fpath;

    git fetch;

    outofdate=$( is_out_of_date "$repo_fpath" && echo true || echo false );
    if [ "$outofdate" = true ]; then
        if [ ! -z "$RepoBranch" ]; then
          git checkout "$RepoBranch";
        fi

        git pull;
    fi
  )
fi


# Copy env file
if is_relative $EnvFile; then
  EnvFile=$( echo $EnvFile | sed -e 's/^\.\///' );
  EnvFile="$RootPath/$EnvFile";
fi

cp "$EnvFile" "$repo_fpath/docker/env_vars.txt";


# Parse & export variables
SERVER_NAME=$(grep SERVER_NAME "$EnvFile" | cut -d'=' -f 2-);
export SERVER_NAME;

cll_app_image=$ImageName;
export cll_app_image;


# Build the cll/app image
(
  cd "$repo_fpath";

  docker build --no-cache -f "docker/production/app.Dockerfile" -t "$ImageName" \
    --build-arg http_proxy="$http_proxy" --build-arg https_proxy="$https_proxy" \
    --build-arg server_name="$SERVER_NAME" \
    '.';

)

# Kill current app
(
  cd "$repo_fpath";

  docker-compose -p "$ProjectName" -f "docker/$ComposeFile" --profile "*" down --volumes;
)


# Start the containers
(
  cd "$repo_fpath";

  declare -a args;
  args=("-p" $ProjectName "-f" "docker/$ComposeFile")

  if [ ! -z "$Profile" ]; then
    args+=("--profile" "$Profile");
  fi
  args+=("up");

  if [ "$DetachedMode" = true ]; then
    args+=("-d");
  fi

  docker-compose ${args[@]};
)


# Prune unused containers/images/volumes if we want to cleanup
if [ "$ShouldClean" = true ]; then
  rm_dangling "all";
fi


# List containers
docker ps -a;
