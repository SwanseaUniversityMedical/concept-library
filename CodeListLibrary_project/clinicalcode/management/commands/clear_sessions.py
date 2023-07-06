from django.core.management.base import BaseCommand
from django.db import connection, transaction

class Command(BaseCommand):
    help = 'Cleans the session data'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        '''
            Removes sessions from the db that have expired
        '''
        with connection.cursor() as cursor:
            cursor.execute('''DELETE FROM django_session WHERE expire_date<now();''')
