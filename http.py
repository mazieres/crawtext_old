from flask import Flask
from flask import render_template
from flask import request
from crawtext import *
from pattern.web import *

app = Flask(__name__)

from random import choice
pitchz = ['Yet another minimalist web crawler.','Your personnal web crawler.','Web crawler. For fun and science.']

@app.route("/", methods=['GET'])
def index():
	return render_template('index.html', pitch=choice(pitchz))

@app.route("/set_crawler", methods=['GET'])
def set_crawler():
	return render_template('set_crawler.html')

@app.route("/start_crawler_adv", methods=['POST'])
def start_crawler_adv():
	pdf = "No"
	if 'pdf' in request.form:
		pdf = 'Yes'

	added_seeds = ''
	nb_added_seeds = 0
	if 'added_seeds' in request.form:
		added_urls = find_urls(request.form['added_seeds'])
		nb_added_seeds = len(added_urls)
		for each in find_urls(request.form['added_seeds']):
			added_seeds += each + '\n'


	return render_template('start_crawler_adv.html', query=request.form['query'], depth=request.form['depth'], email=request.form['email'], nb_seeds=request.form['nb_seeds'], seeds_query=request.form['seeds_query'], added_seeds=added_seeds, nb_added_seeds=nb_added_seeds, pdf=pdf)

@app.route("/start_crawler", methods=['POST'])
def start_crawler():
	return render_template('start_crawler.html', query=request.form['query'], depth=10, email=request.form['email'], nb_seeds=10, seeds_query=request.form['query'], added_seeds='None', nb_added_seeds='0', pdf='No')

if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=True)
#	app.run(host="0.0.0.0", debug=False)