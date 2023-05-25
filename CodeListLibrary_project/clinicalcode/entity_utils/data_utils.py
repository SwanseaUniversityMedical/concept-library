from django.db import connection
from django.apps import apps
from django.conf import settings

import traceback

CREATE_EXTENSION_QUERY = '''CREATE EXTENSION IF NOT EXISTS {ext} SCHEMA public;'''

DROP_EXTENSION_QUERY = '''DROP EXTENSION {ext};'''

SELECT_DUPLICATES_QUERY = '''
SELECT *
FROM (
  SELECT LEVENSHTEIN(T1.{field_name}, T2.{field_name}) AS SIMILARITY, 
      T1.{pk_name} as NEEDLE_ID, T1.{field_name} as NEEDLE,
      T2.{pk_name} as HAYSTACK_ID, T2.{field_name} as HAYSTACK
  FROM public.{table_name} AS T1
  JOIN public.{table_name} AS T2
    ON T1.{field_name} LIKE '%' || T2.{field_name} || '%' AND T1.{pk_name} != T2.{pk_name}
) AS POSSIBLE_DUPLICATES
WHERE POSSIBLE_DUPLICATES.SIMILARITY < {min_similarity}
ORDER BY POSSIBLE_DUPLICATES.SIMILARITY ASC;
'''

def try_find_duplicates(model, pk_name='ID', field_name='NAME', min_similarity=20, drop_ext=False):
    """
        [!] Note: The column defined by field_name must be a string-like datatype

        Compares rows in a table, given its pk field name, and the comparator field

        Args:
            model {django.models.Model}: The model that will be examined

            pk_name {string}: The name of the model's primary key field

            field_name {string}: The name of the model's field that we want to compare

            min_similarity {number}: Limits results where similarity < min_similarity

            drop_ext {boolean}: Whether to drop the extension after use
        
        Returns:
            - Returns a {list} containing the rows that may be duplicated
    """

    result = [ ]
    table_name = model._meta.db_table
    try:
        with connection.cursor() as cursor:
            # First try to create fuzzystrmatch extension if not present
            query = CREATE_EXTENSION_QUERY.format(ext='fuzzystrmatch')
            cursor.execute(query)

            # Run the LDA query and return results
            query = SELECT_DUPLICATES_QUERY.format(
                table_name=table_name,
                pk_name=pk_name,
                field_name=field_name,
                min_similarity=min_similarity
            )
            cursor.execute(query)

            columns = [col[0] for col in cursor.description]
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]

            # Drop the extension if requested
            if drop_ext:
                query = DROP_EXTENSION_QUERY.format(ext='fuzzystrmatch')
                cursor.execute(query)
    except Exception:
        print(f'Failed to run duplicate query for {table_name} with error:')
        traceback.print_exc()

    return result
