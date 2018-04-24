

from google.appengine.ext import ndb
import logging
from flask import Flask, render_template, request, jsonify, json
import datetime


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
	current_boat = ndb.StringProperty(default="")
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

	assignSlipNum(slip=slip)
	slip.put()

	resp = jsonify(slipToJSON(slip))
	resp.status_code = 200
	
	return resp



@app.route('/slips/<slipId>', methods=['GET', 'PATCH', 'DELETE'])
def handleSlipId(slipId):
	slipKey = ndb.Key(urlsafe=slipId)
	slip = slipKey.get()

	if slipKey.kind() == 'Slip' and slip:
		if request.method == 'DELETE' :
			#if slip has a boat, undock it
			if slip.current_boat:
				boatToUndock = ndb.Key(urlsafe=slip.current_boat).get()
				undockBoat( boatToUndock )

			slipKey.delete()
			payload = "Deleted: " + slipKey	#empty payload

		else:
			if request.method == 'PATCH':
				reqObj = request.get_json(force=True)

				if 'number' in reqObj:
					#check if number is taken 
					qry = Slip.query(Slip.number==reqObj.number, Slip.taken==False)
					if not qry.fetch():
						#if slipNum is taken, cancel operation and return with error
						resp = jsonify( { 'Error' : "Slip number "+str(reqObj.number)+" is unavailable." } )
						resp.status_code = 403						
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
		status_code = 403
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

	for slip in qry:
		payload.append( slipToJSON(slip) )
	
	resp = jsonify(payload)
	resp.status_code = 200
	
	return resp


#create new boat
@app.route('/boats', methods=['POST'])
def createBoat():

	reqObj = request.get_json(force=True)

	if 'name' in reqObj and 'type' in reqObj and 'length' in reqObj:
		
		if isNameAvailable( reqObj['name'] ):

			boat = Boat(
		    	name=reqObj['name'],
		    	type=reqObj['type'],
		    	length=reqObj['length'],
		    	at_sea=True
		    	)

			#write boat to ndb
			boatkey = boat.put()

			#compile response body
			payload = {	'id' : boat.key.urlsafe()	}
			status_code = 200

		else:
			payload = {	'Error' : "Name in use"	}
			status_code = 403

	else:
		status_code = 403
		payload = { 'Error': "403 Bad Request" }
	
	#prepare and send response
	resp = jsonify(payload)
	resp.status_code = status_code

	return resp

@app.route('/boats/<boatId>/dock', methods=['PUT', 'DELETE'])
def handleDockBoat(boatId):
	
	boat = ndb.Key(urlsafe=boatId).get()
	#check if valid boatId
	if boat and boat.key.kind() == 'Boat':
			#PUT handler
			if request.method == 'PUT':

				reqObj = request.get_json(force=True)		
				#save slip ID and date if available
				slipId = reqObj['slipId'] if 'slipId' in reqObj else None
				date =  reqObj['date'] if 'date' in reqObj else None	
				
				respObj = dockBoat(boat, slipId=slipId, date=date)

			#DELETE handler
			elif request.method == 'DELETE':
				if boat.at_sea:
					respObj = {
						'message': 'Error: Boat is not docked',
						'status_code' : 403
					}
				else:
					undockBoat(boat)
					respObj = {
						'message': boatToJSON(boat),
						'status_code' : 403
					}
	else:
		respObj = {
			'message': 'Error: Invalid Boat Id',
			'status_code' : 403
		}

	resp = jsonify(respObj['message'])
	resp.status_code = respObj['status_code']

	return resp


#get, modify or delete boat by id
@app.route('/boats/<boatId>', methods=['GET', 'PATCH', 'DELETE'])
def handleBoatId(boatId):

	boatkey = ndb.Key(urlsafe=boatId)
	boat = boatkey.get()

	if boatkey.kind() == 'Boat' and boat:	
		#handle DELETE
		if request.method == 'DELETE' :
			if not boat.at_sea:
				undockBoat(boat)

			boatkey.delete()
			payload = "Deleted Boat: " + boatId	#empty payload

		#handle GET and PATCH
		else :
			if request.method == 'PATCH' :
				reqObj = request.get_json(force=True)

				if 'name' in reqObj :

					#if name isn't available, abort
					if not isNameAvailable( reqObj['name'] ):
						resp = jsonify('Error: Name in use')
						resp.status_code = 403
						return resp

					boat.name = reqObj['name']

				if 'type' in reqObj :
					boat.type = reqObj['type']

				if 'length' in reqObj:
					boat.length = reqObj['length']

				boat.put()

			#default behavior for GET
			payload = boatToJSON(boat)
			
		status_code = 200

	else:
		status_code = 403
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
		payload.append(boatToJSON(boat))

	resp = jsonify(payload)
	resp.status_code = 200
	
	return resp


#------------------------------  HELPER FUNCTIONS  --------------------------------

#removes boat from slip
def undockBoat(boat):

	slip = Slip.query( Slip.current_boat==boat.key.urlsafe() ).fetch()

	if slip[0]:
		slip[0].current_boat = ""
		slip[0].arrival_date = None
		slip[0].put()

	boat.at_sea = True
	boat.put()

#check if name is available
def isNameAvailable(name):

	boats = Boat.query(Boat.name==name).fetch()

	if boats:
		return False
	
	return True

#handles the database model
#returns the json object for response
def dockBoat(boat, slipId=None, date=None):
	print 'hello'
	if not boat.at_sea:
		return {
			'status_code': 403,
			'message': "Error: Boat currently docked"
		}

	#get specified slip	
	if slipId:
		slipKey = ndb.Key(urlsafe=slipId)
		slip = slipKey.get()

		if slip.current_boat:
			return {
				'status_code': 403,
				'message': "Error: Specified slip is occupied"
			}
	
	#find available slip
	else:
		#get first open slip
		availableSlips = Slip.query(Slip.current_boat == "").fetch()
		
		if not availableSlips:
			return {
				"status_code": 403,
				"message": "Error: No slips available"
			}
		else:
			slip = availableSlips[0]

	#get current date if not provided
	if not date:
		now = datetime.datetime.now()
		date = "%d/%d/%d" % (now.month, now.day, now.year)

	
	boat.at_sea = False
	boat.put()

	slip.current_boat = boat.key.urlsafe()
	slip.arrival_date = str(date)
	slipKey = slip.put()

	return 	{
				'status_code': 200,
				'message': "Boat Docked at Slip :" + str(slip.number)
			}
	

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
def boatToJSON(boat):
	payload = {
			'name' : boat.name,
			'type' : boat.type,
			'length' : boat.length,
			'id' : boat.key.urlsafe(),
			'at_sea' : boat.at_sea
		}
	return payload