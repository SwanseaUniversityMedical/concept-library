from dateutil.parser import parse

import re
import datetime

def get_column_index(col_1, col_2, col_3, col_4, col_5, col_6, value):
    # find the category column
    if col_1 == value:
        return 0
    elif col_2 == value:
        return 1
    elif col_3 == value:
        return 2
    elif col_4 == value:
        return 3
    elif col_5 == value:
        return 4
    elif col_6 == value:
        return 5
    else:
        return


def get_column_index_by_text(code_col, code_desc_col, cat_col, cat_desc_col, sub_cat_col, sub_cat_desc_col, search_column):

    if search_column == 'code':
        return code_col
    elif search_column == 'desc':
        return code_desc_col
    elif search_column == 'cat':
        return cat_col
    elif search_column == 'cat_desc':
        return cat_desc_col
    elif search_column == 'sub_cat':
        return sub_cat_col
    elif search_column == 'sub_cat_desc':
        return sub_cat_desc_col
    else:
        return


def isDateTime(x):
    try:
        parse(x)
        #return isinstance(x, datetime.datetime)
    except ValueError:
        return False
    else:
        return True


def isFloat(x):
    try:
        a = float(x)
    except ValueError:
        return False
    else:
        return True


def isInt(x):
    try:
        a = float(x)
        b = int(a)
    except ValueError:
        return False
    else:
        return a == b


def get_int_value(value, default_value):
    if value is not None and isInt(value):
        return int(value)
    else:
        return default_value


def detect_sql_meta_characters(value):
    # reference https://www.symantec.com/connect/articles/detection-sql-injection-and-cross-site-scripting-attacks
    # detect either the hex equivalent of the single-quote, the single-quote itself or the presence of the double-dash. 
    # These are SQL characters for MS SQL Server and Oracle, which denote the beginning of a comment, and everything that follows is ignored. 
    # Additionally, if you're using MySQL, you need to check for presence of the '#' or its hex-equivalent. 
    # We do not need to check for the hex-equivalent of the double-dash, because it is not an HTML meta-character and will not be encoded by the browser

    match_obj = re.search(r'/(\%27)|(\')|(\-\-)|(\%23)|(#)/ix', value, re.M|re.I)

    if match_obj:
        return True
    else:
        return False


def detect_modified_sql_meta_characters(value):
    # reference https://www.symantec.com/connect/articles/detection-sql-injection-and-cross-site-scripting-attacks
    # This signature first looks out for the = sign or its hex equivalent (%3D).
    # It then allows for zero or more non-newline characters, 
    # and then it checks for the single-quote, the double-dash or the semi-colon.

    match_obj = re.search(r'/((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))/i', value)

    if match_obj:
        return True
    else:
        return False


def detect_typical_sql_injection_attack(value):
    # reference https://www.symantec.com/connect/articles/detection-sql-injection-and-cross-site-scripting-attacks
    # \w* - zero or more alphanumeric or underscore characters
    # (\%27)|\' - the ubiquitous single-quote or its hex equivalent
    # (\%6F)|o|(\%4F))((\%72)|r|(\%52) - the word 'or' with various combinations of its upper and lower case hex equivalents.

    match_obj = re.search(r'/\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))/ix', value, re.M|re.I)

    if match_obj:
        return True
    else:
        return False


def detect_sql_injection_with_keywords(value):
    # reference https://www.symantec.com/connect/articles/detection-sql-injection-and-cross-site-scripting-attacks
    # /((\%27)|(\'))union/ix
    # (\%27)|(\') - the single-quote and its hex equivalent
    # union - the keyword union

    match_obj = re.search(r"('(''|[^'])*')|(;)|(\b(ALTER|CREATE|DELETE|DROP|EXEC(UTE){0,1}|INSERT( +INTO){0,1}|MERGE|SELECT|UPDATE|UNION( +ALL){0,1})\b)", value, re.M|re.I)

    if match_obj:
        return True
    else:
        return False


def has_sql_injection(value):
    if detect_sql_injection_with_keywords(value) | detect_sql_meta_characters(value):
        return True
    else:
        return False


def get_bool_value(value , default_value):
    if value.lower() == "true":
        return True
    elif value.lower() == "false":
        return False
    else:
        return default_value

def get_paginator_pages(paginator, page):
    # number of pages
    np = paginator.num_pages
    # current page
    cp = page.number
    # returned pages list
    pl = []
    # left  fill '...'
    lf = False
    # right  fill '...'
    rf = False
    # middle  fill '...'
    mf = False
    for p in range(1, np+1):              
        if np <=10:                
            pl.append(p)
        else:
            if (cp <= 4 and p <=5) or ((cp >= np-4) and p >= np-4) or ( p==1 or p==np):
                pl.append(p)
            elif (cp > 4 and cp < np-4  and (p != 1 and p != np and p > 5 and p < np-4)):
                if not mf:
                    mf = True
                    pl.append(cp-1)
                    pl.append(cp)
                    pl.append(cp+1)
            else:
                if (not lf) and p<cp:
                    lf = True
                    pl.append('...')
                elif (not rf) and p>cp:
                    rf = True
                    pl.append('...')
        
#     print ', '.join([str(i) for i in pl])
    return pl

def clean_str_as_db_col_name(txt):
    # clean string to be a valid column name
    
    s = txt.strip()
    s = s.replace(' ', '_').replace('.', '_').replace('-', '_')
    if isInt(s[0]):
        s = '_' + s
        
    s = re.sub('_+', '_', s)
    return re.sub('[^A-Za-z0-9_]+', '', s)


    
    
    