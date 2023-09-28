#Import necessary libraries
import os, sys
import helpers

from helpers import login_required
from logging import debug
from flask import Flask, redirect, render_template, Response, request, session
from flask_session import Session
from werkzeug.security import check_password_hash 

#Initialize the Flask app
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# user database setup
helpers.setup_db()

# detecting available_cameras and selecting the first one
available_camera_count, available_cameras, _ = helpers.list_cameras()
print(f"Cameras available: {available_camera_count}")
print(f"list of cameras available by number: {available_cameras}")
running_camera = available_cameras[0]


@app.route("/")
@login_required
def index():
    id = session.get("user_id")
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        quser_name = request.form.get("username")
        qpassword =  request.form.get("password")

        user = helpers.check_deets_byname(quser_name, qpassword)

        if user == None:
            error = "Username not on record"
            return render_template("login.html", error=error)

        if user == "error":
            error = "Username and/or Password incorrect"
            return render_template("login.html", error=error)


        session["user_id"] = user.id
        print(session["user_id"])
        return redirect("/")

    else: # if GET method
        return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/camera_view")
@login_required
def camera_view():
    return render_template("camera.html", camera_number=running_camera)


@app.route("/video")
@login_required
def video_feed():
    return Response(helpers.gen_frames(running_camera), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/capture", methods=["POST"])
@login_required
def capture():
    message = helpers.capture_image(running_camera)
    return render_template("camera.html", camera_number=running_camera, message=message)


@app.route("/settings")
@login_required
def settings():
    global available_camera_count, available_cameras
    available_camera_count, available_cameras, _ = helpers.list_cameras()
    return render_template("settings.html", camera_list=available_cameras, current_camera=running_camera)


@app.route("/change_password", methods=["POST"])
@login_required
def change_password():
    qpassword = request.form.get("qpassword")
    npassword = request.form.get("npassword") 
    confirm = request.form.get("confirm") 
    qid = session.get("user_id")

    user = helpers.check_deets_byid(qid, qpassword)
    if user == "error":
        message = user
    elif confirm != npassword:
        message = "new password does not match the confirmation password"
    else:
        message = helpers.new_pass(qid, npassword)
    return render_template("settings.html", camera_list=available_cameras, current_camera=running_camera, message=message)


@app.route("/change_camera", methods=["POST"])
@login_required
def change_camera():
    new_cam = request.form['cam_button']
    global running_camera 
    running_camera = int(new_cam)
    message = f"Camera {running_camera} has now been selected"
    return render_template("settings.html", camera_list=available_cameras, current_camera=running_camera, message=message)


if __name__ == "__main__":
    app.run(use_reloader=True)