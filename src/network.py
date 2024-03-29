
from src import util

import sys
if sys.version > '3':
	from urllib.request import urlopen
	from urllib.parse import urlencode
else:
	from urllib import urlopen
	from urllib import urlencode
import threading

import time

_server_address = util.read_file('server.txt')

class Request(threading.Thread):
	def __init__(self, action, args, user, password):
		threading.Thread.__init__(self)
		self.setDaemon(True)
		self.args = {'action': action}
		if user != None:
			self.args['user_id'] = user
		if password != None:
			self.args['password'] = password
		for key in args:
			self.args[key] = args[key]
		self.hasresponse = False
		self.response = None
		self.error = False
		self.lock = threading.Lock()
	
	def update_address(self, new_address):
		global _server_address
		_server_address = new_address
		util.verboseprint("SERVER HAS MOVED TO:", new_address)
		util.write_file('server.txt', new_address)
	
	def run(self):
		self.send_request()
	
	def send_request(self, attempts=10):
		is_error = False
		data = None
		try:
			url = _server_address + '/server.py?' + urlencode(self.args)
			util.verboseprint("Sending: " + url)
			c = urlopen(url)
			raw_bytes = c.read()
			if 'bytes' in str(type(raw_bytes)): # Ugh, new Python 3 annoyance I learned just now
				raw_bytes = raw_bytes.decode('utf-8')
			data = deserialize_thing(raw_bytes)
			util.verboseprint("RECEIVED: " + str(data))
			if data == None:
				util.verboseprint("RAW DATA: " + raw_bytes.replace('<br />', "\n"))
			c.close()
			
			if data != None and data.get('redirect') != None:
				self.update_address(str(data['redirect']))
				self.send_request()
				return
			
		except:
			if attempts < 1:
				data = { 'success': False, 'message': "Server did not respond" }
				is_error = True
			else:
				time.sleep((11 - attempts) * 3.0)
				self.send_request(attempts - 1)
				return
		
		self.lock.acquire(True)
		self.error = is_error
		self.response = data
		self.hasresponse = True
		self.lock.release()
		
	
	def has_response(self):
		return self.hasresponse
	
	def get_response(self):
		try:
			return self.response
		except:
			return { 'success': False, 'message': "unknown server response: " + str(self.response) }
	
	def is_error(self):
		return self.error
	
	def get_error(self):
		if self.hasresponse:
			return self.response.get("message", "Unknown error has occurred.")
	
	def send(self):
		self.start()

def _send_command(action, args, user=None, password=None):
	request = Request(action, args, user, password)
	request.send()
	return request

def read_till_bang(stream, index):
	output = []
	while index[0] < len(stream) and stream[index[0]] != '!':
		c = stream[index[0]]
		if c == '$':
			index[0] += 1
			c = stream[index[0]]
			if c == '$':
				output.append('$')
			else:
				output.append('!')
		else:
			output.append(c)
		index[0] += 1
	index[0] += 1
	return ''.join(output)

def deserialize_thing(string, index=None):
	if index == None:
		index = [0]
	if index[0] >= len(string): return None
	t = string[index[0]]
	index[0] += 1
	if t == 'n':
		index[0] += 1
		return None
	if t in 'ilfsb':
		x = read_till_bang(string, index)
		if t == 'i': return int(x)
		if t == 'l':
			if sys.version > '3':
				return int(x)
			return long(x)
		if t == 'f': return float(x)
		if t == 's': return x
		if t == 'b': return x == '1'
	if t == 't':
		output = []
		while index[0] < len(string) and string[index[0]] != '!':
			output.append(deserialize_thing(string, index))
		index[0] += 1
		return output
	
	if t == 'd':
		output = {}
		while index[0] < len(string) and string[index[0]] != '!':
			key = deserialize_thing(string, index)
			value = deserialize_thing(string, index)
			output[key] = value
		index[0] += 1
		return output
	index[0] += 1
	return None

def send_echo(stuff):
	return _send_command("echo", { 'data': stuff })

def send_authenticate(username, password):

	if _is_tutorial:

		fake().send_authenticate(username, password)
	return _send_command('authenticate', { 'user': username, 'password': password })

def fake():
	from src import fakenetwork
	return fakenetwork

def send_poll(user_id, password, sector_you_care_about, last_ids_by_sector):
	if _is_tutorial:
		return fake().send_poll(user_id, password, sector_you_care_about, last_ids_by_sector)
	sectors = _get_poll_args(sector_you_care_about, last_ids_by_sector)
	return _send_command('poll', { 'sectors': sectors }, user_id, password)

def _get_poll_args(sector, last_ids_by_sector):
	nsectors = {}
	if '^' in str(sector):
		x,y = util.totuple(sector)
	else:
		x,y = sector
	
	for dx in (-1, 0, 1):
		for dy in (-1, 0, 1):
			nsectors[(x + dx, y + dy)] = True
	s_r = []
	for s in nsectors.keys():
		last_id = last_ids_by_sector.get(s, 0)
		s_r.append(str(last_id) + '^' + util.fromtuple(s))
	return ','.join(s_r)

def send_username_fetch(user_ids):
	if _is_tutorial:
		return fake().send_username_fetch(user_ids)
	return _send_command('getuser', { 'user_id_list': ','.join(map(str, user_ids)) })

def send_build(user_id, password, type, sector_x, sector_y, loc_x, loc_y, sector_you_care_about, last_ids_by_sector, client_token):
	if _is_tutorial:
		return fake().send_build(user_id, password, type, sector_x, sector_y, loc_x, loc_y, sector_you_care_about, last_ids_by_sector, client_token)
	
	poll_sectors = _get_poll_args(sector_you_care_about, last_ids_by_sector)
	last_id = last_ids_by_sector.get((sector_x, sector_y), 0)
	return _send_command('build', {
		'type': type,
		'sector': util.fromtuple((sector_x, sector_y)),
		'last_id': last_id,
		'loc': util.fromtuple((loc_x, loc_y)),
		'client_token': client_token,
		'poll_sectors': poll_sectors
		}, user_id, password)
	
def send_demolish(user_id, password, sector_x, sector_y, x, y, client_token):
	if _is_tutorial:
		return fake().send_demolish(user_id, password, sector_x, sector_y, x, y, client_token)
	return _send_command('demolish', {
		'sector': util.fromtuple((sector_x, sector_y)),
		'loc': util.fromtuple((x, y)),
		'client_token': client_token
	}, user_id, password)

def send_radar(user_id, password, rx, ry):
	if _is_tutorial:
		return fake().send_radar(user_id, password, rx, ry)
	return _send_command('radar', {
		'rx': rx,
		'ry': ry }, user_id, password)

def send_quarry(user_id, password, sector, xy):
	if _is_tutorial:
		return fake().send_quarry(user_id, password, sector, xy)
	return _send_command('quarrydata', {
		'sector': sector,
		'xy': xy }, user_id, password)

def send_getbots(user_id, password):
	if _is_tutorial:
		return fake().send_getbots(user_id, password)
	return _send_command('getbots', {}, user_id, password)

def send_buildbots(user_id, password, type):
	if _is_tutorial:
		return fake().send_buildbots(user_id, password, type)
	return _send_command('buildbot', { 'type': type }, user_id, password)

def send_deploy(user_id, password):
	if _is_tutorial:
		return fake().send_deploy(user_id, password)
	return _send_command('dispatchbots', { }, user_id, password)

def send_give_resources_debug(user_id, password):
	if _is_tutorial:
		return fake().send_give_resources_debug(user_id, password)
	return _send_command('debug_resources', { }, user_id, password)

def send_start_research(user_id, password, subject):
	if _is_tutorial:
		return fake().send_start_research(user_id, password, subject)
	return _send_command('start_research', { 'subject': subject }, user_id, password)

# alien_type = 1, 2, 3
def send_alien_award(user_id, password, alien_type):
	if _is_tutorial:
		return fake().send_alien_award(user_id, password, alien_type)
	return _send_command('alienkill', { 'alientype': alien_type }, user_id, password)

def send_battle_success(user_id, password, attacked_id, bytes):
	if _is_tutorial:
		return fake().send_battle_success(user_id, password, attacked_id, bytes)
	return _send_command('attacksuccess', { 'numbytes': bytes, 'attacked': attacked_id }, user_id, password)

_is_tutorial = False
def toggle_tutorial(is_tutorial):
	global _is_tutorial
	_is_tutorial = is_tutorial


