# Concept Library
The concept library is a system for storing, managing, sharing, and documenting clinical code lists in health research.  
	
The specific goals of this work are:
- Store code lists along with metadata that captures important information about quality, author, etc.
- Store version history and provide a way to unambiguously reference a particular version of a code list.
- Allow programmatic interaction with code lists via an API, so that they can be directly used in queries, statistical scripts, etc.
- Provide a mechanism for sharing code lists between projects and organizations.

## Live Site
The Concept Library web application is [available here](https://conceptlibrary.saildatabank.com).

## User documentation
Concept Library documentation is [available here](https://github.com/SwanseaUniversityMedical/concept-library/wiki/Concept-Library-Documentation).

## Overview
Our goal is to create a system that describes research study designs in a machine-readable format to facilitate rapid study development; higher quality research; easier replication; and sharing of methods between researchers, institutions, and countries.

## Background
A significant aspect of research using routinely collected health records is defining how concepts of interest (including conditions, treatments, symptoms, etc.) will be measured.  This typically involves identifying sets of clinical codes that map to a variable that the researcher wants to measure, and sometimes a set of rules as well (e.g. a sufferer from a disease may be defined as someone who has a diagnosis code from list A and a medication from list B, but excluding anyone who has a code from list C).  A large part of the analysis work may involve consulting clinicians, investigating the data, and creating and testing definitions of clinical concepts to be used.

Often the definitions that are created are of interest to researchers for many studies, but there are barriers to easily sharing them.  The definitions may be embedded within study-specific scripts, such that it is not easy to extract the part that may be of general interest.  Also, often researchers do not fully document how a concept was created, its precise meaning, limitations, etc.  Crucial information may be lost when passing it to other researchers, resulting in mistakes.  Often there simply is no mechanism to discover and share work that has been done previously, leading researchers to waste time and resources reinventing the wheel.  In theory, when research is published, information on the precise methods used should be included, but in reality this is often inadequate.

# Table of contents
1. [Clone this repository](#1-Clone-this-Repository)  
2. [Setup with Docker](#2-Setup-with-Docker)  
  2.1. [Prerequisites](#21-Prerequisites)  
    2.1.1. [Docker](#211-Docker)  
    2.1.2. [Running on Apple](#212-Running-on-Apple)  
  2.2. [Database Setup](#22-Database-Setup)  
    2.2.2. [Restore from Git Repository](#222-Restore-from-Git-Repository)  
    2.2.3. [Migration only](#223-Migration-only)  
    2.2.1. [Restore from Local Backup](#221-Restore-from-Local-Backup)  
  2.3. [Development](#23-Development)  
    2.3.1. [Docker Compose Files](#231-Docker-Compose-Files)  
    2.3.2. [Initial Build](#232-Initial-Build)  
    2.3.3. [Stopping and Starting the Containers](#233-Stopping-and-Starting-the-Containers)  
    2.3.4. [Live Working](#234-Live-Working)  
    2.3.5. [Removing the Containers](#235-Removing-the-Containers)  
    2.3.6. [Local Pre-production Builds](#236-Local-Pre-production-Builds)  
    2.3.7. [Impact of Environment Variables](#237-Impact-of-Environment-Variables)  
  2.4. [Accessing and Exporting the Database](#24-Accessing-and-Exporting-the-Database)  
    2.4.1. [Access/Export with PGAdmin4](#241-Access/Export-with-PGAdmin4)  
    2.4.2. [Access/Export with CLI](#242-Access/Export-with-CLI)  
  2.5. [Debugging and Running Tests](#25-Debugging-and-Running-Tests)  
    2.5.1. [Django Logging](#251-Django-Logging)  
    2.5.2. [Debug Tools in Visual Studio Code](#252-Debug-Tools-in-Visual-Studio-Code)  
    2.5.3. [Running Tests](#253-Running-Tests)  
  2.6. [Setting up VSCode Tasks](#26-Setting-up-VSCode-Tasks)  
    2.6.1. [Basics](#261-Basics)  
    2.6.2. [Debug Build Tasks](#262-Debug-Build-Tasks)  
    2.6.3. [Test Build Tasks](#263-Test-Build-Tasks)  
    2.6.4. [How to Handle Cleaning](#264-How-to-Handle-Cleaning)  
  2.7. [Creating a Superuser](#27-Creating-a-Superuser)
3. [Setup without Docker](#3-Setup-without-Docker)  
  3.1. [Prerequisites](#31-Prerequisites)  
  3.2. [Installing](#32-Installing)  
  3.3. [Using Eclipse](#33-Using-Eclipse)  
  3.4. [Running Tests](#34-Running-Tests)  
4. [Deployment](#4-Deployment)  
  4.1. [Deploy Scripts](#41-Deploy-Scripts)  
    4.1.1. [Manual Deployment](#411-Manual-Deployment)  
    4.1.2. [Automated Deployment](#412-Automated-Deployment)  
  4.2. [Harbor-driven CI/CD Pipeline](#42-Harbor-driven-CI/CD-Pipeline)  

# 1. Clone this Repository
To download this repository:
1. Ensure that you have installed Git (e.g. [Git for Windows](https://gitforwindows.org/)).
2. Open a terminal
3. Navigate to the folder you want to clone this repository into
4. Run the command:  
`git clone https://github.com/SwanseaUniversityMedical/concept-library.git`

# 2. Setup with Docker

## 2.1. Prerequisites

### 2.1.1. Docker
Please ensure that you have installed [Docker Desktop v4.10.1](https://docs.docker.com/desktop/release-notes/) or [Docker Engine v20.10.17](https://docs.docker.com/engine/release-notes/).

If you encounter any issues, please see Docker's documentation (https://docs.docker.com/).

### 2.1.2. Running on Apple

The app container requires emulation for ARM CPUs, please install Rosetta 2:
1. Open a terminal
2. Run: `softwareupdate --install-rosetta`

## 2.2. Database setup

### 2.2.1. Restore from Local Backup
>***[!] Note:** Do not share the backup files with anyone*

To restore from a local backup:
1. Navigate to the `concept-library/docker/development` folder
2. Place a `.backup` file inside of the `db` folder  
3. Skip to [2.3. Development](#23-Development)  

### 2.2.2. Restore from Git Repository
>***[!] Note:** Do not share these files with anyone*

>***[!] Note:** 
The initial run of the application may take a while if you are using this method, however, subsequent builds will be faster as the backup is saved locally in the `concept-library/docker/development/db/` folder*

To restore from a Git repository:
1. Create a personal access token on GitHub (https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token), ensure it grants access to private repositories
2. Navigate to the `concept-library/docker/development/` folder
3. Duplicate the `example.git.token` inside of `development/db/`
4. Rename the duplicated file to `git.token`
5. Delete the contents of the file and paste your personal access token
6. Open the `postgres.compose.env` file inside of the `docker/development/env` folder
7. Ensure that the environment variable `POSTGRES_RESTORE_REPO` is set to the correct GitHub repository where your `.backup` file is stored
8. Skip to [2.3. Development](#23-Development)  

### 2.2.3. Migration only
If you do not have a backup available the application will still run successfully as migrations are automatically applied, however, no data will be restored. Please skip to [2.3. Development](#23-Development).

With an empty database, you will need to run statistics manually for the application to work correctly:
  1. After following the steps to start the application in [2.3. Development](#23-Development)
  2. Navigate to 127.0.0.1/admin/run-stats

## 2.3. Development
### 2.3.1. Docker Compose Files
Within the `concept-library/docker/` directory you will find the following docker-compose files:

1. `docker-compose.dev.yaml`
    - This is the development docker container used to iterate on the Concept Library.
    - After building, the application can be located at http://127.0.0.1:8000
2. `docker-compose.test.yaml`
    - This compose file builds an environment that better reflects the production environment, serving the application via Apache, and includes adjunct services like Redis and Celery.
    - It is recommended for use when developing the Docker images, or as a pre-production test when modifying build behaviour such as offline compression.
    - After building, the application can be located at http://localhost:8005
3. `docker-compose.prod.yaml`
    - This compose file builds the production container.
    - It is used for both manual and automated deployment via CI/CD workflows
    - After building, the application can be located at https://conceptlibrary.some-demo-app.saildatabank.com where `some-demo-app` describes the development sub-domain

### 2.3.2. Initial Build
To perform the initial build and run of the application:
1. Open a terminal
2. Navgiate to the `concept-library/docker/` folder
3. In the terminal, run `docker-compose -p cll -f docker-compose.dev.yaml up --build` (append `-d` as an argument to run in background)

The application and database will be available at:
 - Application: `127.0.0.1:8000`
 - Database: `127.0.0.1:5432`

### 2.3.3. Stopping and Starting the Containers
To stop the docker container:
1. If you have a terminal open which is running the docker containers, press `CTRL + C` or `CTRL + Z` to stop the containers
2. If you do not have a terminal open which is running the containers:  
a. Open a terminal  
b. Navigate to the `concept-library/docker/` folder  
c. In the terminal, run `docker-compose -p cll -f docker-compose.dev.yaml down`  

To start the docker container (if it has already been built and has stopped for any reason):
1. Open a terminal
2. Navigate to the `concept-library/docker/` folder
3. In the terminal, run `docker-compose -p cll -f docker-compose.dev.yaml start`

### 2.3.4. Live Working
Whilst working on the codebase, any changes should be automatically applied to the codebase stored in the app container after saving the file. 

If you make any changes to the models you will need to:  
1. Stop and start the containers again with `docker-compose -p cll -f docker-compose.dev.yaml up --build`, the migrations will be automatically applied
2. *OR*; execute the migration code from within the app container (see: https://docs.docker.com/engine/reference/commandline/exec/)

### 2.3.5. Removing the Containers
To remove the containers:
1. Open a terminal
2. Navigate to the `concept-library/docker/` folder
3. In the terminal, run:  
a. `docker compose down`: removes networks and containers.  
b. *OR;* `docker-compose -p cll -f docker-compose.dev.yaml down --rmi all -v`: removes networks, containers, images and volumes.  
c. *OR;* to prune your docker, enter `docker system prune -a`  

### 2.3.6. Local Pre-production Builds
>***[!] Note:**   
To test the transpiling, minification or compression steps, OR; if you have made changes to the Docker container or its images it is recommended that you run a local, pre-production build*

>***[!] Note:**
If you do not want to start the celery services you can remove the "--profiles live" argument

To build a local, pre-production build:
1. Open a terminal
2. Follow the steps above if you have not already built the images
3. Navigate to the `concept-library/docker/` folder
4. Set up the environment variables within `./test/app.compose.env`
5. In the terminal, run `docker build -f test/app.Dockerfile -t cll/app --build-arg server_name=localhost ..`
6. Once the image is built, run `docker tag cll/app cll/celery_beat; docker tag cll/app cll/celery_worker`
7. Finally, run `docker-compose -p cll -f docker-compose.test.yaml --profile live up` (append `-d` as an argument to run in background)
8. Open a browser and navigate to `localhost:8005` to access the application

### 2.3.7. Impact of Environment Variables

>***[!] Note:**   
To modify the environment variables, please navigate to `./docker/test/app.compose.env` (or the appropriate folder for the container you are building)*


#### Impact on Application Behaviour
Some environment variables modify the behaviour of the application.

The following are important to consider when modifying `app.compose.env`:
- `DEBUG` → When this flag is set to `True`:
    - The application will expect a Redis service to be running for use as the cache backend, otherwise it will use a DummyCache
    - The application will enable the compressor and precompilers, otherwise this will not take place (aside from HTML Minification)
- `IS_DEVELOPMENT_PC` → When this flag is set to `False`:
    - The application will use both LDAP and User model authentication, otherwise only the latter will be used
    - The application will use a different logging backend - please see `settings.py` for more information

#### Impact on Building
Some environment variables modify the behaviour of the container when building, you should be aware of this behaviour when building `docker-compose.prod.yaml` and `docker-compose.test.yaml` - this behaviour is mostly defined within `init-app.sh`. 

The following are important to consider when modifying `app.compose.env`:
- `IS_DEVELOPMENT_PC` → When this flag is set to `True`:
    - The application and celery services will await the postgres service to initialise before continuing
- `CLL_READ_ONLY` → When this flag is set to `False`:
    - The application will not run the `makemigrations` and `migrate` commands on startup
- `DEBUG` → This flag determines static collection behaviour:
    - If set to `True` it will compile, transpile and compress static resources
    - If set to `False` it will only collect the static resources

#### Other Variables
To learn about the impact of the other environment variables, please open and examine `./cll/settings.py`. 

## 2.4. Accessing and Exporting the Database
>***[!] Note:**   
If you have made changes to the environment variables in the docker-compose.dev.yaml file you will need to match those changes when connecting through the CLI or PGAdmin4*

### 2.4.1. Access/Export with PGAdmin4
#### To access the database
Please ensure you have installed [PGAdmin4](https://www.pgadmin.org/download/pgadmin-4-windows/) and then:
1. Open PGAdmin4
2. Right-click the `Servers` object in the browser and click `Register > Server...`
3. In the `General` tab, enter a name for the server, e.g. `docker-concept-library`
4. In the `Connection` tab, enter:  
    - `Host`: 127.0.0.1
    - `Port`: 5432
    - `Username`: clluser
    - `Password`: password
5. Click save, the connection should now be visible in the browser

#### To export the database
1. Ensure the Docker container is running
2. Open PGAdmin4
3. Connect to the `docker-concept-library` server
4. Right click the `concept_library` database and click `Backup...`
5. In the filename input field, enter the directory and name to save the backup file as. Ensure you save the file as a `.backup`
6. Click the `Backup` button

### 2.4.2. Access/Export with CLI
#### To access the database
> ***[!] Note:** The query will fail to retrieve results if you forget the semicolon, `;`, at the end of the query*

1. Open a terminal
2. In the terminal, run: `docker exec -it cll-postgres-1 /bin/bash`
3. Query the database:  
a. Initiate an active session with `psql -U clluser concept_library` and then run queries directly, e.g. `SELECT * FROM CLINICALCODE_PHENOTYPES LIMIT 1;`  
b. *OR;* run a query directly with `psql -U clluser -d concept_library 'SELECT * FROM CLINICALCODE_PHENOTYPES LIMIT 1;'`

#### To export the database
1. Open a terminal
2. In the terminal, run: `docker exec -it cll-postgres-1 /bin/bash`
3. Replace `[filename]` with the file name desired and run:  
`pg_dump -U postgres -F c concept_library > [filename].backup`

## 2.5. Debugging and Running Tests

### 2.5.1. Django Logging
Django logging is enabled by default, you can view the logs in the terminal used to start the docker container. 

To disable the verbose logging:
1. In docker-compose.dev.yaml set `tty: false` under the `app` service
2. In docker-compose.dev.yaml set `DEBUG: false` under the `environment` section of the `app` service

### 2.5.2. Debug Tools in Visual Studio Code
Before continuing, open the `docker-compose.dev.yaml` file and ensure the `DEBUG_TOOLS` variable in the `app` container definition is set to true.

Create a run configuration for the project:
1. Create a new folder and name it `.vscode`
2. Create a new file within that folder and name it `launch.json`
3. Paste the json below into the new file and then save the file

```json
{
  "configurations": [
    {
      "name": "Debug Application",
      "type": "python",
      "request": "attach",
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}/CodeListLibrary_project",
          "remoteRoot": "/var/www/CodeListLibrary_project"
        }
      ],
      "port": 8000,
      "host": "127.0.0.1"
    }
  ]
}
```

Now you're ready to start debugging:
1. Build the container `docker-compose -p cll -f docker-compose.dev.yaml up --build` and ensure it is running
2. Add a breakpoint to the file that you are debugging
3. In Visual Studio Code, open the `Run and Debug Menu` by clicking the icon on the left-hand side of the screen or using the hotkey `CTRL + SHIFT + D`
4. At the top of the debug menu, select the `Debug Application` option
5. Press the run button and start debugging

Variables, Watch and Callstack can all be viewed in the `Run and Debug` menu panel and the console can be viewed in the `Debug Console` (hotkey: `CTRL + SHIFT + Y`) window.

### 2.5.3. Running Tests
> **[!] Todo:** Needs documentation once we implement & finalise new test suite

[Details]


## 2.6. Setting up VSCode Tasks

### 2.6.1. Basics
> ***[!] Note:** You can learn more about using external tools and VSCode's Tasks system [here](https://code.visualstudio.com/docs/editor/tasks)*

#### Set up
To start using tasks:
1. Open your terminal
2. Navigate to the root of the `concept-library` project
3. Create a new `.vscode` directory within the project folder by running: `mkdir .vscode`
4. Navigate into this directory by running: `cd .vscode`
5. Create a new `tasks.json` file by running: `touch tasks.json`

#### Basic File Configuration
After opening the `tasks.json` file, you should configure the contents so it looks like this:
```json
{
  "version": "2.0.0",
  "tasks": []
}
```

### 2.6.2. Debug Build Tasks
> ***[!] Note:** You can learn about the available options for tasks [here](https://code.visualstudio.com/docs/editor/tasks-appendix)*

To set up your first debug task, configure your `tasks.json` file such that:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Build Debug",
      "detail": "Builds the development container",
      "type": "shell",
      "command": "docker-compose -p cll -f docker-compose.dev.yaml up --build",
      "options": {
        "cwd": "${workspaceFolder}/docker/"
      },
      "group": {
        "kind": "build",
        "isDefault": true
      },
      "presentation": {
        "reveal": "always",
        "panel": "new",
        "focus": false
      }
    }
  ]
}
```

### 2.6.3. Test Build Tasks
To set up a task for the `docker-compose.test.yaml` container, you append the following to the `"tasks": []` property:
```json
{
  "label": "Build Test",
  "detail": "Builds the test container",
  "type": "shell",
  "command": "docker build -f test/app.Dockerfile -t cll/app --build-arg server_name=localhost ..; docker tag cll/app cll/celery_beat; docker tag cll/app cll/celery_worker; docker-compose -p cll -f docker-compose.test.yaml up",
  "options": {
    "cwd": "${workspaceFolder}/docker/"
  },
  "group": {
    "kind": "test"
  },
  "presentation": {
    "reveal": "always",
    "panel": "new",
    "focus": false
  }
}
```

### 2.6.4. How to Handle Cleaning
> ***[!] Note:** There will be some differences between Windows and other operating systems. The example below is set up to use PowerShell logical operators. On a Linux-based OS, you would need to use the '&&' and '||' operators instead of '-and' and '-or'*

If you set up both the debug and test builds you will note that the docker container isn't cleaned between different tasks. It is possible to set up your tasks such that the containers will be cleaned.

To set this up, you would need to append the following cleaning task to your `tasks` property:
```json
{
  "label": "Clean Containers",
  "detail": "Cleans all cll related containers",
  "type": "shell",
  "command": "(docker ps -q --filter 'name=cll') -and (docker rm $(docker stop $(docker ps -q -f 'name=cll' -f 'name=redis'))) -or (echo 'Nothing to clean')",
  "options": {
    "cwd": "${workspaceFolder}/docker/"
  },
  "group": {
    "kind": "build"
  },
  "presentation": {
    "reveal": "never",
    "panel": "shared"
  },
  "problemMatcher": []
},
```

Using [Compound Tasks](https://code.visualstudio.com/docs/editor/tasks#_compound-tasks), you can modify your `Build Debug` and `Build Test` tasks to clean before starting by adding the `dependsOn` property. In the case of the `Build Debug` task, it would look like this:
```json
{
  "label": "Build Debug",
  "detail": "Builds the development container",
  "type": "shell",
  "command": "docker-compose -p cll -f docker-compose.dev.yaml up --build",
  "options": {
    "cwd": "${workspaceFolder}/docker/"
  },
  "group": {
    "kind": "build",
    "isDefault": true
  },
  "presentation": {
    "reveal": "always",
    "panel": "new",
    "focus": false
  },
  "dependsOn": ["Clean Containers"]
},
```

## 2.7. Creating a Superuser

To create a superuser:
1. Ensure the docker container is running and open a new terminal
2. Run `docker exec -it cll-app-1 /bin/bash` (see below if this doesn't work)
3. Navigate to the CodeListLibrary_project directory by running: `cd /var/www/CodeListLibrary_project`
4. Run `python manage.py createsuperuser` and follow the instructions in the terminal to create the user
5. Verify that the user was created properly by navigating to the website and logging in with the credentials entered

If you you are unable to `exec` into `cll-app-1`:
1. Run `docker ps -a` in the terminal
2. Look for the Concept Library's `app` container and copy its `CONTAINER ID`
3. Run the same command using the `CONTAINER ID`, e.g. `docker exec -it 82508ae4ef /bin/bash`
4. Continue with Step (3) above

# 3. Setup without Docker

## 3.1. Prerequisites
Please ensure that you have the following installed:
1. [Python 3.9](https://www.python.org/downloads/release/python-390/)
2. [Pip](https://pip.pypa.io/en/stable/cli/pip_install/) 
3. [MSVC C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
4. [PostgreSQL 14.4](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
5. [PGAdmin4](https://www.pgadmin.org/download/pgadmin-4-windows/)

## 3.2. Installing

#### Cloning the Concept Library

To clone the repository:
1. Open the terminal
2. Navigate to an appropriate directory
3. Run the following command: `git clone https://github.com/SwanseaUniversityMedical/concept-library.git`
4. Checkout the branch you would like to work on, e.g. run the following to work on Master: `git checkout master`

#### Install virtualenv and virtualenvwrapper

This will provide a dedicated environment for each project you create. It is considered best practice and will save time when you’re ready to deploy your project.

1. Open the terminal
2. Run the following command: `pip install virtualenvwrapper-win`
3. Now navigate to the directory to where you have downloaded the project e.g. `cd C:/Dev/concept-library`
4. To create a virtualenv you should run the following command: `mkvirtualenv cclproject`
5. To work on this environment, run: `workon cclproject`
6. To install the required packages, run the following command: `pip install -r docker/requirements/local.txt`
7. To stop working on this environment, run: `deactivate cclproject`

#### Database set up

1. Install [Postgres](https://www.postgresql.org/download/) and [PGAdmin](https://www.pgadmin.org/) on your device.
2. Within PGAdmin3, do the following:
    - Create a role called `clluser`
    - Create a database called `code_list_library`
    - Create a read-only role
3. When running the application it may complain that you have unapplied migrations; your app may not work properly until they are applied. To do this:
    - Navigate to `concept-library/CodeListLibrary_project/cll`
    - Run: `python manage.py makemigrations`
    - Finally, run: `python manage.py migrate`
4. To run the application:
    - Navigate to `concept-library/CodeListLibrary_project/cll`
    - Run the following: `python manage.py runserver 0.0.0.0:8000`
5. You can now access the server on http://127.0.0.1:8000/admin/
6. To stop the server, press `CTRL + C` or `CTRL + Z` within the terminal

#### Installing LDAP functionality

For windows machines:
- You will need to install the Microsoft Visual C++ Compiler for Python. This can be found [here](https://www.microsoft.com/en-us/download/details.aspx?id=44266)
- Download the `python_ldap` wheel, located [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#python-ldap)
- Once downloaded, activate your virtualenv and run the following `pip install path/to/the/file/python_ldap.whl`
- Once installed, you can run the `pip install django-auth-ldap` command. See LDAP installation reference [here](https://django-auth-ldap.readthedocs.io/en/1.2.x/install.html)
- If you intend to use LDAP over SSL, please take a look at the troubleshooting guide found [here](https://support.microsoft.com/en-us/help/938703/how-to-troubleshoot-ldap-over-ssl-connection-problems)

#### Administration area
When you first start the application there will be no users within your database. You will first need to create a superuser account in order to access the administration site.

1. Open the terminal and run the following: `python manage.py createsuperuser`
2. Fill in the desired username, email and password
3. When the development server is running you can access the admin section by going to the following url: http://127.0.0.1:8000/admin/

## 3.3. Using Eclipse

#### Set up
1. Navigate to the `File` button within Eclipse's toolbar, then select `Open projects from file system`
2. Browse to the Concept Library folder, e.g. `C:/Dev/concept-library`
3. Assuming you have followed the previous steps to create a virtual env, you will need to point Eclipse's python interpreter to the virtual env:
    - Select the `Window` button within your toolbar and open `Preferences`
    - Select `PyDev -> Interpreters -> Python Interpreter` and select `New`
    - Follow the interpreter wizard (e.g. enter the name), then browse to the Python executable (as set in your system environment %PATH% variable)
    - Select each of the folders you want added to your python path
    - Right click the Concept Library project and select `Debug as...` and choose the python development interpreter
4. You should now see that the server is live at http://127.0.0.1:8000/admin/

## 3.4. Running Tests
> **[!] Todo:** Needs documentation once we implement & finalise new test suite

[Details]

# 4. Deployment

## 4.1. Deploy Scripts

### 4.1.1. Manual Deployment
> **[!] Note:** These instructions only pertain to feature branches which are not covered by the CI/CD workflow

#### Feature branch deployment with deploy-feature.sh
This script can be used to manually deploy feature branches on the server. Please note that you will have to either (a) modify the script to use the appropriate directories and settings, or (b) pass arguments to the script to ensure it runs correctly.

Optional arguments for this script include:

| Command        | Shorthand | Default value                                                           | Description                                                                    |
|----------------|-----------|-------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| `--file-path`  | `-fp`     | `/root/deploy_DEV_DEMO_DT`                                              | Determines the root path of your environment variable text file (see below)    |
| `--foreground` | `-fg`     | `false`                                                                 | Whether the containers will be built in the foreground                         |
| `--no-pull`    | `-nd`     | `true`                                                                  | Whether to pull the branch from the Git repository                             |
| `--no-clean`   | `-nc`     | `true`                                                                  | Whether to clean unused docker containers/images/networks/volumes/build caches |
| `--env`        | `-e`      | `env_vars.txt`                                                          | Name of the environment variables text file                                    |
| `--file`       | `-f`      | `docker-compose.prod.yaml`                                              | Name of the docker-compose file you would like to deploy                       |
| `--name`       | `-n`      | `cllro_dev`                                                             | Name of the docker container                                                   |
| `--repo`       | `-r`      | [Repo](https://github.com/SwanseaUniversityMedical/concept-library.git) | Github repository you would like to pull from                                  |
| `--branch`     | `-b`      | `DFTM`                                                                  | Repo's branch you would like to pull from                                      |
| `--profile`    | `-p`      | `live`                                                                  | Name of the docker profile to execute                                          |

#### Setting up your environment variables
> **[!] Note:** This file should be present within the `$RootPath` as described above (modified by passing `-fp [path]` to the deployment script)

This process should be automatic assuming you have ensured that you have an `env-vars.txt` file in your server's directory. The name of this file usually includes a suffix to describe the server's status, e.g. `-FA` for full-access servers or `-RO` for read-only servers.

During manual deployment, the file will be copied and renamed to `env_vars.txt` for use by `docker-compose.prod.yaml` within `./concept-library/CodeListLibrary_project/docker/` after the repository is cloned by the `deploy-feature.sh` script.

#### To deploy manually
1. SSH into the server
2. Skip this step if you have already created the `deploy-feature.sh` within this server:
    - Please clone the [Github repository](https://github.com/SwanseaUniversityMedical/concept-library) and copy/move it into a directory of your choosing (in this case, we will assume it's within /root/)
3. Ensure the `deploy-feature.sh` script has the appropriate permissions
4. Within your terminal, run the following: `/root/deploy-feature.sh`
    - Apply any parameters you would like to add e.g. `/root/deploy-feature.sh --repo Dynamic-Template-Feature-Master`
    - OR; simply edit the variables within the `deploy-feature.sh` script
5. Await the successful build
6. You should now be able to visit the site on the appropriate domain

### 4.1.2. Automated Deployment
> **[!] Todo:** Needs documentation once we move from Gitlab CI/CD -> Harbor

[Details]

#### Files
> ***[!] Note:** The env_file has to (1) be in the same directory as the compose file and (2) be set within the docker-compose.prod.yaml file*

> ***[!] Note:** `/root/` in this case describes the the directory of your choosing* 

If not already present on the machine, please ensure that the following files are within the root directory:
1. Copy `./docker/production/scripts/deploy-site.sh` to `/root/`
2. Copy `./docker/docker-compose.prod.yaml` to `/root/`

If you wish, you can now edit the `deploy-site.sh` to set up any variables that may differ from the other servers. Please see the table below for more information regarding variables and commands that can be passed to `deploy-site.sh`.

### Environment Variables
You need to ensure that there is an `env_vars.txt` within the same directory as the `/root/` directory where your `docker-compose.prod.yaml` is found. 

#### Site Deployment Arguments
Optional parameters for the `deploy-site.sh` script include:

| Command        | Shorthand | Default value              | Description                                                                    |
|----------------|-----------|----------------------------|--------------------------------------------------------------------------------|
| `--file-path`  | `-fp`     | `/root/deploy_DEV_DEMO_DT` | Determines the root path of where the `docker-compose.prod.yaml` file lives    |
| `--foreground` | `-fg`     | `false`                    | Whether the containers will be built in the foreground                         |
| `--no-clean`   | `-nc`     | `true`                     | Whether to clean unused docker containers/images/networks/volumes/build caches |
| `--address`    | `-a`      | _Harbor registry URL_      | Determines the registry we will try to pull the images from                    |
| `--file`       | `-f`      | `docker-compose.prod.yaml` | Name of the docker-compose file you would like to deploy                       |
| `--profile`    | `-p`      | `live`                     | Name of the docker profile to execute                                          |

#### What to do when automated deployment is disabled
> **[!] Todo:** Needs updating after moving to automated, Harbor-driven CI/CD pipeline

Images will be automatically built via Gitlab CI/CD from the `master` branch when a merge is committed. These images can be pulled using the `deploy-site.sh` script as described in [4.1.2. Automated Deployment](#412-Automated-Deployment).

When automated deployment is disabled, which may be the case for certain servers, you can still deploy the images being built by the CI/CD pipeline.

To do so manually, please do the following:

1. Open the terminal and SSH into the server
2. `cd` to the `/root/` directory of the server you are deploying (e.g. `/root/deploy_DEV_DEMO_DT`)
3. Copy the `./docker/production/scripts/deploy-site.sh` and `./docker/docker-compose.prod.yaml` files to this directory (you can do this by pulling them from the Github repository)
4. Ensure you have a `.txt` file named `env_vars.txt` within the same directory as these files
5. Ensure you are logged in, e.g. `docker login {details}` - if you are SSHing into a live server, this step will have already been completed by our config(s)
6. Run the following command `./root/{directory}/deploy-site.sh --address {registry_address}` where the `{registry_address}` describes the address where the Gitlab images are uploaded (check out `.gitlab-ci.yml` for more information)

## 4.2. Harbor-driven CI/CD Pipeline
> **[!] Todo:** Needs documentation once we move from Gitlab CI/CD -> Harbor and have set up automated deployment

[Details]
