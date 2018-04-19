

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


#create new boat
@app.route('/boats', methods=["POST"])
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
		payload = { 'message': "400 Bad Request" }
	
	#prepare and send response
	resp = jsonify(payload)
	resp.status_code = status_code

	return resp


#get or modify boat by id
@app.route('/boats/<boatId>', methods=['GET', 'PATCH', 'DELETE'])
@app.route('/boats/<boatId>/', methods=['GET', 'PATCH', 'DELETE'])
def getBoat(boatId):

	boatkey = ndb.Key(urlsafe=boatId)
	boat = boatkey.get()

	if boat != None :	

		#handle DELETE
		if request.method == 'DELETE' :

			boatkey.delete()
			payload = ""	#empty payload

		#handle GET and PATCH
		else :
			if request.method == 'PATCH' :
				reqObj = request.get_json(force=True)
				#iterate through
				print reqObj
				if 'name' in reqObj :
					boat.name = reqObj['name']
				if 'type' in reqObj :
					boat.type = reqObj['type']
				if 'length' in reqObj:
					boat.length = reqObj['length']
				if 'at_sea' in reqObj :
					boat.at_sea = reqObj['at_sea']

				boat.put()

			payload = boatToJson(boat)
			
		status_code = 200

	else:
		status_code = 400
		payload = 'Error: Could not find Boat with id=' + boatId

	 #prepare and send response
	resp = jsonify(payload)
	resp.status_code = status_code
	
	return resp
	
#get all boats
@app.route('/boats', methods=['GET'])
@app.route('/boats/', methods=['GET'])
def getBoats():

	qry = Boat.query()

	payload = []

	for boat in qry :
		payload.append(boatToJson(boat))

	resp = jsonify(payload)
	resp.status_code = 200
	
	return resp


#-----------------  Helper Functions  ------------------

def boatToJson(boat):
	payload = {
			'name' : boat.name,
			'type' : boat.type,
			'length' : boat.length,
			'id' : boat.key.urlsafe(),
			'at_sea' : boat.at_sea
		}
	return payload