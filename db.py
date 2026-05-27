

import os
from flask_mysqldb import MySQL

mysql = MySQL()

def init_db(app):

    app.config['MYSQL_HOST'] = os.getenv('MYSQLHOST', 'localhost')
    app.config['MYSQL_USER'] = os.getenv('MYSQLUSER', 'root')
    app.config['MYSQL_PASSWORD'] = os.getenv('MYSQLPASSWORD', 'Riya@1234')
    app.config['MYSQL_DB'] = os.getenv('MYSQLDATABASE', 'subscription_mangement')
    app.config['MYSQL_PORT'] = int(os.getenv('MYSQLPORT', 3306))
    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
    mysql.init_app(app)
    


