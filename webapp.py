from flask import Flask, redirect, url_for, session, request, jsonify
from flask_oauthlib.client import OAuth
#from flask_oauthlib.contrib.apps import github #import to make requests to GitHub's OAuth
from flask import render_template
from flask import flash
import pymongo
from bson.objectid import ObjectId
import pprint
import os
from dateutil.parser import *

# This code originally from https://github.com/lepture/flask-oauthlib/blob/master/example/github.py
# Edited by P. Conrad for SPIS 2016 to add getting Client Id and Secret from
# environment variables, so that this will work on Heroku.
# Edited by S. Adams for Designing Software for the Web to add comments and remove flash messaging

app = Flask( __name__ )

app.debug = True  #Change this to False for production
os.environ[ 'OAUTHLIB_INSECURE_TRANSPORT' ] = '1'  #Remove once done debugging

app.secret_key = os.environ[ 'APP_SECRET_KEY' ]  #used to sign session cookies
oauth = OAuth( app )
oauth.init_app( app )  #initialize the app to be able to make requests for user information

#Set up GitHub as OAuth provider
github = oauth.remote_app(
    'github',
    consumer_key = os.environ[ 'GITHUB_CLIENT_ID' ],  #your web app's "username" for github's OAuth
    consumer_secret = os.environ[ 'GITHUB_CLIENT_SECRET' ],  #your web app's "password" for github's OAuth
    request_token_params = { 'scope': 'user:email' },  #request read-only access to the user's email.  For a list of possible scopes, see developer.github.com/apps/building-oauth-apps/scopes-for-oauth-apps
    base_url = 'https://api.github.com/',
    request_token_url = None,
    access_token_method = 'POST',
    access_token_url = 'https://github.com/login/oauth/access_token',
    authorize_url = 'https://github.com/login/oauth/authorize'  #URL for github's OAuth login
)

# MongoDB
connection_string = os.environ[ "MONGO_CONNECTION_STRING" ]
db_name = os.environ[ "MONGO_DBNAME" ]
client = pymongo.MongoClient( connection_string )
db = client[ db_name ]
collection = db[ 'Posts' ]


#context processors run before templates are rendered and add variable(s) to the template's context
#context processors must return a dictionary
#this context processor adds the variable logged_in to the conext for all templates
@app.context_processor
def inject_logged_in():
    return { "logged_in": ( 'github_token' in session ) }


#redirect to GitHub's OAuth page and confirm callback URL
@app.route( '/login' )
def login():
    return github.authorize( callback = url_for( 'authorized', _external = True, _scheme = 'http' ) )  #callback URL must match the pre-configured callback URL


@app.route( '/logout' )
def logout():
    session.clear()
    flash( 'You were logged out.' )
    return redirect( '/' )


@app.route( '/login/authorized' )
def authorized():
    resp = github.authorized_response()
    if resp is None:
        session.clear()
        flash( 'Access denied: reason=' + request.args[ 'error' ] + ' error=' + request.args[ 'error_description' ] + ' full=' + pprint.pformat( request.args ), 'error' )
    else:
        try:
            session[ 'github_token' ] = ( resp[ 'access_token' ], '' )  #save the token to prove that the user logged in
            session[ 'user_data' ] = github.get( 'user' ).data
            #pprint.pprint(vars(github['/email']))
            #pprint.pprint(vars(github['api/2/accounts/profile/']))
            flash( f"You were successfully logged in as { session[ 'user_data' ][ 'login' ] }." )
        except Exception as inst:
            session.clear()
            print( inst )
            flash( 'Unable to login, please try again.', 'error' )
    return redirect( '/' )


@app.route( '/' )
def home():
    # Home will list all the Topics
    return render_template( 'home.html', collection = collection.find() )


@app.route( '/displaytopic' )
def displayTopic():
    args = request.args
    id = args.get( 'id' )
    topic = collection.find_one( { '_id': ObjectId( id ) } )
    return render_template( 'topic.html', topic = topic )


@app.route( '/addtopic', methods = [ 'POST', 'GET' ] )
def addTopic():
    if request.method == 'POST':
        return redirect( url_for('home') )

    action = 'add'
    title = 'Add Topic'
    return render_template( 'topic_form.html', action = action, title = title )


@app.route( '/edittopic', methods = [ 'POST', 'GET' ] )
def editTopic():
    action = 'edit'
    title = 'Edit Topic'
    return render_template( 'topic_form.html', action = action, title = title )


@app.route( '/deletetopic', methods = [ 'POST', 'GET' ] )
def deleteTopic():
    action = 'delete'
    title = 'Delete Topic'
    return render_template( 'topic_form.html', action = action, title = title )


@app.route( '/addpost' )
def addPost():
    action = 'add'
    return render_template( 'post_form.html', action = action )


@app.route( '/replypost' )
def replyPost():
    action = 'reply'
    return render_template( 'post_form.html', action = action )


@app.route( '/editpost' )
def editPost():
    action = 'edit'
    return render_template( 'post_form.html', action = action )


@app.route( '/deletepost' )
def deletePost():
    action = 'delete'
    return render_template( 'post_form.html', action = action )


#the tokengetter is automatically called to check who is logged in.
@github.tokengetter
def get_github_oauth_token():
    return session[ 'github_token' ]


# found this on StackExchange
@app.template_filter( 'strftime' )
def filter_datetime( date, fmt = None ):
    date = parse( date )
    format = '%Y-%m-%d %I:%M:%S %p'
    return date.strftime( format )


if __name__ == '__main__':
    app.run()
