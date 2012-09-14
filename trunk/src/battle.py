import random, math
from src import sprite, structure, terrain
from src.font import get_text

class Battle:
	def __init__(self, user_id, buildings, other_user_id=None):
		# if other_user_id is, then this is an alien vs player session
		self.user_id = user_id
		self.other_id = other_user_id
		self.buildings = buildings
		
		print("base size: %s" % len(self.buildings))
		hqs = [b for b in self.buildings if isinstance(b, structure.HQ)]
		print("number of HQs: %s" % len(hqs))
		self.hq = hqs[0]

#		self.buildbasepath()
		
		self.data_stolen = 0.0 # add to this in real time as the sprites successfully get into the HQ
		self.aliens = []  # both aliens and bots
		
		# queue of the aliens and the frames at which they'll appear
		self.alienq = []
		
		# Number of bots that can be deployed
		self.nbots0 = 0
		
		# TODO: make this harder depending on the era and/or your bases's strength
		if self.is_computer_attacking():
			self.alienq = [
				(t, sprite.Alien)
				for t in range(30, 400, 10)
			]
		else:
			self.nbots0 = 40

		self.nbots = self.nbots0

		self.t = 0

	# Obsolete function: pathfinding no longer needed
	def buildbasepath(self):
		self.forbiddentiles = []
		for building in self.buildings:
			#print building.btype, building.rsquares()
			self.forbiddentiles.extend(building.rsquares())
		self.pathdistance = {}
		self.pathparent = {}
		tileq, d = self.hq.rsquares(), 0
		#print tileq
		while tileq:
			for tile in tileq:
				self.pathdistance[tile] = d
			if d >= 25: break
			ntileq = set()
			for x0,y0 in tileq:
				for dx in (-1,1):
					for dy in (-1,1):
						x,y = x0+dx,y0+dy
						if (x,y) in self.forbiddentiles or terrain.isunderwater(x, y):
							continue
						if (x,y) not in self.pathdistance:
							ntileq.add((x,y))
							self.pathparent[(x,y)] = (x0,y0)
			tileq = sorted(ntileq)
			d += 1

	def pathtohq(self, x0, y0):
		path = [(x0, y0)]
		while self.pathdistance[path[-1]]:
			path.append(self.pathparent[path[-1]])
		return path

	def collective_sprite_midpoint(self):
		return (0, 0)

	def deploy(self, scene, target, btype):
		X0, Y0 = terrain.toModel(self.hq.x, self.hq.y)
		#print self.hq.x, self.hq.y, X0, Y0, X0 - Y0, -X0 - Y0
		while True:
            # TODO: get them to the base border
			theta = random.random() * 1000
			r = 12
			X = int((X0 + r * math.sin(theta))//1)
			Y = int((Y0 + r * math.cos(theta))//1)
			x, y = terrain.nearesttile(X - Y, -X - Y)
			if not terrain.isunderwater(x, y) and scene.empty_tile(x, y):
				break
		alien = btype(X, Y)
		targets = [b for b in self.buildings if b.attackable and b.hp >= 0]
		alien.settarget(random.choice(targets))
		self.aliens.append(alien)
	
	def attack_building(self, scene, building):
		if building not in self.buildings:
			return False
		if not building.attackable:
			return False
		if building.hp <= 0:
			return False
		if not self.nbots:
			return False
		self.deploy(scene, building, sprite.Seeker)
		self.nbots -= 1
		return True

	def update(self, scene):
		self.t += 1
		if self.alienq and self.t >= self.alienq[0][0]:
			t, atype = self.alienq.pop(0)
			# TODO: choose a starting position based on the base layout
			targets = [b for b in self.buildings if b.attackable and b.hp >= 0]
			target = random.choice(targets)
			self.deploy(scene, target, atype)

		for b in self.buildings:
			b.handleintruders(self.aliens)
		
		for a in self.aliens: a.update(scene)
		for b in self.buildings: b.update(scene)
		
		self.aliens = [a for a in self.aliens if a.alive]
	
	# aliens, seeker bots, projectiles
	def get_sprites(self):
		return self.aliens
	
	def is_complete(self):
		# HQ disabled
		if self.hq.hp <= 0:
			return True
		if self.is_computer_attacking():
			# All aliens defeated
			if not self.alienq and not self.aliens:
				return True
		else:
			if not self.nbots0 and not self.aliens:
				return True
		return False
	##
	# @return {!int} The number of bytes stolen.
	#
	def bytes_stolen(self):
		return self.data_stolen
	
	# This function is done.
	def is_computer_attacking(self):
		return self.other_id == None


	def renderstatus(self, screen):
		data = self.bytes_stolen()
		
		if self.is_computer_attacking():
			text = "Bytes lost: " + str(data)
			color = (255, 0, 0)
		else:
			text = "Bytes learned: " + str(data)
			color = (0, 100, 255)
		if data == 0:
			text = "Attack in progress"

		if self.is_computer_attacking():
			text = "Attack in progress"
		else:
			text = "Bots available: %s/%s" % (self.nbots, self.nbots0)

		
		text = get_text(text, color, 22)
		x = ((screen.get_width() - text.get_width()) // 2)
		y = screen.get_height() * 4 // 5
		screen.blit(text, (x, y))
			


	
	# This is used to send deletions to the server.
	# If you return a building in this function, it should not be
	# returned again (like pygame.event.get())
	# actual values are coordinates of the building
	
	# TODO: this function should probably be invoked at some point, I imagine.
	def new_buildings_destroyed(self):
		dead = [b for b in self.buildings if b is not self.hq and b.hp <= 0]
		if dead:
			self.buildings = [b for b in self.buildings if b not in dead]
		return dead
	
	# return buildings that have been damaged when a player attacks another player
	# this will be 
	# @return a dictionary with coordinate keys. value is ignored 
	def all_buildings_damaged(self):
		return {}
