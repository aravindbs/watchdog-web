from app import app
from flask import render_template, redirect, flash, url_for, request, make_response
from flask_login import login_required, login_user, logout_user, current_user
from .forms import *
from app import db, images
from .models import *
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from createGroup import createGroup
from faceapi import addFace, addPerson, createGroup, trainFaces, deletePerson
#from .camera import *
from azure.storage.blob import BlockBlobService , ContentSettings
import json
import httplib, urllib, base64, yaml
import re

with open("config.yaml", "r") as f:
    config = yaml.load(f)

block_blob_service = BlockBlobService(account_name = config['azure-blob']['account_name'], account_key= config['azure-blob']['account_key'])


@app.route('/', methods = ['GET', 'POST'])
def homepage():
  return render_template('index.html', title = 'Home')

@app.route('/index')
def index():
    return render_template('index.html', title = 'Home')

@app.route('/signup', methods=['GET','POST'])
def signup():
    form = SignUpForm()
    if form.validate_on_submit():
        user = Users(email=form.email.data, username=form.username.data, password=form.password.data)
        code = createGroup (form.username.data, form.email.data, form.username.data)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash('Registration Successful! You may now create your profile.' , 'success')
        return redirect(url_for('editProfile'))
    return render_template('signup.html', title='Sign Up', form = form)

@app.route('/login' , methods = ['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('cameraDetails'))

    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email = form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user)

            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login.html', title='Sign In', form = form)

@app.route('/editProfile', methods=['GET', 'POST'])
@login_required
def editProfile():
    profile = Profile.query.filter_by(username = current_user.username).first()
    if profile is None:
        form = EditProfileForm()
        if form.validate_on_submit():
            profile = Profile(username = current_user.username, first_name = form.first_name.data, last_name = form.last_name.data)
            db.session.add(profile)
            db.session.commit()
            return redirect(url_for('cameraDetails'))
    else:
        form = EditProfileForm(obj=profile)
        form.populate_obj(profile)
        if form.validate_on_submit():
            profile = Profile(username = current_user.username, first_name = form.first_name, last_name = form.last_name)
            db.session.commit()
            return redirect(url_for('cameraDetails'))
    return render_template('editProfile.html', title='Edit Profile', form = form)


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    profile = Profile.query.filter_by(username = current_user.username).first()
    form = DateForm()
    
    if form.validate_on_submit():
        date = form.date.data
        return redirect(url_for('chart' , date = date))
    return render_template('dashboard.html' ,  profile = profile , form = form )

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have logged out.' , 'success')
    return redirect(url_for('login' ))

@app.route('/cameraDetails' , methods = ['GET' , 'POST'])
@login_required
def cameraDetails():
    #camcount=1
    camera = Camera.query.filter_by(username = current_user.username).all()
    camcount=len(camera)
    if request.method == 'POST':
        if request.form['submit'] == 'submit':
            detailsList = request.form.getlist('add-more[]')
            print detailsList
            CameraNoList = detailsList[0::2]
            CameraDescList = detailsList[1::2]
            length = len(CameraNoList)
            camcount=length+2
            for i in range(0,length):
                existing_camera = Camera.query.filter_by(cno=CameraNoList[i]).first()
                if existing_camera is None:
                    camera = Camera(username = current_user.username , cno = CameraNoList[i] , cdesc = CameraDescList[i])
                    db.session.add(camera)
                    db.session.commit()
                else: 
                    existing_camera.cdesc = CameraDescList[i]
                    db.session.commit()
            return redirect(url_for('watchlist'))
    return render_template('test2.html' , camera=camera, camcount=camcount )


@app.route('/unAuth<date>' , methods = ['GET' , 'POST'])
@login_required
def unAuth(date):

    pics = UnauthImageGallery.query.filter(UnauthImageGallery.timestamp.contains(date)).filter_by( username = current_user.username).all()
    print pics 

    if not pics: 
        print "yes"
        flash('No Security Breaches for selected date' , 'danger')
        return redirect(url_for('dashboard'))
    
    for pic in pics: 
        pic.timestamp = pic.timestamp[:16]
    return render_template('Unauth.html', pics = pics)

@app.route('/train' , methods = ['GET' , 'POST'])
@login_required
def train():
    return 'Hello World'


@app.route('/uploadImages', methods=['GET', 'POST'])
@login_required
def uploadImages():
    count = 0
   
    #x = db.session.query(Persons.person_name,Persons.person_id,AuthImageGallery.image_path).filter(Persons.person_id == AuthImageGallery.person_id, Persons.username == current_user.username).all()
    people = Persons.query.filter_by(username = current_user.username).all()
    peopleDict = {}
    for ppl in people: 
        photo = AuthImageGallery.query.filter_by(person_id = ppl.person_id).first()
        peopleDict[ppl] = photo
    """
    form = AddPersonForm()
    
    if form.submit.data: #adding another person
        code = addPerson ( current_user.username, form.name.data, form.name.data)
        add_person = Persons(person_name = form.name.data, username = current_user.username, azure_id = code["personId"])
        db.session.add(add_person)
        db.session.commit()
        return redirect(url_for('addPics' , user = add_person.person_id))
    """
    return render_template('Auth.html' , peopleDict = peopleDict)

@app.route('/addPeople', methods=['GET', 'POST'])
@login_required
def addPeople():
    
    form = AddPersonForm()

    locations = Camera.query.filter_by(username = current_user.username)

    if form.validate_on_submit(): 
        print request.form.getlist("ingredients[]")
        code = addPerson ( current_user.username, form.name.data, form.name.data)
        print "hey" 
        print code 
        add_person = Persons(person_name = form.name.data, username = current_user.username, azure_id = code["personId"])
        db.session.add(add_person)
        db.session.commit()
        add_person = Persons.query.filter_by(person_name = form.name.data).first()
        for loc in request.form.getlist("ingredients[]"):
            add_location = Location(person_id = add_person.person_id , location = loc)
            db.session.add(add_location)

        db.session.commit()
        return redirect(url_for('addPics' , user = add_person.person_id))
        
    return render_template('addPerson.html' , form = form , locations = locations)

@app.route('/TrainFaces', methods=['GET', 'POST'])
@login_required
def TrainFaces():

    faces =  db.session.query(Persons.username,AuthImageGallery.image_path, Persons.azure_id ).filter(Persons.person_id == AuthImageGallery.person_id, Persons.username == current_user.username, AuthImageGallery.training_status == 'false').all()

    for face in faces:
        addFace(str(face[0]) , str(face[2]), str(face[1]))

    code = trainFaces (current_user.username)
    if code == 202:
        flash("Successfully Trained!",'success')

        notTrained = AuthImageGallery.query.filter_by(training_status = 'false')

        for face in notTrained:
            face.training_status = 'true'
            db.session.commit()
    else :
        flash("Training Failed.",'danger')

    
    return redirect(url_for('dashboard'))


@app.route('/viewPerson/<user>' , methods = ['GET' , 'POST'])
@login_required
def viewPerson(user):
  
    listPics = AuthImageGallery.query.filter_by(person_id = user).all()
    

    delPics = []
    if request.method == "POST":
        delPics = request.form.getlist('users')
   
    if delPics:
        for f in delPics:
           
            img = AuthImageGallery.query.filter_by(imgid = f).first()
           
            block_blob_service.delete_blob('video', img.image_filename)
            
            #os.remove(os.path.join(app.config['UPLOADED_IMAGES_DEST'], img.image_filename))
            db.session.delete(img)
            db.session.commit()
        flash('Deleted Successfully', 'success')
        return redirect(url_for('uploadImages'))
    return render_template('deleteImages.html' , pics = listPics, user1 = user)


@app.route('/addPics/<user>' , methods = ['GET' , 'POST'])
@login_required
def addPics(user):

    current_person = Persons.query.filter_by(person_id = user).first()

    form = EditImageGalleryForm()
   
    if form.skip.data:

        if 'image' in request.files:
            for f in request.files.getlist('image'):
                if f.filename:
                    filename = secure_filename(f.filename)
                    #path = os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename)
                    block_blob_service.create_blob_from_stream('video', filename, f)
                    #f.save(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename))
                    url = config['azure-blob']['blob_url'] + "/" + filename

                    person = Persons.query.filter_by(person_id = user).first()
                    image = AuthImageGallery(image_filename= filename, image_path= url, person_id = person.person_id, training_status = 'false' )
                    db.session.add(image)
                    db.session.commit()
            faces = db.session.query(Persons.username,AuthImageGallery.image_path, Persons.azure_id ).filter(Persons.person_id == AuthImageGallery.person_id, Persons.username == current_user.username, AuthImageGallery.training_status == 'false').all()

            for face in faces:
                addFace(str(face[0]) , str(face[2]), str(face[1]))



            code = trainFaces (current_user.username)
            if code == 202:
                resp = "Successfully Trained!"
                flash ( resp , 'success')
                notTrained = AuthImageGallery.query.filter_by(training_status = 'false')

                for face in notTrained:
                    face.training_status = 'true'
                    db.session.commit()
            else :
                resp = "Training Failed."
                flash ( resp , 'danger')
            
        return redirect(url_for('dashboard'))

    return render_template('pics.html', form = form, user=user)

@app.route('/webcam/<user>', methods=['GET', 'POST'])
@login_required
def webcam(user):
    return render_template('webcam.html', user = user)

@app.route('/getWebcamPics/<user>', methods=['POST'])
@login_required
def getWebcamPics(user):
    
    if request.method == "POST":
        ret = request.files
        for f in request.files.getlist('webcam'):
                if f.filename:
                    filename = secure_filename(f.filename)
                    time = str(datetime.now())
                    time = re.sub(r"\s+", '-', time)
                    filename = filename + time
                    #path = os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename)
                    block_blob_service.create_blob_from_stream('video', filename, f)
                    #f.save(os.path.join(app.config['UPLOADED_IMAGES_DEST'], filename))
                    url = config['azure-blob']['blob_url'] + "/" + filename

                    person = Persons.query.filter_by(person_id = user).first()
                    image = AuthImageGallery(image_filename= filename, image_path= url, person_id = person.person_id, training_status = 'false' )
                    db.session.add(image)
                    db.session.commit()
                   
@app.route('/removePeople', methods=['GET', 'POST'])
@login_required
def removePeople():     
    people = Persons.query.filter_by(username = current_user.username).all()

    delPeople = []
    if request.method == "POST":
        delPeople = request.form.getlist('users')
        print delPeople
    
    if delPeople:
        for id in delPeople:
            person = Persons.query.filter_by(person_id = id).first()
            response = deletePerson( current_user.username, person.azure_id)
            #print response
            #flash('Deleted Successfully', 'success')
            db.session.delete(person)
            db.session.commit()
        flash('Deleted Successfully', 'success')
        return redirect(url_for('uploadImages'))
    return render_template('deletePeople.html', people=people)

@app.route('/chart<date>', methods=['GET', 'POST'])
@login_required
def chart(date):

    unauth = UnauthImageGallery.query.filter(UnauthImageGallery.timestamp.contains(date)).filter_by( username = current_user.username).all()
    if not unauth: 
        flash('No Security Breaches for selected date' , 'danger')
        return redirect(url_for('dashboard'))
    hours = []
    
    for i in range (0, 24):
        hours.append(0)

    for img in unauth:
        
        hour = img.timestamp[11:13]
        hours[int(hour)]+=1  

    return render_template('chart.html' , hours = hours , date = date) 

@app.route('/unAuthDatePicker', methods=['GET', 'POST'])
@login_required
def unAuthDatePicker():
    
    form = DateForm()
    
    if form.submit2.data:
        print "submit 2"
        date = form.date.data
        return redirect(url_for('unAuthObjects' , date = date))
    elif form.submit1.data: 
        print "submit 1"
        date = form.date.data
        return redirect(url_for('unAuth' , date = date))

    return render_template('date.html' , form = form)

@app.route('/unAuthObjects<date>', methods=['GET', 'POST'])
@login_required
def unAuthObjects(date):
    
    print date 
    pics = UnauthObjects.query.filter(UnauthObjects.timestamp.contains(date)).filter_by( username = current_user.username).all()
    print pics 

    if not pics: 
        print "yes"
        flash('No Security Breaches for selected date' , 'danger')
        return redirect(url_for('dashboard'))
    
    for pic in pics: 
        pic.timestamp = pic.timestamp[:16]
    return render_template('UnAuthObjects.html', pics = pics)

@app.route('/watchlist', methods=['GET', 'POST'])
@login_required
def watchlist():
    
    if request.method == "POST":
        watchlist = request.form.getlist('watchlist')
        print str(watchlist)
        obj = Watchlist(username = current_user.username , watchlist = str(watchlist))

        db.session.add(obj)
        db.session.commit() 
        return redirect(url_for('dashboard'))
    
    return render_template('watchlist.html')
