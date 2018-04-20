

from google.appengine.ext import ndb
import logging
from flask import Flask, render_template, request, jsonify, json


app = Flask(__name__)

#set print to console
logging.basicConfig(level=logging.DEBUG)

#disables strict slashes GLOBALLY https://stackoverflow.com/questions/33241050/trailing-slash-triggers-404-in-flask-path-rule?utm_medium=organic&utm_source=google_rich_qa&utm_campaign=google_rich_qa
app.url_map.strict_slashes = False



#boat entity definition
class Boat(ndb.Model):
    name = ndb.StringProperty()
    type = ndb.StringProperty()
    length = ndb.FloatProperty()
    at_sea = ndb.BooleanProperty(default=True)

class Departure(ndb.Model):
	date = ndb.DateProperty()
	boat = ndb.KeyProperty(Boat)

class Slip(ndb.Model):
	number = ndb.IntegerProperty()
	current_boat = ndb.KeyProperty(Boat)
	arrival_date = ndb.StringProperty()
	#departure_date = ndb.StructuredProperty(Departure, repeated=True)

#manages slip human-readable numbers 
class SlipNum(ndb.Model):
	number = ndb.IntegerProperty()
	taken = ndb.BooleanProperty()


#   ----------  REQUEST HANDLERS  ------------

@app.route('/all', methods=['DELETE'])
def deleteAll():

	allKeys = Boat.query().fetch(keys_only=True)
	allKeys.extend(Departure.query().fetch(keys_only=True))
	allKeys.extend(Slip.query().fetch(keys_only=True))
	allKeys.extend(SlipNum.query().fetch(keys_only=True))
	ndb.delete_multi( allKeys )
	return 'All Entities Removed'



@app.route('/slips', methods=['POST'])
def createSlip():

	slip = Slip()		

	assignSlipNum(slip)
	slip.put()

	resp = slipToJSON(slip)
	resp.status_code = 200

	return resp



@app.route('/slips/<slipId>', methods=['GET', 'PATCH', 'DELETE'])
def handleSlipId(slipId):
	slipKey = ndb.Key(urlsafe=slipId)
	slip = slipKey.get()

	if slipKey.kind() == 'Slip' and slip:
		if request.method == 'DELETE' :
			slipKey.delete()
			payload = "Deleted: " + slipKey	#empty payload
		else:# TODO:

			if request.method == 'PATCH':
				reqObj = request.get_json(force=True)

				if 'number' in reqObj:
					#check if number is taken 
					qry = Slip.query(Slip.number==reqObj.number, Slip.taken==False)
					if not qry.fetch():
						#if slipNum is taken, cancel operation and return with error
						resp = jsonify( { 'Error' : "Slip number "+str(reqObj.number)+" is unavailable." } )
						resp.status_code = 400						
						return resp
					else:
						assignSlipNum(slip=slip, number=reqObj.number)

				if 'arrival_date' in reqObj:
					slip.arrival_date = reqObj.arrival_date

				slip.put()

			#default GET behavior
			payload = slipToJSON(slip)
			
		status_code = 200

	else:
		status_code = 400
		payload = 'Error: Could not find Boat with id=' + boatId

	#prepare and send response
	resp = jsonify(payload)
	resp.status_code = status_code
	
	return resp

#get all boats
@app.route('/slips', methods=['GET'])
def getAllSlips():

	qry = Slip.query()
	payload = []
	for slip in qry :
		payload.append(slipToJSON(slip))
	resp = jsonify(payload)
	resp.status_code = 200
	
	return resp


#create new boat
@app.route('/boats', methods=['POST'])
def createBoat():

	reqObj = request.get_json(force=True)

	if 'name' in reqObj and 'type' in reqObj and 'length' in reqObj:
		
		boat = Boat(
	    	name=reqObj['name'],
	    	type=reqObj['type'],
	    	length=reqObj['length'],
	    	at_sea=True
	    	)

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


#get, modify or delete boat by id
@app.route('/boats/<boatId>', methods=['GET', 'PATCH', 'DELETE'])
def handleBoatId(boatId):

	boatkey = ndb.Key(urlsafe=boatId)
	boat = boatkey.get()

	if boatkey.kind() == 'Boat' and boat:	
		#handle DELETE
		if request.method == 'DELETE' :
			boatkey.delete()
			payload = "Deleted: " + boatId	#empty payload

		#handle GET and PATCH
		else :

			if request.method == 'PATCH' :
				reqObj = request.get_json(force=True)

				if 'name' in reqObj :
					boat.name = reqObj['name']
				if 'type' in reqObj :
					boat.type = reqObj['type']
				if 'length' in reqObj:
					boat.length = reqObj['length']
				#if 'at_sea' in reqObj :
				#	boat.at_sea = reqObj['at_sea']

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
def getBoats():

	qry = Boat.query()

	payload = []

	for boat in qry :
		payload.append(boatToJson(boat))

	resp = jsonify(payload)
	resp.status_code = 200
	
	return resp


#-----------------  Helper Functions  ------------------

#finds or creates available slip number and updates slip with new number
def assignSlipNum(slip, number=None):

	qry = SlipNum.query()

	#CASE: number is specified, so check if exists
	if not number is None :
		slipNum = qry.filter(Slip.number==Getnumber).fetch()[0]
		#CASE: SlipNum doesn't exist, so create slipNum
		if not slipNum:
			slipNum = SlipNum(number=number, taken=True)
		#CASE: slipNum exists and is available, so make unavailable
		elif slipNum.taken == False:
			slipNum.taken = True
		#CASE: slipNum exists and is Unavailable, so exit function
		else:
			return
	#CASE: number not specified, and SlipNum table is empty, so create first SlipNum
	elif not qry.fetch():
		#if SlipNum is empty, create first number, add to set and update slip
		slipNum = SlipNum(number=1, taken=True)
	#CASE: number not specified, and SlipNum table is not empty
	else:
		availableNums = qry.filter(SlipNum.taken==False)
		#CASE: There are no available SlipNums, so create new slipNum
		if not availableNums.fetch():
			#create new SlipNum from largest in qry + 1
			newNumber = qry.order(-SlipNum.number).fetch()[0].number + 1
			slipNum = SlipNum(number=newNumber, taken=True)

		else:
			#CASE: Ther is available SlipNum, so get lowest available and assign it
			slipNum = availableNums.order(SlipNum.number).iter().next()
			slipNum.taken = True
	
	#update slipnum table
	slipNum.put()
	#assign slipNum to slip
	slip.number = slipNum.number
	slip.put()
	return

def slipToJSON(slip):
	payload = { 
		"id": slip.key.urlsafe(), 
		"number" : slip.number,
		"current_boat" : slip.current_boat,
		"arrival_date" : slip.arrival_date 
	}
	return payload

#returns json object of given Boat class
def boatToJson(boat):
	payload = {
			'name' : boat.name,
			'type' : boat.type,
			'length' : boat.length,
			'id' : boat.key.urlsafe(),
			'at_sea' : boat.at_sea
		}
	return payload