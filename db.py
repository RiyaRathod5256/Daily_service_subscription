import os
import pymysql
from urllib.parse import urlparse

def get_connection():

    db_url = urlparse(os.getenv("MYSQL_URL"))

    return pymysql.connect(
        host=db_url.hostname,
        user=db_url.username,
        password=db_url.password,
        database=db_url.path[1:],
        port=db_url.port,
        cursorclass=pymysql.cursors.DictCursor
    )

