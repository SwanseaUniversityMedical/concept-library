'''
    Test base class

    Set-up and tear-down etc. which are common for unit and functional tests.
'''
import os

import urllib3
from django.db import connection, connections  # , transaction

SCREEN_DUMP_LOCATION = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'screendumps')
'''
    Global test parameters.
'''
su_user = 'superuser'
su_password = 'superuserPassword'
ow_user = 'owneruser'
ow_password = 'owneruserPassword'
gp_user = 'groupuser'
gp_password = 'groupuserPassword'
vgp_user = 'viewGroupUser'
vgp_password = 'viewGroupUserPassword'
egp_user = 'editGroupUser'
egp_password = 'editGroupUserPassword'
nm_user = 'reginald'
nm_password = 'reginaldspassword'
Google_website = "https://www.google.com"


def update_friendly_id():
    update_sqls = [
        "UPDATE clinicalcode_historicalconcept       SET       friendly_id = concat('C', cast(id as text));",
        "UPDATE clinicalcode_concept                 SET       friendly_id = concat('C', cast(id as text));",
        "UPDATE clinicalcode_historicalworkingset    SET       friendly_id = concat('WS', cast(id as text));",
        "UPDATE clinicalcode_workingset              SET       friendly_id = concat('WS', cast(id as text));"
    ]

    for sql in update_sqls:
        with connection.cursor() as cursor:
            try:
                cursor.execute(sql)
            except:
                pass

    print("######  update_friendly_id   #############################")


def save_stat(host):
    url_run = host + "/admin/run-stat/"
    http = urllib3.PoolManager()
    resp_stat = http.request("GET", url_run)

    print((str(resp_stat.status) + "#### Run-stat ####"))

    url_save = host + "/admin/run-stat-filters/"
    resp_stat = http.request("GET", url_save)

    print((str(resp_stat.status) + "#### Run-stat-filters save ####"))
