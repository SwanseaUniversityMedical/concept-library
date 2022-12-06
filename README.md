# Concept Library
The concept library is a system for storing, managing, sharing, and documenting clinical code lists in health research.  
	
The specific goals of this work are:
- Store code lists along with metadata that captures important information about quality, author, etc.
- Store version history and provide a way to unambiguously reference a particular version of a code list.
- Allow programmatic interaction with code lists via an API, so that they can be directly used in queries, statistical scripts, etc.
- Provide a mechanism for sharing code lists between projects and organizations.

## Live Site
The Concept Library web application is [available here](htttps://conceptlibrary.saildatabank.com).

## User documentation
Concept Library documentation is [available here](https://github.com/SwanseaUniversityMedical/concept-library/wiki/Concept-Library-Documentation).

## Overview
Our goal is to create a system that describes research study designs in a machine-readable format to facilitate rapid study development; higher quality research; easier replication; and sharing of methods between researchers, institutions, and countries.

## Background
A significant aspect of research using routinely collected health records is defining how concepts of interest (including conditions, treatments, symptoms, etc.) will be measured.  This typically involves identifying sets of clinical codes that map to a variable that the researcher wants to measure, and sometimes a set of rules as well (e.g. a sufferer from a disease may be defined as someone who has a diagnosis code from list A and a medication from list B, but excluding anyone who has a code from list C).  A large part of the analysis work may involve consulting clinicians, investigating the data, and creating and testing definitions of clinical concepts to be used.

Often the definitions that are created are of interest to researchers for many studies, but there are barriers to easily sharing them.  The definitions may be embedded within study-specific scripts, such that it is not easy to extract the part that may be of general interest.  Also, often researchers do not fully document how a concept was created, its precise meaning, limitations, etc.  Crucial information may be lost when passing it to other researchers, resulting in mistakes.  Often there simply is no mechanism to discover and share work that has been done previously, leading researchers to waste time and resources reinventing the wheel.  In theory, when research is published, information on the precise methods used should be included, but in reality this is often inadequate.

# Table of contents
1. [Clone this repository](#1.-Clone-this-Repository)  
2. [Setup with Docker](#2.-Setup-with-Docker)  
  2.1. [Prerequisites](#2.1.-Prerequisites)  
  2.1.1. [Running on Apple](#2.1.1.-Running-on-Apple)  
  2.2. [Database Setup](#2.2.-Database-Setup)  
    2.2.2. [Restore from Git Repository](#2.2.2.-Restore-from-Git-Repository)  
    2.2.3. [Migration only](#2.2.3.-Migration-only)  
    2.2.1. [Restore from Local Backup](#2.2.1.-Restore-from-Local-Backup)  
  2.3. [Development](#2.3.-Development)  
    2.3.1. [Initial Build](#2.3.1.-Initial-Build)  
    2.3.2. [Stopping and Starting the Containers](#2.3.2.-Stopping-and-Starting-the-Containers)  
    2.3.3. [Live Working](#2.3.3.-Live-Working)  
    2.3.4. [Removing the Containers](#2.3.4.-Removing-the-Containers)  
  2.4. [Accessing and Exporting the Database](#2.4.-Accessing-and-Exporting-the-Database)  
    2.4.1. [Access/Export with PGAdmin4](#2.4.1.-Access/Export-with-PGAdmin4)  
    2.4.2. [Access/Export with CLI](#2.4.2.-Access/Export-with-CLI)  
  2.5. [Debugging and Running Tests](#2.5.-Debugging-and-Running-Tests)  
    2.5.1. [Django logging](#2.5.1.-Django-Logging)  
    2.5.2. [Debug Tools in Visual Studio Code](#2.5.2.-Debug-Tools-in-Visual-Studio-Code)  
    2.5.3. [Running Tests](#2.5.3.-Running-Tests)  
  2.6. [Creating a Superuser](#2.6-Creating-a-Superuser)
3. [Setup without Docker](#3.-Setup-without-Docker)  
  3.1. [Prerequisites](#3.1.-Prerequisites)  
  3.2. [Installing](#3.2.-Installing)  
  3.3. [Running Tests](#3.3.-Running-Tests)  
4. [Deployment](#4.-Deployment)  
  4.1. [Running Tests](#4.1.-Running-Tests)  

# 1. Clone this Repository
To download this repository:
1. Ensure that you have installed Git (e.g. [Git for Windows](https://gitforwindows.org/)).
2. Open a terminal
3. Navigate to the folder you want to clone this repository into
4. Run the command:  
`git clone https://github.com/SwanseaUniversityMedical/concept-library.git`

# 2. Setup with Docker

## 2.1. Prerequisites
Please ensure that you have installed [Docker Desktop v4.10.1](https://docs.docker.com/desktop/release-notes/) or [Docker Engine v20.10.17](https://docs.docker.com/engine/release-notes/).

If you encounter any issues, please see Docker's documentation (https://docs.docker.com/).

## 2.1.1. Running on Apple

The app container requires emulation for ARM CPUs, please install Rosetta 2:
1. Open a terminal
2. Run: `softwareupdate --install-rosetta`

## 2.2. Database setup

### 2.2.1. Restore from Local Backup
To restore from a local backup:
1. Navigate to the `concept-library/docker/development` folder
2. Place a `.backup` file inside of the `db` folder  
>**Note: Do not share this file with anyone**
3. Skip to [2.3. Development](#2.3.-Development)  

### 2.2.2. Restore from Git Repository
>*Note:  
The initial run of the application may take a while if you are using this method, however, subsequent builds will be faster as the backup is saved locally in the `concept-library/docker/development/db/` folder*

To restore from a Git repository:
1. Create a personal access token on GitHub (https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token), ensure it grants access to private repositories
2. Navigate to the `concept-library/docker/development/` folder
3. Duplicate the `example.git.token` inside of `development/db/`
4. Rename the duplicated file to `git.token`
5. Delete the contents of the file and paste your personal access token
>**Note: Do not share this file with anyone**
6. Open the `docker-compose.yaml` file inside of the `docker/` folder
7. Ensure that the environment variable `POSTGRES_RESTORE_REPO` is set to the correct GitHub repository where your `.backup` file is stored
8. Skip to [2.3. Development](#2.3.-Development)  

### 2.2.3. Migration only
If you do not have a backup available the application will still run successfully as migrations are automatically applied, however, no data will be restored. Please skip to [2.3. Development](#2.3.-Development).

## 2.3. Development
### 2.3.1. Initial Build
To perform the initial build and run of the application:
1. Open a terminal
2. Navgiate to the `concept-library/docker/` folder
3. In the terminal, run `docker compose up --build`

The application and database will be available at:
 - Application: `127.0.0.1:8000`
 - Database: `127.0.0.1:5432`

### 2.3.2. Stopping and Starting the Containers
To stop the docker container:
1. If you have a terminal open which is running the docker containers, press `ctrl+c`
2. If you do not have a terminal open which is running the containers:  
a. Open a terminal  
b. Navigate to the `concept-library/docker/` folder  
c. In the terminal, run `docker compose stop`  

To start the docker container (if it has already been built and has stopped for any reason):
1. Open a terminal
2. Navigate to the `concept-library/docker/` folder
3. In the terminal, run `docker compose start`

### 2.3.3. Live Working
Whilst working on the codebase, any changes should be automatically applied to the codebase stored in the app container after saving the file. 

If you make any changes to the models you will need to:  
1. Stop and start the containers again with `docker compose up`, the migrations will be automatically applied
2. *OR*; execute the migration code from within the app container (see: https://docs.docker.com/engine/reference/commandline/exec/)

### 2.3.4. Removing the Containers
To remove the containers:
1. Open a terminal
2. Navigate to the `concept-library/docker/` folder
3. In the terminal, run:  
a. `docker compose down`: removes networks and containers.  
b. *OR;* `docker-compose down --rmi all -v`: removes networks, containers, images and volumes.

## 2.4. Accessing and Exporting the Database
>*Note:   
If you have made changes to the environment variables in the docker-compose.yaml file you will need to match those changes when connecting through the CLI or PGAdmin4*

### 2.4.1. Access/Export with PGAdmin4
*To access the database:*  
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

*To export the database:*  
1. Ensure the Docker container is running
2. Open PGAdmin4
3. Connect to the `docker-concept-library` server
4. Right click the `concept_library` database and click `Backup...`
5. In the filename input field, enter the directory and name to save the backup file as. Ensure you save the file as a `.backup`
6. Click the `Backup` button

### 2.4.2. Access/Export with CLI
*To access the database:*  
1. Open a terminal
2. In the terminal, run: `docker exec -it concept-library-development-postgres-1 /bin/bash`
3. Query the database:  
a. Initiate an active session with `psql -U clluser concept_library` and then run queries directly, e.g. `SELECT * FROM CLINICALCODE_PHENOTYPES LIMIT 1;`  
b. *OR;* run a query directly with `psql -U clluser -d concept_library 'SELECT * FROM CLINICALCODE_PHENOTYPES LIMIT 1;'`
> *Note: The query will fail to retrieve results if you forget the semicolon, `;`, at the end of the query*

*To export the database:*  
1. Open a terminal
2. In the terminall, run: `docker exec -it concept-library-development-postgres-1 /bin/bash`
3. Replace `[filename]` with the file name desired and run:  
`pg_dump -U postgres -F c concept_library > [filename].backup`

## 2.5. Debugging and Running Tests

### 2.5.1. Django Logging
Django logging is enabled by default, you can view the logs in the terminal used to start the docker container. 

To disable the verbose logging:
1. In docker-compose.yaml set `tty: false` under the `app` service
2. In docker-compose.yaml set `DEBUG: false` under the `environment` section of the `app` service

### 2.5.2. Debug Tools in Visual Studio Code
Before continuing, open the `docker-compose.yaml` file and ensure the `DEBUG_TOOLS` variable in the `app` container definition is set to true.

Create a run configuration for the project:
1. Create a new folder and name it `.vscode`
2. Create a new file within that folder and name it `launch.json`
3. Paste the json below into the new file and then save the file

```
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
      "port": 3000,
      "host": "127.0.0.1"
    }
  ]
}
```

Now you're ready to start debugging:
1. Build the container `docker compose up --build` and ensure it is running
2. Add a breakpoint to the file that you are debugging
3. In Visual Studio Code, open the `Run and Debug Menu` by clicking the icon on the left-hand side of the screen or using the hotkey `Ctrl+Shift+D`
4. At the top of the debug menu, select the `Debug Application` option
5. Press the run button and start debugging

Variables, Watch and Callstack can all be viewed in the `Run and Debug` menu panel and the console can be viewed in the `Debug Console` (hotkey: `Ctrl+Shift+Y`) window.

### 2.5.3. Running Tests
To run tests on the container, you first need to:
1. Build the container `docker compose up --build` and ensure it is running
2. Open a terminal
3. In the terminal, run: `docker exec -it concept-library-development-postgres-1 /bin/bash`
4. Navigate to the directory containing the codebase by running: `cd /var/www/CodeListLibrary_project`
5. As described below, enter a command to run the tests

*All tests*  
To run all tests except for read-only tests, run:  
`python manage.py test --noinput`

*Read-only tests*  
> **Note: Read-only tests must take the settings from read_only_test_settings.py otherwise they will fail**  

To run only the read-only functional tests, run:  
`python manage.py test --noinput clinicalcode.tests.functional_tests.read_only`  

To run only the read-only unit tests, run:  
`python manage.py test --noinput clinicalcode.tests.unit_tests.read_only`

## 2.6. Creating a Superuser

To create a superuser:
1. Ensure the docker container is running and open a new terminal
2. Run `docker exec -it concept-library-development-app-1 /bin/bash`
3. Navigate to the CodeListLibrary_project directory by running: `cd /var/www/CodeListLibrary_project`
4. Run `python manage.py createsuperuser` and follow the instructions in the terminal to create the user
5. Verify that the user was created properly by navigating to the website and logging in with the credentials entered

# 3. Setup without Docker

## 3.1. Prerequisites
Please ensure that you have the following installed:
1. [Python 3.9](https://www.python.org/downloads/release/python-390/)
2. [Pip](#installing-pip) 
3. [MSVC C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
4. [PostgreSQL 14.4](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
5. [PGAdmin4](https://www.pgadmin.org/download/pgadmin-4-windows/)

## 3.2. Installing
**Get CodeListLibrary code from git**

Open command window as administrator 

Navigate to your folder where you store all of your code. For example:

c:/dev/

Then type the following command:  

*> git clone git-url*


To begin with, you will want to work on the master branch so you will need to checkout the master branch by typing the following in the command window: 

*> git checkout master*

**Install virtualenv and virtualenvwrapper**

This will provide a dedicated environment for each project you create. It is considered best practice and will save time when you’re ready to deploy your project.

Open your command window and type:

*> pip install virtualenvwrapper-win*

Now change directory to where you have downloaded the project e.g. C:\\Dev\\CodeListLibrary_root

To create a virtualenv to install all of your packages for your project type:

*> mkvirtualenv cclproject*

Note:

To work on a virtual environment to install packages then type:

*> workon <virtualenv name>*

To cancel working within a virtualenv type:

*> deactivate <virtualenv name>*

To install the required packages there is a txt file containing all the required packages, this makes it easy to install correct versions of each package, please enter the following into the command line:

*> pip install –r requirements/local.txt*

This is the equivalent of installing:

*> pip install Django==1.11.3*

*> pip install django-mathfilters==0.4.0*

*> pip install django-simple-history==1.9.0*

*> pip install djangorestframework==3.6.3*

*> pip install pathlib==1.0.1*

*> pip install psycopg2==2.7.1*

*> pip install pytz==2017.2*

Then install pandas

*> pip2 install pandas*

Note:

Within the requirements folder there are more .txt for staging and production in case they ever did differentiate for each environment.

**Database setup**

Using PGAdmin3

1. Create a role called clluser
2. Create a database called code_list_library
3. Create a read-only role

When running the application it complains that you have unapplied migrations; your app may not work properly until they are applied. So in the command window type:
*> python manage.py makemigrations*

*> python manage.py migrate*

To run the application from the command window you need to change directory to where the manage.py file exists and then type:

*> python manage.py runserver*

Press Ctrl + break to stop the server

**Administration area**
There are no users in your database. So we need to create a superuser in order to access the administration site to manage other users.

Open the command line and execute:

*> python manage.py createsuperuser*

Fill in the desired username, email and password

When the development server is running you can access the admin section by going to the following url:
http://127.0.0.1:8000/admin/

**Get it working within Eclipse**

File -> Open projects from file system

Browse to code e.g. C:\\Dev\\CodeListLibrary_root

**Point your python interpreter to your VirtualEnv python Intepreter**

Presuming you have created a virtualenv and installed all of your packages then you need to point your python interpreter to the virtualenv. So within Eclipse go to:

Window -> Preferences

Select PyDev -> Intepreters -> Python Interpreter

Click New

Enter Interpreter name e.g. CCLProjectPython

And browse to the python executable e.g. C:\\Users\\\<user\>\\Envs\\cclproject\\Scripts\\python.exe and then click Ok.

Select all folders to be added to the system pythonpath

To run Right Click cll project and click debug as -> PyDev: Django

You should see the that you have started the development server at http://127.0.0.1:8000/


**Importing coding systems into the code list library**

Concept library has 4 coding systems:

1. Read cdde v2
2. Read code v3
3. ICD10
4. OPCS4

*Due to governance, coding system cannot be shared.*

The coding systems/codes needs to be imported to the dataase.

**Install ldap functionality**

For windows machines I had to install Microsoft Visual C++ compiler for python 2.7

https://www.microsoft.com/en-us/download/details.aspx?id=44266

Download python_ldap 2.4.44 cp27 cp27m win_amd64 from the following location:

https://www.lfd.uci.edu/~gohlke/pythonlibs/#python-ldap

Within your virtualenv run the following command (change the <username> section):

pip install C:\\Users\\<username>\\Downloads\\python_ldap-2.4.44-cp27-cp27m-win_amd64.whl

Then run:

pip install django-auth-ldap

For reference see:

https://django-auth-ldap.readthedocs.io/en/1.2.x/install.html

If we are to use ldap over ssl then we’ll need to follow this example:

https://support.microsoft.com/en-us/help/938703/how-to-troubleshoot-ldap-over-ssl-connection-problems

## 3.3. Running Tests
To run all the tests you need to run THREE commands:  
- python manage.py test  --noinput  
- python manage.py test  --noinput clinicalcode.tests.functional_tests.read_only  
- python manage.py test  --noinput clinicalcode.tests.unit_tests.read_only  

The first one will run all the tests except read only tests. It is necessary  because normal tests will take settings from settings.py
The second one runs READ_ONLY tests. It takes settings from read_only_test_settings.py. Read_only tests must take settings from read_only_test_settings.py otherwise they will fail.

manage.py manage which settings file is read. If a command contains read_only phrase then it reads read_only_test_settings.py otherwise settings.py

# 4. Deployment
(TODO) Deployment is done through GIT CI and docker. 

## 4.1. Running Tests
first set REMOTE_TEST = True in both test_settings.py and read_only_settings.py

Go into the webapp docker container: `docker exec -it concept-library-dev-db_webapp_1 /bin/bash`

Load the environment: `source /var/www/concept_lib_sites/v1/cllvirenv_v1/bin/activate`

Go into the project folder: `cd /var/www/concept_lib_sites/v1/CodeListLibrary_project`

Execute the tests: `python manage.py test --noinput`
