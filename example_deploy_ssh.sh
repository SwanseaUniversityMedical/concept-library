#!/bin/bash

echo ">>>>> STARTING (READ-ONLY DEMO server) <<<<<<<<<<<<<<<<<<<"

http_proxy=http://192.168.10.15:8080;
export http_proxy

https_proxy=https://192.168.10.15:8080;
export https_proxy


#git config --global http.proxy http://192.168.10.15:8080/
#git config --global https.proxy http://192.168.10.15:8080/

echo "-------------------------------------"
docker container stop '$(docker ps -q)'
docker container prune -f
docker image prune -f

echo ">>>>> git pull GitHub (HDR-UK branch) <<<<<<<<<<<<<<<<<<<"
rm -rf /root/py3dj2/concept-library
cd /root/py3dj2
git clone https://github.com/SwanseaUniversityMedical/concept-library.git

cd /root/py3dj2/concept-library
pwd

#git checkout HDR-UK
#git pull origin HDR-UK
git checkout Docker_compose_test
git pull origin Docker_compose_test


echo "-------------------Build OS ----------------------------------------"
#docker build --no-cache  -f  "/root/py3dj2/concept-library/OS/Dockerfile" -t cll/os . --build-arg http_proxy=http://192.168.10.15:8080 --build-arg https_proxy=http://192.168.10.15:8080 --build-arg pip_proxy="--proxy http://192.168.10.15$

echo ">>>>> build image <<<<<<<<<<<<<<<<<<<<<<<"
docker build --no-cache -t cll/app:v0 . --build-arg http_proxy=http://192.168.10.15:8080 --build-arg https_proxy=http://192.168.10.15:8080 --build-arg pip_proxy="--proxy http://192.168.10.15:8080"
docker build -t cll/celery_worker . --build-arg http_proxy=http://192.168.10.15:8080 --build-arg https_proxy=http://192.168.10.15:8080 --build-arg pip_proxy="--proxy http://192.168.10.15:8080"

docker build -t cll/celery_beat . --build-arg http_proxy=http://192.168.10.15:8080 --build-arg https_proxy=http://192.168.10.15:8080 --build-arg pip_proxy="--proxy http://192.168.10.15:8080"

docker pull redis:alpine
echo "-----------------------------------------------------------"


echo ">>>>> stop and remove old container (READ-ONLY) <<<<<<<<<<<<<<<<<<"


echo ">>>>>>> delete unused data <<<<<<<<<<<<<<"
docker container prune -f
docker image prune -f
docker system prune -f

echo "-----------------------------------------------------------"


echo ">>>> run docker (READ-ONLY) <<<<<<<<<<<<"
#docker run -t -d --env-file ../env_vars-RO.txt -p 80:80 --name cl --mount source=cl_log_ro,target=/home/config_cll/cll_srvr_logs cll/app:v0
#cp /root/py3dj2/concept-library/docker-compose.yml /root/py3dj2/docker-compose.yml
cd /root/py3dj2/
docker network create redis
docker run --name redis --network redis -d redis:alpine
docker run -t -d --env-file env_vars-RO.txt -p 80:80 --name cl --mount source=cl_log_ro,target=/home/config_cll/cll_srvr_logs cll/app:v0
docker run -t --entrypoint /home/config_cll/worker_start.sh -d --env-file env_vars-RO.txt --name celery_worker  --network redis  cll/celery_worker
docker run -t --entrypoint /home/config_cll/beat_start.sh -d --env-file env_vars-RO.txt --name celery_beat  --network redis  cll/celery_beat


echo ">>>> run DB mig (READ-ONLY) <<<<<<<<<<<<<<<<<"
docker exec -i cl  /home/config_cll/deploy_script_DB_mig_ro.sh
#docker exec -i cl  /home/config_cll/worker_start.sh
#docker exec -i cl  /home/config_cll/beat_start.sh

echo "-----------------------------------------------------------"

docker ps -a
sudo apt-get clean
