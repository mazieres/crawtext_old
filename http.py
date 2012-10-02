from flask import Flask
from flask import render_template
from flask import request
from crawtext import *

app = Flask(__name__)

from random import choice
pitchz = ['Yet another minimalist web crawler.','Your personnal web crawler.','Web crawler. For fun and science.']

@app.route("/", methods=['GET'])
def hello():
	return render_template('index.html', pitch=choice(pitchz))

@app.route("/set_crawler", methods=['GET'])
def set_crawler():
	return render_template('set_crawler.html')

@app.route("/start_crawler", methods=['POST'])
def start_crawler():
	return render_template('start_crawler.html', query=request.form['query'], depth=request.form['depth'], email=request.form['email'])



if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=True)
#	app.run(host="0.0.0.0", debug=False)