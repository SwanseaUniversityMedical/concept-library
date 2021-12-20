from django.conf import settings


class ClinicalCode(object):
    ''' class to store clinical code session information '''
    def __init__(self, request):
        self.session = request.session
        clinicalcode = self.session.get(settings.CLINICALCODE_SESSION_ID)

        if not clinicalcode:
            # save an empty clinicalcode in the session
            clinicalcode = self.session[settings.CLINICALCODE_SESSION_ID] = {}
            clinicalcode['page_size']

        self.clinicalCode = clinicalcode

        # store concept search information
        # self.page_size = int(self.session.get('page_size'), 20)
        # self.page = int(self.session.get('page'), 1)
        # self.search = str(self.session.get('search'), None)

    def save(self):
        # update the session
        self.session[settings.CLINICALCODE_SESSION_ID] = self.clinicalcode
        # mark the session as "modified" to make sure it is saved
        self.session.modified = True

    def clear(self):
        self.session[settings.CLINIALCODE_SESSION_ID] = {}
        self.session.modified = True
