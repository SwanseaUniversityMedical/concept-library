'''
    Test base class

    Set-up and tear-down etc. which are common for unit and functional tests.
'''
import os

SCREEN_DUMP_LOCATION = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'screendumps'
)

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

