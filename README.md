# concept-library
Concept Library web application (conceptlibrary.saildatabank.com)
	
The concept library is a system for storing, managing, sharing, and documenting clinical code lists in health research.  
	
The specific goals of this work are:
* Store code lists along with metadata that captures important information about quality, author, etc.
* Store version history and provide a way to unambiguously reference a particular version of a code list.
* Allow programmatic interaction with code lists via an API, so that they can be directly used in queries, statistical scripts, etc.
* Provide a mechanism for sharing code lists between projects and organizations.


## Documentation

Concept Library documentation is available at this URL  

[https://docs.hiru.swan.ac.uk/display/SATP/Concept+Library+Documentation](https://docs.hiru.swan.ac.uk/display/SATP/Concept+Library+Documentation)

## Background

A significant aspect of research using routinely collected health records is defining how concepts of interest (including conditions, treatments, symptoms, etc.) will be measured.  This typically involves identifying sets of clinical codes that map to a variable that the researcher wants to measure, and sometimes a set of rules as well (e.g. a sufferer from a disease may be defined as someone who has a diagnosis code from list A and a medication from list B, but excluding anyone who has a code from list C).  A large part of the analysis work may involve consulting clinicians, investigating the data, and creating and testing definitions of clinical concepts to be used.


Often the definitions that are created are of interest to researchers for many studies, but there are barriers to easily sharing them.  The definitions may be embedded within study-specific scripts, such that it is not easy to extract the part that may be of general interest.  Also, often researchers do not fully document how a concept was created, its precise meaning, limitations, etc.  Crucial information may be lost when passing it to other researchers, resulting in mistakes.  Often there simply is no mechanism to discover and share work that has been done previously, leading researchers to waste time and resources reinventing the wheel.  In theory, when research is published, information on the precise methods used should be included, but in reality this is often inadequate.
	
# Overview

Our goal is to create a system that describes research study designs in a machine-readable format to facilitate rapid study development; higher quality research; easier replication; and sharing of methods between researchers, institutions, and countries.  

# Development

**Prerequisites**

Ensure you have the following installed:

Python 2.7

Pip

PostgreSQL

PGAdmin3

Eclipse

Git

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

# Deployment

Deployment is done through GIT CI and docker.


