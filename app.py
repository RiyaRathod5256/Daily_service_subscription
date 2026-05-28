# Corrected app.py (Syntax Errors + Table Case Mismatch + Clean Imports/Routes)


from flask import Flask, render_template, request, flash, redirect, url_for, session
from db import get_connection
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import timedelta, datetime

app = Flask(__name__)
app.secret_key = "123456"


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form['username']
        email = request.form['email'].lower()
        password = request.form['password']
        phone = request.form['phone']

        if not name or not email or not password or not phone:
            flash("All fields are required", "empty")
            return redirect(url_for("register"))

        username_pattern = r'^[a-zA-Z_][a-zA-Z0-9_.@#$%^&*!-]{2,60}$'

        if not re.match(username_pattern, name):
            flash("Invalid username format", "error")
            return redirect(url_for("register"))

        if len(name) < 3:
            flash("Username is too short", "error")
            return redirect(url_for("register"))

        if len(name) > 60:
            flash("Username is too long", "error")
            return redirect(url_for("register"))

        if re.search(r'(.)\\1{4,}', name):
            flash("Username cannot have too many repeated characters", "error")
            return redirect(url_for("register"))

        email_pattern = r'^[A-Za-z][A-Za-z0-9._%+-]*@[A-Za-z0-9]+([.-][A-Za-z0-9]+)*\\.[A-Za-z]{2,}$'

        if not re.fullmatch(email_pattern, email):
            flash("Invalid email format", "error")
            return redirect(url_for("register"))

        phone_pattern = r'^(?!.*(\\d)(?:.*\\1){5})[6-9]\\d{9}$'

        if not re.match(phone_pattern, phone):
            flash("Invalid phone number", "error")
            return redirect(url_for("register"))

        password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]{8,15}$'

        if not re.match(password_pattern, password):
            flash("Weak password", "error")
            return redirect(url_for("register"))

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM user1 WHERE useremail=%s", (email,))
        user = cur.fetchone()

        if user:
            flash("User already registered", "error")
            conn.close()
            return redirect(url_for("register"))

        cur.execute("SELECT * FROM user1 WHERE userphonenumber=%s", (phone,))
        phone_user = cur.fetchone()

        if phone_user:
            flash("Phone number already registered", "error")
            conn.close()
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        cur.execute(
            "INSERT INTO user1(username, useremail, userpassword, userphonenumber) VALUES(%s,%s,%s,%s)",
            (name, email, hashed_password, phone)
        )

        conn.commit()
        conn.close()

        flash("Registration successful", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT user1_id, username, useremail, userpassword FROM user1 WHERE useremail=%s",
            (email,)
        )

        user = cur.fetchone()

        if user and check_password_hash(user["userpassword"], password):
            session["user_id"] = user["user1_id"]
            session["user_email"] = user["useremail"]
            session["user_name"] = user["username"]
            session["loggedin"] = True

            flash("Login successful", "success")
            conn.close()
            return redirect(url_for("dashboard"))

        flash("Invalid email or password", "error")
        conn.close()

    return render_template("login.html")


@app.route("/dashboard")
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
            billing.bill_status
        FROM subscriptions
        JOIN service
            ON subscriptions.service_id = service.service_id
        LEFT JOIN billing
            ON subscriptions.uuid_id = billing.subscription_id
        WHERE subscriptions.user1_id = %s
    """, (session["user_id"],))

    subscriptions_list = cur.fetchall()

    active = 0
    paused = 0
    due = 0

    for sub in subscriptions_list:
        if sub["status"] == "active":
            active += 1
        elif sub["status"] == "paused":
            paused += 1

        if sub["bill_status"] in ["unpaid", "Unpaid"]:
            due += 1

    total = active + paused

    conn.close()

    return render_template(
        "dashboard.html",
        subscriptions=subscriptions_list,
        active=active,
        paused=paused,
        due=due,
        total=total
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for("login"))


@app.route("/toggle/pause/<id>")
def pause_service(id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE subscriptions SET status='paused' WHERE uuid_id=UUID_TO_BIN(%s)",
        (id,)
    )

    cur.execute(
        "INSERT INTO pause_history(pause_start_date, subscription_id) VALUES(CURDATE(), UUID_TO_BIN(%s))",
        (id,)
    )

    conn.commit()
    conn.close()

    flash("Service paused successfully", "success")
    return redirect(url_for("dashboard"))


@app.route("/toggle/resume/<id>")
def resume(id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE subscriptions SET status='active' WHERE uuid_id=UUID_TO_BIN(%s)",
        (id,)
    )

    cur.execute("""
        UPDATE pause_history
        SET pause_end_date = CURDATE(),
            pause_days = GREATEST(DATEDIFF(CURDATE(), pause_start_date), 0)
        WHERE subscription_id = UUID_TO_BIN(%s)
        AND pause_end_date IS NULL
    """, (id,))

    conn.commit()
    conn.close()

    flash("Service resumed successfully", "success")
    return redirect(url_for("dashboard"))


@app.route("/delete/<id>")
def delete_service(id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM billing WHERE subscription_id=UUID_TO_BIN(%s)",
        (id,)
    )

    cur.execute(
        "DELETE FROM pause_history WHERE subscription_id=UUID_TO_BIN(%s)",
        (id,)
    )

    cur.execute(
        "DELETE FROM subscriptions WHERE uuid_id=UUID_TO_BIN(%s)",
        (id,)
    )

    conn.commit()
    conn.close()

    flash("Subscription deleted successfully", "success")
    return redirect(url_for("dashboard"))


@app.route('/pause_details/<id>')
def pause_details(id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            service.service_name,
            subscriptions.uuid_id,
            subscriptions.start_date,
            subscriptions.end_date,
            subscriptions.status
        FROM subscriptions
        JOIN service
            ON subscriptions.service_id = service.service_id
        WHERE subscriptions.uuid_id = UUID_TO_BIN(%s)
    """, (id,))

    subs = cur.fetchone()

    cur.execute("""
        SELECT pause_start_date, pause_end_date, pause_days
        FROM pause_history
        WHERE subscription_id = UUID_TO_BIN(%s)
    """, (id,))

    pauses = cur.fetchall()

    is_paused = False
    ongoing_days = 0

    for p in pauses:
        if p["pause_end_date"] is None:
            is_paused = True
            ongoing_days = (datetime.today().date() - p["pause_start_date"]).days

    cur.execute(
        "SELECT SUM(pause_days) AS total_pause_days FROM pause_history WHERE subscription_id=UUID_TO_BIN(%s)",
        (id,)
    )

    t_p_d = cur.fetchone()

    total_pause_days = int(t_p_d["total_pause_days"] or 0) + ongoing_days

    original_end_date = subs["end_date"]

    if is_paused:
        extended_end_date = "Will update after resume"
    else:
        extended_end_date = original_end_date + timedelta(days=total_pause_days)

    conn.close()

    return render_template(
        'pause_details.html',
        subs=subs,
        pauses=pauses,
        total_pause_days=total_pause_days,
        extended_end_date=extended_end_date,
        is_paused=is_paused
    )


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)
