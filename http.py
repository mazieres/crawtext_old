from flask import Flask
from flask import render_template
from flask import request
from crawtext import *

app = Flask(__name__)

@app.route("/", methods=['GET'])
def hello():
	return render_template('index.html')

@app.route("/start_crawler", methods=['POST'])
def start_crawler():
	return render_template('start_crawler.html', query=request.form['query'], depth=request.form['depth'], email=request.form['email'])

if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=True)
#	app.run(host="0.0.0.0", debug=False)