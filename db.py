from flask_mysqldb import MySQL


mysql=MySQL()  
# create object of MYSQL Class i.e mysql

def init_db(app):
    app.config['MYSQL_HOST']='localhost'
    app.config['MYSQL_USER']='root'
    app.config['MYSQL_PASSWORD']='Riya@1234'
    app.config['MYSQL_DB']='subscription_mangement'
    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
    mysql.init_app(app)
    # init_app is like pluggin the usb device into the computer 
    

    


