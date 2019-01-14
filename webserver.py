from flask import (Flask, render_template, request, jsonify, make_response,
                   url_for, redirect, session as login_session, flash)
import random
import string
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from db_setup import Base, Movie, User, Category
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests

app = Flask(__name__)

engine = create_engine('sqlite:///moviecategory.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Movie Client 1"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
            'Current user is already connected.'
            ), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['name'] = data['name']
    login_session['img'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'
    if not check_user():
        createUser()
    return jsonify(name=login_session['name'],
                   email=login_session['email'],
                   img=login_session['img'])


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    print(access_token)
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['name']
        del login_session['email']
        del login_session['img']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/')
def index():
    return render_template('index.html', session=login_session)


def createUser():
    name = login_session['name']
    email = login_session['email']
    url = login_session['img']
    provider = login_session['provider']
    newUser = User(name=name, email=email, image=url, provider=provider)
    session.add(newUser)
    session.commit()


def check_user():
    session = DBSession()
    email = login_session['email']
    return session.query(Movie).filter_by(email=email).one_or_none()


@app.route('/login')
def login():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    # Disconnect based on provider
    if login_session.get('email'):
        return gdisconnect()
    else:
        response = make_response(json.dumps({'state': 'notConnected'}),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return render_template('index.html')


@app.route('/category/<category>/new', methods=['GET', 'POST'])
def newItem(category):
    session = DBSession()
    if login_session:
        if request.method == 'POST':
                newMovie = Movie(
                    title=request.form['title'],
                    director=request.form['director'],
                    category_name=category,
                    email=login_session['email']
                )
                session.add(newMovie)
                flash('Movie Added')
                session.commit()
                return redirect(url_for('newItem', category=category))
        else:
            return render_template('newMovie.html')
    else:
        return render_template('mustLogin.html')


@app.route('/category/<category>/<movie_id>/edit', methods=['GET', 'POST'])
def editItem(category, movie_id):
    session = DBSession()
    editedMovie = session.query(Movie).filter_by(id=movie_id).one()
    if login_session:
        if request.method == 'POST':
            if editedMovie.email == login_session['email']:
                if request.form['title']:
                    editedMovie.title = request.form['title']
                if request.form['director']:
                    editedMovie.director = request.form['director']

                session.add(editedMovie)
                session.commit()
                flash('Edit Successful')
                return redirect(url_for(
                    'editItem',
                    category=category,
                    movie_id=movie_id)
                )
            if editedMovie.email != login_session['email']:
                return render_template('permissions.html')
            else:
                flash('You do not have permission to do that')
                return render_template('mustLogin.html')
        else:
            return render_template('editMovie.html')
    else:
        return render_template('mustLogin.html')


@app.route('/category/<category>/<movie_id>/delete', methods=['GET', 'POST'])
def deleteItem(category, movie_id):
    session = DBSession()
    movieToDelete = session.query(Movie).filter_by(id=movie_id).one()
    if login_session:
        if request.method == 'POST':
            if movieToDelete.email == login_session['email']:
                session.delete(movieToDelete)
                session.commit()
                flash('Deleted Successfully!')
                return redirect(url_for('showCategory', category=category))
        else:
            return render_template('deleteMovie.html', item=movieToDelete)
    else:
        return render_template('mustLogin.html')


# Show a movies in category
@app.route('/category/<category>/')
def showCategory(category):
    session = DBSession()
    movies = session.query(Movie).filter_by(category_name=category).all()
    print(movies)
    header = category.capitalize()
    return render_template(
        'movies.html',
        items=movies,
        category=category,
        header=header
    )
    # 'This page is the list for movies of a specific category


# JSON APIs to view Movie Information
@app.route('/category/<category>/JSON')
def moviesByCategory(category):
    movies = session.query(Movie.category_name).filter_by(
        category_name=category
    ).all()
    return jsonify(movies=[i.serialize for i in movies])


@app.route('/category/<category>/<movie_id>/JSON')
def movieById(category, movie_id):
    movie = session.query(Movie).filter_by(category_name=category).one()
    return jsonify(movie=movie.serialize)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
