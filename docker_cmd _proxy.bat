echo ">>>>> stop and remove old container (FULL-ACCESS) <<<<<<<<<<<<<<<<<<"
docker container stop cllfa
docker container stop celery_worker
docker container stop celery_beat
docker container stop redis

echo ">>>>>>> delete unused data <<<<<<<<<<<<<<"
docker container prune -f
docker image prune -f
docker system prune -f
docker network prune -f

echo "-------------------Build OS ----------------------------------------"
#docker build --no-cache  -f  "OS/Dockerfile" -t cll/os .

echo ">>>>> build app image <<<<<<<<<<<<<<<<<<<<<<<"
docker build --no-cache -t cll/app:v0 . --build-arg http_proxy=http://192.168.10.15:8080 --build-arg https_proxy=http://192.168.10.15:8080 --build-arg pip_proxy="--proxy http://192.168.10.15:8080"
docker build -t cll/celery_worker . --build-arg http_proxy=http://192.168.10.15:8080 --build-arg https_proxy=http://192.168.10.15:8080 --build-arg pip_proxy="--proxy http://192.168.10.15:8080"
docker build -t cll/celery_beat . --build-arg http_proxy=http://192.168.10.15:8080 --build-arg https_proxy=http://192.168.10.15:8080 --build-arg pip_proxy="--proxy http://192.168.10.15:8080"
docker pull redis:alpine  
echo "-----------------------------------------------------------"


echo ">>>> run docker (FULL-ACCESS) <<<<<<<<<<<"
docker network create redis
docker run --name redis --network redis -d redis:alpine
docker run -t -d --env-file env_vars.txt -p 80:80 --name cllfa   cll/app:v0
docker run -t --entrypoint /home/config_cll/worker_start.sh -d --env-file env_vars.txt --name celery_worker  --network redis  cll/celery_worker
docker run -t --entrypoint /home/config_cll/beat_start.sh -d --env-file env_vars.txt --name celery_beat  --network redis  cll/celery_beat





echo ">>>> run DB mig (FULL-ACCESS) <<<<<<<<<<<<<<<<<"
docker exec -i cllfa  /home/config_cll/deploy_script_DB_mig.sh

echo "-----------------------------------------------------------"