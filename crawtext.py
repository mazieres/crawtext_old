#!/usr/bin/python

import sys
import os
import urllib2
import base64
import json
import pymongo
from pymongo import Connection
import string
import time
from pattern.web import *
from random import choice
import pprint
import re
import threading
from decruft import Document
import operator
from lxml import etree
import copy
from pattern.graph import *

reload(sys) 
sys.setdefaultencoding("utf-8")

nb_thread_limit = 200

root_url = 'https://api.datamarket.azure.com/Bing/Search/'
markets_list = ["ar-XA","bg-BG","cs-CZ","da-DK","de-AT","de-CH","de-DE","el-GR","en-AU","en-CA","en-GB","en-ID","en-IE","en-IN","en-MY","en-NZ","en-PH","en-SG","en-US","en-XA","en-ZA","es-AR","es-CL","es-ES","es-MX","es-US","es-XL","et-EE","fi-FI","fr-BE","fr-CA","fr-CH","fr-FR","he-IL","hr-HR","hu-HU","it-IT","ja-JP","ko-KR","lt-LT","lv-LV","nb-NO","nl-BE","nl-NL","pl-PL","pt-BR","pt-PT","ro-RO","ru-RU","sk-SK","sl-SL","sv-SE","th-TH","tr-TR","uk-UA","zh-CN","zh-HK","zh-TW"]
user_agents = [u'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.1 (KHTML, like Gecko) Chrome/22.0.1207.1 Safari/537.1', u'Mozilla/5.0 (Windows NT 6.1; rv:15.0) Gecko/20120716 Firefox/15.0a2', u'Mozilla/5.0 (compatible; MSIE 10.6; Windows NT 6.1; Trident/5.0; InfoPath.2; SLCC1; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; .NET CLR 2.0.50727) 3gpp-gba UNTRUSTED/1.0', u'Opera/9.80 (Windows NT 6.1; U; es-ES) Presto/2.9.181 Version/12.00', ]
unwanted_extensions = ['css','js','gif','GIF','jpeg','JPEG','jpg','JPG','pdf','PDF','ico','ICO','png','PNG','dtd','DTD']
allowed_mimetypes = ['text/html']
unwanted_domain = ['www.facebook.com']

new_seeds = set()
next_seeds = set()

posts = {}

threads = []

class Content:
	def __init__(self, src):
		self.raw_src = src
		self.xml_src = etree.HTML(src)

	def get_content_xpath(self):
        # Huge thanks to Renaud Lifchitz for this idea
		d = {}
		self.xpath = ''
		def build_xpath(src_xml, src_xml_tag):
			for child in src_xml:
				if not child.getchildren() and child.text:
					full_path = "/%s/%s" % (src_xml_tag, child.tag)
					if d.has_key(full_path):
						d[full_path] += [len(child.text)]
					else:
						d[full_path] = [len(child.text)]
				else:
					build_xpath(child, "%s/%s" % (src_xml_tag, child.tag))
		build_xpath(self.xml_src, self.xml_src.tag)
		d_average = {x: sum(d[x]) for x in d}	#/len(d[x])
		d_sorted = sorted(d_average.iteritems(), key=operator.itemgetter(1), reverse=True)
		xpath_ranking = [x for x in d_sorted if not any(_ in x[0] for _ in ['style', 'script','built-in'])]
		for i in range(1):
			for path in self.xml_src.xpath(xpath_ranking[i][0]):
				try:
					self.xpath += path.text
				except:
					pass

	def get_content_decruft(self):
		self.decruft = Document(self.raw_src).summary()


class Page:
	def __init__(self, uri):
		self.uri = uri
		self.outlinks = set()
		self.inlinks = set()
		self.pattern = URL(self.uri)

	def check_domain(self):
		return bool(self.pattern.domain not in unwanted_domain)

	def check_mimetype(self):
		if extension(self.pattern.page) in unwanted_extensions:
			return False
		else:
			return bool(self.pattern.mimetype == 'text/html')

	def get_src(self):
		self.src = URL(self.uri).open(user_agent=choice(user_agents)).read()

	def is_relevant(self):
		return bool(re.search(query.replace(' ','.*'), self.src, re.IGNORECASE))

	def get_outlinks(self):
		for found_url in find_urls(self.src, unique=True):
			if '"' in found_url:				# Tweak Pattern bug on find_urls output format
				found_url = found_url.split('"')[0] 
			if ');' in found_url:				# IDEM
				found_url = found_url.split(');')[0]
			if '#' in found_url:				# Strip Anchors
				found_url = found_url.split('#')[0]
			self.outlinks.add(found_url)

	def select_content(self, method):
		c = Content(self.src)
		if 'decruft' in method:
			c.get_content_decruft()
			self.content_decruft = c.decruft
		if 'xpath' in method:
			c.get_content_xpath()
			self.content_xpath = c.xpath

	def build_post(self):
		self.post = {}
		self.post['url'] = self.uri
		#self.post['src'] = self.src
		self.post['outlinks'] = self.outlinks
		self.post['inlinks'] = self.inlinks
		self.post['content'] = {}
		if self.content_xpath:
			self.post['content']['xpath'] = self.content_xpath
		if self.content_decruft:
			self.post['content']['decruft'] = self.content_decruft
		posts[self.uri] = self.post

def query_bing(query_words, password, nb_results=10, market="fr-FR", username=''):
	seeds = set([])
	# Formatting username and password for HTTP headers 
	base64string = base64.encodestring('%s:%s' % (username,password) )

	# Formatting query	
	query_clean = query_words.replace(' ','%20')

	# Checking Market validity
	if market not in markets_list:
		print "The market you specified is not supported by Bing API"
		print "Markets List: " + str(markets_list)
		sys.exit(1)

	# Limiting the number of results (This limit can be overcome > TODO, check "next" in bing answer)
	if nb_results > 50:
		print "Results are limited to 50. Set to 50."
		nb_results = 50

	query_url = 'Web?Query=%27'+('%s' % query_clean)+'%27&$top='+str(nb_results)+'&$format=JSON&Market=%27'+market+'%27'
	full_url = root_url + query_url

	query = urllib2.Request(full_url)
	query.add_header("Authorization", "Basic %s" % base64string )

	print "Query URL: ", query.get_full_url()
	for each in query.header_items():
		print each

	try:
		results_utf8 = unicode(urllib2.urlopen(query).read(), errors='ignore')
	except IOError as e:
	    if hasattr(e, 'reason'):
	        print 'We failed to reach a server.'
	        print 'Reason: ', e.reason
	    elif hasattr(e, 'code'):
	        print 'The server couldn\'t fulfill the request.'
	        print 'Error code: ', e.code
	        print 'Error message: ', e.msg
	        print 'Header: ', e.hdrs
	        print 'FP: ', e.fp

	results_json = json.loads(results_utf8)
	results = results_json['d']['results']
	print type(results)
	for each in results:
		seeds.add(each['Url'])
	return seeds

def graph(posts):
	g = Graph()
	for each in posts:
		g.add_node(each)
	for url in posts:
		for outlink in posts[url]['outlinks']:
			g.add_edge(url, outlink, weight=0.0, type='is-related-to')
	timestamp = ''
	for each in time.localtime()[:]:
		timestamp += str(each) + "_"
	export(g, 'graph_%s' % timestamp, directed=True, width=1000, height=600, distance=15)

def post_to_db(query, posts):
	connection = Connection()
	connection = Connection('localhost', 27017)

	timestamp = ''
	for each in time.localtime()[:]:
		timestamp += str(each) + "_"

	db = connection['crOOw']
	collection_name = "%s_%s" % (query.replace(' ',''), timestamp)
	collection = db['%s' % collection_name]
	for post in posts:
		collection.insert(posts[post])

def build_inlinks_clean_outlinks(posts):
	viewed_urls = posts.keys()
	posts_cp = copy.deepcopy(posts)
	for each in posts:
		for url in posts[each]['outlinks']:
			if url in viewed_urls:
				posts_cp[url]['inlinks'].add(each)
			else:
				posts_cp[each]['outlinks'].remove(url)
	for each in posts:
		posts[each]['inlinks'] = list(posts_cp[each]['inlinks'])
		posts[each]['outlinks'] = list(posts_cp[each]['outlinks'])

def parse(url):
	u = Page(url)
	if not u.check_mimetype():
		print '[LOG]:: The page %s is not HTML and won\'t be parsed: Discarded.' %  u.uri
		return
	if not u.check_domain():
		print '[LOG]:: The page %s belong to unwanted domain list' % u.uri
		return
	u.get_src()
	if not u.is_relevant():
		print '[LOG]:: The page %s doesn\'t seem relevant regarding the query: Discarded.' % u.uri
		return
	print '[LOG]:: The page %s is relevant.' % u.uri
	u.get_outlinks()
	global new_seeds
	new_seeds = {x for x in u.outlinks if x not in posts.keys()}
	global next_seeds
	next_seeds = next_seeds.union(new_seeds)
	print '%d parsed links: ' % len(u.outlinks)
	u.select_content(['decruft','xpath'])
	u.build_post()

def chunks(l, n):
    return [l[i:i+n] for i in range(0, len(l), n)]

def crawl(seeds, query, depth=1):
	print '[LOG]:: Starting Crawler with Depth set to %d' % depth
	print '[LOG]:: Seeds are %s' % str(seeds)
	print '[LOG]:: Query is "%s"' % query
	while depth >= 0:
		for each in chunks(list(seeds),nb_thread_limit):
			for url in each:
				t = threading.Thread(None, parse, None, (url,))
				t.start()
				threads.append(t)
			for thread in threads:
				thread.join()
		seeds = {x for x in next_seeds if x not in posts.keys()}
		next_seeds.clear()
		depth -= 1
		crawl(seeds, query, depth)


if __name__ == '__main__':
	seeds = query_bing("Algues Vertes","HIDDEN", nb_results=10)
	query = "Algues Vertes"

	crawl(seeds, query)

	build_inlinks_clean_outlinks(posts)
	
	pp = pprint.PrettyPrinter(indent=4)
	pp.pprint(posts)
	graph(posts)
	post_to_db(query, posts)

