from flask import Flask, render_template,request,flash,redirect,url_for,session
from db import get_connection
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import timedelta,datetime

app = Flask(__name__)
app.secret_key = "123456"


@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method == "POST":
        name=request.form['username']
        email=request.form['email']
        password=request.form['password']
        phone=request.form['phone']
        email=email.lower()
        # validation
        # empty fields

        if not name  or  not email or not password or not phone:
            flash("All fields are required","empty")
            return  redirect(url_for("register"))
        username_pattern = r'^[a-zA-Z_][a-zA-Z0-9_.@#$%^&*!-]{2,60}$'
        if not re.match(username_pattern, name):
            flash("Username must start with a letter or _ and can contain letter, number, and underscore,special character (3-60 characters) ,space is not allowed", "error")
            return redirect(url_for("register"))
        
        if len(name)<3:
            flash("Username is too short","error")
            return redirect(url_for("register"))
        if len(name)>60:
            flash("Username is too long must be less tahn 60 characters")
            return redirect(url_for("register"))
        
        if re.search(r'(.)\1{4,}', name):
            flash("Username cannot have too many repeated characters", "error")
            return redirect(url_for("register"))
        
        if not phone.isdigit() or len(phone) != 10:
            flash("Invalid phone number number must be of 10 digits and start with 6,7,8,9","error")
            return redirect(url_for("register"))
        
        email_pattern = r'^[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9]+([.-][A-Za-z0-9]+)*\.[A-Za-z]{2,}$'
        if not re.fullmatch(email_pattern, email):
            flash("invalid email format ","error")
            return redirect(url_for("register"))
        
        if len(email)>70:
            flash("invalid email length must be less than 70 characters")
        
        if len(password)<8 or len(password)>15:
            flash("password must be of 8 to 15 characters","error")
            return redirect(url_for("register"))
        
        phone_pattern = r'^(?!.*(\d)(?:.*\1){5})[6-9]\d{9}$'

        if not re.match(phone_pattern, phone):
            flash("Enter a valid 10-digit phone number and must start with 6,7,8,9 and number not repeat more than 5 ", "error")
            return redirect(url_for("register"))
        # email dupliacte
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("select * from user1 where useremail=%s",(email,))

        user= cur.fetchone()
        
        if user:
            cur.close()
            flash("user already registered","error")
            return redirect(url_for("register"))
        
        cur.execute("select * from user1 where userphonenumber=%s",(phone,))
        phone=cur.fetchone()

        if phone:
            cur.close()
            flash("phone number already registered","error")
            return redirect(url_for("register"))

        password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
        if not re.match(password_pattern, password):
            flash("Password must be at least 8 characters and atmost 15 character long and include uppercase, lowercase, number, and special character." , "error")
            return redirect(url_for("register"))

        hash_password=generate_password_hash(password)

        cur.execute("insert into user1(username,useremail,userpassword,userphonenumber)VALUES(%s,%s,%s,%s)",(name,email,hash_password,phone))
        print(name)
        print(email)
        print(password)
        print(phone)
        
        conn.commit()
        conn.close()

        flash("Registration successfull","success")
        return redirect(url_for ("login"))
    return render_template("signup.html")




#login logic
@app.route("/login",methods=("POST","GET"))
def login():
    if(request.method=="POST"):
        email=request.form["email"]
        password=request.form["password"]
        
        email_pattern=r'^[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9]+([.-][A-Za-z0-9]+)*\.[A-Za-z]{2,}$'
        if not re.match(email_pattern, email):
            print("login")
            flash("Enter a valid Gmail (start with letter or underscore)", "error")
            return redirect(url_for("login"))

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("select useremail from user1 where useremail=%s",(email,))
        user_email= cur.fetchone()

        

        if user_email:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("select userpassword from user1 where useremail=%s",(email,))
            stored_password=cur.fetchone()
            
            
            if stored_password and check_password_hash(stored_password["userpassword"],password):
                cur.execute("select user1_id,useremail,username from user1 where useremail=%s",(email,))
                user_details=cur.fetchone()
                print(user_details)
                conn.commit()
                conn.close()
                session["user_id"]=user_details["user1_id"]
                session["user_email"]=user_details["useremail"]
                session["user_name"]=user_details["username"]
                session["loggedin"]=True


                flash("login Successful!","success")
                return redirect(url_for("dashboard"))
            else:
                flash("incorrect password","error")
                return redirect(url_for("login"))


        else:
            flash("user does not exist","error")

    return render_template("login.html")
        

#dashboard logic               
@app.route("/dashboard",methods=("POST","GET"))
def dashboard():
    if "loggedin" not in session:
        return redirect(url_for("login"))

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    SELECT 
        service.service_id,
        subscriptions.start_date,
        subscriptions.end_date,
        subscriptions.status,
        BIN_TO_UUID(subscriptions.uuid_id) AS uuid,
        subscriptions.user1_id,
        service.service_name,
        Billing.bill_status
        FROM subscriptions
    JOIN service 
        ON subscriptions.service_id = service.service_id
    LEFT JOIN Billing 
        ON subscriptions.uuid_id = Billing.subscription_id
    WHERE subscriptions.user1_id = %s
""", (session["user_id"],))
    subscriptions_list=cur.fetchall()
    
    print(subscriptions_list)

    active=0
    paused=0
    due=0
    total=0
    #logic to calculate numbers 
    for sub in subscriptions_list:
        if sub["status"]=="active":
            active+=1
        elif sub["status"]=="paused":
            paused+=1
    
    total=active+paused
    for sub in subscriptions_list:
        if sub["bill_status"]=="unpaid":
            due+=1
        elif sub["bill_status"]=="Unpaid":
            due+=1
        
    
    return render_template("dashboard.html",subscriptions=subscriptions_list,active=active,paused=paused,due=due,total=total,)

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for("login"))
    
   

   
   
    
   
   

#add service
@app.route("/addservice",methods=("POST","GET"))
def addservice():
    if(request.method=="POST"):
        service_name=request.form["service_name"]
        service_provider=request.form["provider"]
        service_provider_number=request.form["number"]
        service_provider_address=request.form["address"]
        price_per_day=request.form["price"]
        daily_quantity=request.form["quantity"]
        start_date=request.form["start"]
        end_date=request.form["end"]
        #empty
        if not service_name or not service_provider  or not service_provider_number or not service_provider_address or not price_per_day or not daily_quantity or not start_date or not end_date:
            flash("All fields are required","error")
            return redirect(url_for("addservice"))
        #regex
        service_name_pattern = r"^[A-Za-z]+( [A-Za-z]+)*$"
        provider_pattern ="^(?!.*(.)\1{3,})[A-Za-z]+( [A-Za-z]+)*$"
        phone_pattern = r'^(?!.*(\d)(?:.*\1){5})[6-9]\d{9}$'
        address_pattern = r"^[A-Za-z0-9\s,.-]{5,}$"
        price_pattern = r"^\d+(\.\d{1,2})?$"
        quantity_pattern = r"^[1-9]\d"
        
        

        if not re.match(service_name_pattern,service_name):
            flash("Invalid Service Name ,Only alphabets with single space between words allowed","error")
            return redirect(url_for("addservice"))
        
        if not re.match(provider_pattern,service_provider):
            flash("invalid provider name Only alphabets, single space between words, max 3 repeated letters allowed","error")
            return redirect(url_for("addservice"))
        
        if not re.match(phone_pattern,service_provider_number):
            flash("invalid phone number format")
            return redirect(url_for("addservice"))
        
        if not re.match(address_pattern,service_provider_address):
            flash("invalid address pattern")
            return redirect(url_for("addservice"))
        
        

        price_per_day = price_per_day.strip()
        print(repr(price_per_day))  # debug

        if not re.fullmatch(price_pattern, price_per_day):
            flash("invalid price pattern")
            return redirect(url_for("addservice"))
                
        daily_quantity = daily_quantity.strip()

        if not re.fullmatch(r"^[1-9]\d*$", daily_quantity):
            flash("invalid quantity pattern")
            return redirect(url_for("addservice")) 
                
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

        if start_date_obj > end_date_obj:
            flash("Start date cannot be greater than end date", "error")
            return redirect(url_for("addservice"))
        
        conn = get_connection()
        cur = conn.cursor()
        user_id=session["user_id"]

        #existing service

        cur.execute("select service_id,service_name,price_per_day from service where service_name=%s",(service_name,))
        service=cur.fetchone()
        
        
        #insert service
        if not service:
            cur.execute("insert into service (service_name,price_per_day) values (%s,%s)",(service_name,price_per_day))
            cur.execute("select service_id,service_name,price_per_day from service where service_name=%s",(service_name,))
            service=cur.fetchone()

       #existing service provider 
        cur.execute("select service_provider_id,service_provider_name,service_provider_number,service_provider_address,service_id from service_provider where service_provider_number=%s",(service_provider_number,))
        service_provider_details=cur.fetchone()
        
        
        #insert service provider
        if not service_provider_details:
            cur.execute("insert into service_provider(service_provider_name,service_provider_number,service_provider_address,service_id)values (%s,%s,%s,%s)",(service_provider,service_provider_number,service_provider_address,service["service_id"]))
            cur.execute("select service_provider_id,service_provider_name,service_provider_number,service_provider_address from service_provider where service_provider_number=%s",(service_provider_number,))
            service_provider_details=cur.fetchone()
           
        
        #existing susbcription

        cur.execute("select * from subscriptions where user1_id=%s and service_id=%s and service_provider_id=%s and start_date=%s and end_date=%s",(user_id,service["service_id"],service_provider_details["service_provider_id"],start_date,end_date))
        subscription=cur.fetchone()

        if subscription:
            flash("subscription already exist","error")
            return redirect (url_for("addservice"))
        

        
        cur.execute("insert into subscriptions(user1_id,service_id,service_provider_id,start_date,end_date,daily_quantity) values(%s,%s,%s,%s,%s,%s)",(user_id,service["service_id"],service_provider_details["service_provider_id"],start_date,end_date,daily_quantity))
        flash("subscription added successfully","success")
        print("Insert executed")
        
        cur.execute("""select subscriptions.uuid_id,
                    service.service_id,subscriptions.start_date,subscriptions.end_date,subscriptions.status,subscriptions.user1_id,service.service_name FROM subscriptions JOIN  service on subscriptions.service_id=service.service_id where subscriptions.user1_id=%s""",(session["user_id"],))
        
       
        subscriptions_list=cur.fetchall()

        print(subscriptions_list)
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard"))
       

    return render_template("addservice.html")



#pause service logic
@app.route("/toggle/Pause/<id>")
def pause_service(id):
    conn = get_connection()
    cur = conn.cursor()

    #update status in database 
    cur.execute("""update subscriptions
                set status="paused"
                where uuid_id=UUID_TO_BIN(%s)""",(id,))
    flash("service paused succesfully")
    
    cur.execute("insert into pause_history(pause_start_date,subscription_id) values(CURDATE(),UUID_TO_BIN(%s))",(id,))
    
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))
    



#resume service logic
@app.route("/toggle/Resume/<id>")
def resume(id):
    conn = get_connection()
    cur = conn.cursor()

    #resume status in database 
    cur.execute("""update subscriptions
                set status="active"
                where uuid_id=UUID_TO_BIN(%s)""",(id,))
    flash("service resumed succesfully")
    

    cur.execute("""
    UPDATE pause_history 
    SET pause_end_date = CURDATE(),
        pause_days = GREATEST(DATEDIFF(CURDATE(), pause_start_date), 0)
    WHERE subscription_id =UUID_TO_BIN(%s)
    AND pause_end_date IS NULL
""", (id,))
                
    # pause_days=cur.fetchone()
    # print(pause_days)
        
     
    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

@app.route("/delete/<id>")
def delete_service(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("select service_id,service_provider_id from subscriptions where uuid_id= UUID_TO_BIN(%s)",(id,))
    service_details=cur.fetchone()
    print(service_details)
    
    conn.close()
 
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("delete from billing where subscription_id=UUID_TO_BIN(%s)",(id,))
    cur.execute("delete from pause_history where subscription_id=UUID_TO_BIN(%s)",(id,))     
    cur.execute(" delete from subscriptions where uuid_id=UUID_TO_BIN(%s)",(id,))
    
    flash("delete subscription successfully")
    conn.commit()
    conn.close()
    print("service id that we have to delete ",service_details)
    
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("select * from subscriptions where service_id=%s",(service_details["service_id"],))
    exist_subs_dlt_service=cur.fetchone()
    
    if not exist_subs_dlt_service:

        cur.execute("delete from service_provider where service_id=%s",(service_details["service_id"],))
        cur.execute("delete from service where service_id=%s",(service_details["service_id"],))
        
    



    conn.commit()
    conn.close()
    return redirect(url_for("dashboard"))

#pause_details _page

@app.route('/pause_details/<id>')
def pause_details(id):
    conn = get_connection()
    cur = conn.cursor()

    #Get subscription
    cur.execute("""SELECT 
                   service.service_name,
                   subscriptions.uuid_id,
                   subscriptions.start_date,
                   subscriptions.end_date ,
                   subscriptions.status
                   From Subscriptions JOIN SERVICE
                    on Subscriptions.service_id=SERVICE.service_id
                where subscriptions.uuid_id=UUID_TO_BIN(%s)""",(id,))
    subs= cur.fetchone()
    
    print(subs)
    
    #  2.pause history
    cur.execute("""
        SELECT pause_start_date, pause_end_date, pause_days
        FROM pause_history
        WHERE subscription_id=UUID_TO_BIN(%s)
    """, (id,))
    pauses = cur.fetchall()
    print(pauses)
    #check if ongoing pause
    is_Paused=False
    ongoing_days=0

    for p in pauses:
        if p["pause_end_date"] is None:
            is_Paused = True
            ongoing_days = (datetime.today().date() - p["pause_start_date"]).days 
    



    #total_pause_days_calculation


    cur.execute("select sum(pause_days) as total_pause_days from pause_history where subscription_id=%s",(id,))
    t_p_d=cur.fetchone()
    
    total_pause_days = int(t_p_d["total_pause_days"] or 0) + ongoing_days

         
    print("total paused days of service is :",total_pause_days)

    orignal_end_date=subs["end_date"]
    


    #exetnded_end_days_logic
    if  is_Paused:
        extended_end_date = "Will update after resume" 
    else:
        extended_end_date=orignal_end_date+timedelta(days=total_pause_days)
    print("extended end date is :",extended_end_date)
    
    conn.close()
    
    return render_template(
        'pause_details.html',
        subs=subs,
        pauses=pauses,
        total_pause_days=total_pause_days,
        extended_end_date=extended_end_date,
        is_Paused=is_Paused

    )


@app.route('/generate_bill/<id>')
def generate_bill(id):
    conn = get_connection()
    cur = conn.cursor() 

    # subscription + price
    cur.execute("""
    SELECT s.start_date, s.end_date, s.daily_quantity, s.user1_id,
           srv.price_per_day, srv.service_name,
           sp.service_provider_name,
           sp.service_provider_number
    FROM subscriptions s
    JOIN service srv ON s.service_id = srv.service_id
    JOIN service_provider sp ON s.service_provider_id = sp.service_provider_id
    WHERE s.uuid_id = UUID_TO_BIN(%s)
""", (id,))
    
    sub = cur.fetchone()

    if not sub:
        flash("Subscription not found", "error")
        return redirect(url_for("dashboard"))

    today = datetime.today().date()

    #  Check if service completed
    if today < sub["end_date"]:
        flash("Service is still in progress", "error")
        return redirect(url_for("dashboard"))

    
        
    cur.execute("SELECT * FROM billing WHERE subscription_id=UUID_TO_BIN(%s)", (id,))
    existing_bill = cur.fetchone()
    #  Calculate pause days
    cur.execute("""
        SELECT SUM(pause_days) as total_pause_days
        FROM pause_history
        WHERE subscription_id=%s
    """, (id,))
    
    pause = cur.fetchone()
    total_pause_days = pause["total_pause_days"] or 0

    # Calculate total days
    total_days = (sub["end_date"] - sub["start_date"]).days+1

    # Active days
    active_days = total_days - total_pause_days

    #  Final bill
    total_amount = active_days * sub["price_per_day"] * sub["daily_quantity"]

    #  Insert into billing table
    #   if bill already exists
    
    if existing_bill:
        cur.execute("""
        UPDATE billing
        SET total_amount=%s, bill_date=CURDATE()
        WHERE subscription_id=UUID_TO_BIN(%s)
    """, (total_amount, id))
    else:
         cur.execute("""
        INSERT INTO billing (subscription_id, total_amount, created_at, user1_id, bill_date, bill_status)
        VALUES (UUID_TO_BIN(%s), %s, NOW(), %s, CURDATE(), %s)
    """, (id, total_amount, sub["user1_id"], "unpaid"))


        
        

    
    conn.commit()
    conn.close()

    return render_template(
    "bill.html",
    service_name=sub["service_name"],
    provider_name=sub["service_provider_name"],   # added
    provider_number=sub["service_provider_number"], #
    start_date=sub["start_date"],
    end_date=sub["end_date"],
    total_days=total_days,
    pause_days=total_pause_days,
    active_days=active_days,
    price=sub["price_per_day"],
    quantity=sub["daily_quantity"],
    total_amount=total_amount,
    status="unpaid"
)

#payment status
@app.route("/toggle/paid/<id>")
def to_paid(id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM billing WHERE subscription_id=UUID_TO_BIN(%s)", (id,))
    bill = cur.fetchone()

    if not bill:
        flash("Generate bill first!", "error")
        return redirect(url_for("dashboard"))

    #update status to paid 
    cur.execute("Update Billing set bill_status='unpaid' where subscription_id=UUID_TO_BIN(%s)",(id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for("dashboard"))
    

@app.route("/toggle/unpaid/<id>")
def to_unpaid(id):
    conn = get_connection()
    cur = conn.cursor()
    #update status to paid 

    cur.execute("SELECT * FROM billing WHERE subscription_id=UUID_TO_BIN(%s)", (id,))
    bill = cur.fetchone()

    if not bill:
        flash("Generate bill first!", "error")
        return redirect(url_for("dashboard"))

    cur.execute("Update Billing set bill_status='Paid' where subscription_id=UUID_TO_BIN(%s)",(id,))
    flash("paid bill")
    conn.commit()
    conn.close()
    
    return redirect(url_for("dashboard"))



@app.route("/toggle/not_present/<id>")
def no_bill(id):
    flash("No bill is generated ")
    return redirect(url_for("dashboard"))


    
@app.route('/about')
def about():
    return render_template('about.html')

@app.route("/editservice/<id>", methods=["GET", "POST"])
def edit_service(id):
    conn = get_connection()
    cur = conn.cursor()

    
    cur.execute("""
        SELECT s.start_date, s.end_date, s.daily_quantity,
               sp.service_provider_name, sp.service_provider_number, sp.service_provider_address,
               srv.service_name, srv.price_per_day
        FROM subscriptions s
        JOIN service srv ON s.service_id = srv.service_id
        JOIN service_provider sp ON s.service_provider_id = sp.service_provider_id
        WHERE s.uuid_id = UUID_TO_BIN(%s)
    """, (id,))
    
    service = cur.fetchone()
    print(service)

    
    if request.method == "POST":
        service_name=request.form["service_name"]
        service_provider=request.form["provider"]
        service_provider_number=request.form["number"]
        service_provider_address=request.form["address"]
        price_per_day=request.form["price"]
        daily_quantity=request.form["quantity"]
        start_date=request.form["start"]
        end_date=request.form["end"]
        #empty
        if not service_name or not service_provider  or not service_provider_number or not service_provider_address or not price_per_day or not daily_quantity or not start_date or not end_date:
            flash("All fields are required","error")
            return redirect(url_for("addservice"))

        if not service_name or not service_provider  or not service_provider_number or not service_provider_address or not price_per_day or not daily_quantity or not start_date or not end_date:
            flash("All fields are required","error")
            return redirect(url_for("addservice"))
        #regex
        service_name_pattern = r"^[A-Za-z ]{3,}$"
        provider_pattern = r"^[A-Za-z ]+$"
        phone_pattern = r'^(?!.*(\d)(?:.*\1){5})[6-9]\d{9}$'
        address_pattern = r"^[A-Za-z0-9\s,.-]{5,}$"
        price_pattern = r"^\d+(\.\d{1,2})?$"
        quantity_pattern = r"^[1-9]\d"
        
        

        if not re.match(service_name_pattern,service_name):
            flash("invalid name format","error")
            return redirect(url_for("addservice"))
        
        if not re.match(provider_pattern,service_provider):
            flash("invalid provider name","error")
            return redirect(url_for("addservice"))
        
        if not re.match(phone_pattern,service_provider_number):
            flash("invalid phone number format")
            return redirect(url_for("addservice"))
        
        if not re.match(address_pattern,service_provider_address):
            flash("invalid address pattern")
            return redirect(url_for("addservice"))
        
        

        price_per_day = price_per_day.strip()
        print(repr(price_per_day))  # debug

        if not re.fullmatch(price_pattern, price_per_day):
            flash("invalid price pattern")
            return redirect(url_for("addservice"))
                
        daily_quantity = daily_quantity.strip()

        if not re.fullmatch(r"^[1-9]\d*$", daily_quantity):
            flash("invalid quantity pattern")
            return redirect(url_for("addservice")) 
                
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

        if start_date_obj > end_date_obj:
            flash("Start date cannot be greater than end date", "error")
            return redirect(url_for("addservice"))
        
        
        cur.execute("""
            UPDATE service 
            SET service_name=%s, price_per_day=%s
            WHERE service_id = (
                SELECT service_id FROM subscriptions WHERE uuid_id=UUID_TO_BIN(%s)
            )
        """, (service_name, price_per_day, id))

        
        cur.execute("""
            UPDATE service_provider 
            SET service_provider_name=%s,
                service_provider_number=%s,
                service_provider_address=%s
            WHERE service_provider_id = (
                SELECT service_provider_id FROM subscriptions WHERE uuid_id=UUID_TO_BIN(%s)
            )
        """, (service_provider, service_provider_number, service_provider_address, id))

       
        cur.execute("""
            UPDATE subscriptions
            SET start_date=%s, end_date=%s, daily_quantity=%s
            WHERE uuid_id=UUID_TO_BIN(%s)
        """, (start_date, end_date, daily_quantity, id))

        conn.commit()
        conn.close()

        flash("Service updated successfully!", "success")
        return redirect(url_for("dashboard"))

    conn.close()
    return render_template("edit_service.html", service=service)

    
    






if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000,debug=True)

   