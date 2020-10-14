from django.db import connection, transaction
from faker import Faker

# Create your tests here.


def generate_codes():
    ''' 
        if you want to test your local database with high volume data then call this procedure 
        this method currently populates a coding system table with many records
    '''

    fake = Faker()

    with transaction.atomic():
        with connection.cursor() as cursor:
            for _ in range(0, 1000000):
                cursor.execute("insert into clinicalcode_lookup (code, description) values (%s, %s); ", [fake.ean(length=8), fake.text(max_nb_chars=250, ext_word_list=None)])


generate_codes()