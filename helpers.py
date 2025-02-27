import cv2, datetime, os, time
import flask

from flask import redirect
from functools import wraps
from numpy import diff
from werkzeug.security import check_password_hash, generate_password_hash
from yolo.yolo import yolo_run


def gen_frames(camera, activate_ai, net):
    """
    produce frames for web page using the currently selected camera
    for ip camera use - rtsp://username:password@ip_address:554/user=username_password='password'_channel=channel_number_stream=0.sdp' for local webcam use cv2.VideoCapture(0)
    """
    old_photo_time = 0
    while True:
        success, frame = camera.read()  # read the camera frame
        if not success:
            print("error with camera feed, no frame detected")
            break
        else:
            if activate_ai:
                frame, bird, photo_time = yolo_run(frame, net)
                if bird:
                    diff = photo_time - old_photo_time
                    if diff >= 5:
                        old_photo_time = photo_time
                        capture_image(camera, activate_ai)

            ret, buffer = cv2.imencode(".jpg", frame)
            frame = buffer.tobytes()
            yield (
                b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )  # concat frame one by one and show result


def capture_image(camera, activate_ai):
    """
    capture an image of the what the current camera is viewing
    """
    success, img = camera.read()
    if not success:
        return "error"
    else:
        now = datetime.datetime.now()
        now = now.strftime("%Y-%m-%d-%H-%M-%S")
        if activate_ai:
            now = now + "AI"
        image_name = now + ".png"
        image_path = os.path.join("./images/", image_name)
        cv2.imwrite(image_path, img)
        print(f"image successfully saved to {image_path}, activate_at={activate_ai}")
        return f"image saved to {image_path}"


def list_cameras():
    """
    Test the ports and returns a tuple with the available ports and the ones that are working.
    """
    non_working_ports = []
    dev_port = 0
    working_ports = []
    available_ports = 0
    while (
        len(non_working_ports) < 6
    ):  # if there are more than 5 non working ports stop the testing.
        camera = cv2.VideoCapture(dev_port)
        if not camera.isOpened():
            non_working_ports.append(dev_port)
            print("Port %s is not working." % dev_port)
        else:
            is_reading, img = camera.read()
            w = camera.get(3)
            h = camera.get(4)
            if is_reading:
                print(
                    "Port %s is working and reads images (%s x %s)" % (dev_port, h, w)
                )
                working_ports.append(dev_port)
                available_ports += 1
            else:
                print(
                    "Port %s for camera ( %s x %s) is present but does not reads."
                    % (dev_port, h, w)
                )
        dev_port += 1
    camera.release()
    return available_ports, working_ports, non_working_ports


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if flask.session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


# SQL and SQLAlchemy code
from sqlalchemy import Integer, create_engine, insert, String, Column, select, update
from sqlalchemy.orm import Session, declarative_base


def establish_ORM():
    Base = declarative_base()

    class User(Base):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True)
        user_name = Column(String(30), nullable=False, unique=True)
        hash = Column(String(), nullable=False, unique=True)

        def __repr__(self) -> str:
            return f"users(id={self.id!r}, user_name={self.user_name!r}, hash={self.hash!r})"

    engine = create_engine("sqlite:///bird.db", echo=True)
    Base.metadata.create_all(engine)
    return engine, User


def setup_db():
    if not os.path.isfile("./bird.db"):
        create_db = True
    else:
        create_db = False

    engine, User = establish_ORM()

    if create_db:
        print("User database not found, creating new database")
        with Session(engine) as session:
            sushi = User(
                user_name="sushi",
                hash="pbkdf2:sha256:600000$hXyEIMeIonIa0zMW$bfd20ef7a6673179e0a62bb94e6d383b686da5221069023a47c01245538629ac",
            )
            session.add_all([sushi])
            session.commit()
            print(
                "database has been created, please ensure the default password is changed imediately"
            )
    else:
        print("User database has been found, database ready")


def check_deets_byname(qusername, qpassword):
    engine, User = establish_ORM()
    stmt = select(User).where(User.user_name == qusername)
    with Session(engine) as session:
        user = session.execute(stmt).fetchone()[0]
    if user == None:
        return "error"
    correct = check_password_hash(user.hash, qpassword)
    if correct:
        return user
    else:
        return "error"


def check_deets_byid(qid, qpassword):
    engine, User = establish_ORM()
    stmt = select(User).where(User.id == qid)
    with Session(engine) as session:
        user = session.execute(stmt).fetchone()[0]
        if user == None:
            return "Error: user not found"
        correct = check_password_hash(user.hash, qpassword)
        print(f"user.hash: {user.hash}")
        if correct:
            return user
        else:
            return "Error: password incorrect"


def new_pass(userid, newpassword):
    """
    save a new password to the bird.db database.
    """
    engine, User = establish_ORM()
    newhash = generate_password_hash(newpassword)
    with Session(engine) as session:
        stmt = select(User).where(User.id == userid)
        selected_user = session.scalars(stmt).one()
        selected_user.hash = newhash
        session.commit()
    return "Password changed successfully"
