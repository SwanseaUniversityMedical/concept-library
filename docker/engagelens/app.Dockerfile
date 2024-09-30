FROM python:3.9-slim

ENV PYTHONUNBUFFERED 1
ENV LC_ALL=C.UTF-8

# Set the working directory
WORKDIR /engagelens


# Install and update packages
RUN apt-get update -y -q && \
    apt-get upgrade -y -q && \
    apt-get install dos2unix

COPY ./requirements/engagelens.txt .

# Install requirements
RUN pip --no-cache-dir install -r engagelens.txt

COPY ./development/scripts/wait-for-it.sh /bin/wait-for-it.sh
# Make wait-for-it.sh executable
RUN ["chmod", "+x", "/bin/wait-for-it.sh"]
# Convert the wait-for-it.sh script to Unix line endings (optional, if developed on Windows)
RUN ["dos2unix", "/bin/wait-for-it.sh"]

