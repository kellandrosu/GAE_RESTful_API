from google.appengine.ext import ndb
from flask import Flask, render_template, request, jsonify


app = Flask(__name__)


#use flask to handle requests. 
	#interpret request body using json

#boat entity definition
class Boat(ndb.Model):
    id = ndb.IntegerProperty()
    name = ndb.StringProperty()
    type = ndb.StringProperty()
    length = ndb.FloatProperty()
    at_sea = ndb.BooleanProperty(default=True)


@app.route('/boat', methods=["POST", "GET"])
def createBoat():
	boat = Boat(
    	id=123, name='Boaty McBoatface', type="Tugboat", length=10, at_sea=False)
	boatkey = boat.put()

	message = {
		'id' : boatkey.urlsafe()
	}
	resp = jsonify(message)
	resp.status_code = 200
	return resp
	

@app.route('/boat/<boatId>', methods=['GET'])
def getBoat():
	boatkey = ndb.Key(urlsafe=boatId)
	boat = boatkey.get()

	return boat.name
	


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