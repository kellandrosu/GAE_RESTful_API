

from google.appengine.ext import ndb
import logging
from flask import Flask, render_template, request, jsonify, json


app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG)

#use flask to handle requests. 
	#interpret request body using json

#boat entity definition
class Boat(ndb.Model):
#    id = ndb.StringProperty()
    name = ndb.StringProperty()
    type = ndb.StringProperty()
    length = ndb.FloatProperty()
    at_sea = ndb.BooleanProperty(default=True)


@app.route('/boat', methods=["POST"])
def createBoat():

	reqObj = request.get_json(force=True)

	if 'name' in reqObj and 'type' in reqObj and 'length' in reqObj:
		
		boat = Boat(
	    	name=reqObj['name'],
	    	type=reqObj['type'],
	    	length=reqObj['length']
	    	)

		if 'at_sea' in reqObj :
			boat.at_sea = reqObj['at_sea']

		#write boat to ndb
		boatkey = boat.put()

		#compile response body
		payload = {
			'id' : boat.key.urlsafe()
		}
		status_code = 200

	else:
		status_code = 400
		payload = "400 Bad Request"
	
	#prepare and send response
	resp = jsonify(payload)
	resp.status_code = status_code

	return resp

@app.route('/boat/<boatId>', methods=['GET'])
def getBoat(boatId):

	boatkey = ndb.Key(urlsafe=boatId)
	boat = boatkey.get()

	if boat != None :
		payload = {
			'name' : boat.name,
			'type' : boat.type,
			'length' : boat.length,
			'id' : boatId
		}
		status_code = 200
	else:
		status_code = 400
		payload = "Error: Could not find Boat with id " + boatId

	 #prepare and send response
	resp = jsonify(payload)
	resp.status_code = status_code
	
	return resp
	


@app.route('/form')
def form():
    return render_template('form.html')


@app.route('/submitted', methods=['POST'])
def submitted_form():
	name = request.form['name']
	email = request.form['email']
	site = request.form['site_url']
	comments = request.form['comments']

	return render_template(
		'submitted_form.html',
		name=name,
		email=email,
		site=site,
		comments=comments
		)