import pygame, math, random, time
from src import worldmap, camera, settings, terrain, effects, images, jukebox, network
from src.images import get_image


directions = [(0,-1),(1,-1),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1)]

class Sprite(object):
	hp0 = 1
	last_direction = 0
	vx, vy = 0, 0
	shootable = False
	target = None
	diesound = None
	hurtsound = None
	reelstep = None
	awardnumber = None
	freerange = False  # can only exist outside borders
	visible = True
	def __init__(self, x, y, z=None):
		self.vx, self.vy = 0, 0
		self.x, self.y = terrain.toCenterRender(x, y)
		self.z = terrain.height(self.x, self.y) if z is None else z
		self.alive = True
		self.hp = self.hp0

	def lookatme(self):
		camera.lookat(self.x, self.y, terrain.height(self.x, self.y))

	def trackme(self):
		camera.track(self.x, self.y, terrain.height(self.x, self.y), settings.trackvalue)

	def screenpos(self, looker=None):
		return (looker or camera).screenpos(self.x, self.y, self.z)

	# Stand this high above the ground at current position
	def setheight(self, h=0):
		self.z = terrain.height(self.x, self.y) + h

	def rendershadow(self, screen):
		px, py = camera.screenpos(self.x, self.y, terrain.height(self.x, self.y))
		pygame.draw.ellipse(screen, (20, 20, 20, 100), (px - 4, py - 2, 8, 4))

	def update(self):
		pass

	def getModelXY(self):
		return terrain.toModel(self.x, self.y)

	def getsector(self):
		sx, sy = self.getModelXY()
		return sx//60, sy//60

	def setModelXY(self, x, y):
		self.x, self.y = terrain.toRender(self.x - .5, self.y - .5)

	def drawmini(self, surf, x0, y0):
		px, py = int((self.x - x0)//1), int((-self.y + y0)//1)
		pygame.draw.line(surf, self.minicolor, (px-1,py), (px+1,py))
		pygame.draw.line(surf, self.minicolor, (px,py-1), (px,py+1))

	def die(self):
		self.alive = False
		if self.diesound:
			jukebox.play_sound(self.diesound)
		
	def reel(self, x, y):
		dx, dy = x - self.x, y - self.y
		d = math.sqrt(dx**2 + dy**2)
		if not d: return
		self.reelstep = -0.3 * dx / d, -0.3 * dy / d, 3

	def hurt(self, dhp, hurter=None):
		if hurter:
			self.reel(hurter.x, hurter.y)
		self.hp = max(self.hp - dhp, 0)
		if self.hp <= 0:
			self.die()
		else:
			if self.hurtsound:
				jukebox.play_sound(self.hurtsound)

	def sethp0(self, hp0):
		if hp0 == self.hp0: return
		if hp0 > self.hp:
			self.hp = self.hp0 = hp0
		else:
			self.hp0 = hp0
			self.hp = min(self.hp, hp0)

	def heal(self, dhp):
		self.hp = min(self.hp + dhp, self.hp0)

	def healall(self):
		self.hp = self.hp0

	def move(self, dx, dy):
		self.vx = dx * self.v
		self.vy = dy * self.v
		self.moving = bool(dx or dy)
		if self.moving:
			a, b = (dx > 0) - (dx < 0), (dy > 0) - (dy < 0)
			self.last_direction = directions.index((a,b))

	def cango(self, isempty, x, y, exclude=None):
		if terrain.isunderwater(x, y):
			return False
		if not isempty(x, y, exclude) and isempty(self.x, self.y):
			return False
		return True

	# pass it a function that returns whether a given tile is empty.
	def walk(self, isempty, speedfactor = 1):
		if self.reelstep:
			rx, ry, n = self.reelstep
			self.reelstep = (rx, ry, n-1) if n else None
		else:
			rx, ry = 0, 0
		nx = self.x + self.vx * speedfactor + rx
		ny = self.y + self.vy * speedfactor + ry
		if not self.cango(isempty, nx, ny, self.target):
			return False
		self.x, self.y = nx, ny
		return True

little_yous = {}

class You(Sprite):
	v = 0.3   # tiles per frame
	runspeed = 0.35
	walkspeed = 0.15
	minicolor = 255, 128, 0  # color on the minimap
	weaponchargetime = 20
	weapont = 0
	hp0 = 1
	hurtsound = "ouch"
	diesound = "ouch"

	def __init__(self, x, y, z=None):
		Sprite.__init__(self, x, y, z)
		self.moving = False
		self.last_direction = 0
		self.counter = 0

	def setrun(self, running):
		self.v = self.runspeed if running else self.walkspeed

	def shoot(self):
		if self.weapont < self.weaponchargetime:
			return None
		jukebox.play_sound("raygun")
		shot = Ray(self.x, self.y, self.z + 3)
		shot.x, shot.y = self.x, self.y   # it's 1am, i'm doing this the sloppy way
		shot.move(*directions[self.last_direction])
		self.weapont = 0
		return shot

	def update(self, scene):
		self.counter += 1
		self.weapont += 1
		self.walk(scene.empty_tile)
		self.setheight()

	def render(self, screen):
		if not self.visible: return
		if not little_yous:
			little_yous.update(images.spritesheet('playersprite.png', 8, 3))
		i = 0
		if self.moving:
			i = int(self.counter * self.v * 1 // 1) % 4
		img = little_yous[(self.last_direction, (0,1,0,2)[i])]
		
#		self.rendershadow(screen)
		px, py = self.screenpos()
		#pygame.draw.circle(screen, (255, 0, 0), (px, py-21), 4)
		screen.blit(img, (px - img.get_width() // 2, py - img.get_height()))

	def drawhealth(self, screen):
		px, py = 10, screen.get_height() - 10
		for j in range(self.hp0):
			pygame.draw.circle(screen, (255,255,255), (px,py), 8)
			color = (255,0,0) if j < self.hp else (20,20,20)
			pygame.draw.circle(screen, color, (px,py), 7)
			px += 20


# Laser beam from your ray gun
class Ray(Sprite):
	v = 1.0
	lifetime = 14
	strength = 8
	harmrange = 1.5
	t = 0

	def update(self, scene):
		self.t += 1
		if self.t > self.lifetime: self.alive = False
		self.x += self.vx
		self.y += self.vy
#		self.setheight(3)

	def drawmini(self, surf, x0, y0):
		pass

	def render(self, screen):
		p0 = camera.screenpos(self.x, self.y, self.z)
		p1 = camera.screenpos(self.x+self.vx, self.y+self.vy, self.z)
		pygame.draw.line(screen, (255,128,0), p0, p1)

	def attack(self, target):
		target.hurt(self.strength, self)
		self.alive = False

	def handlealiens(self, aliens):
		for alien in aliens:
			if not alien.shootable: continue
			dx, dy = alien.x - self.x, alien.y - self.y
			if dx**2 + dy**2 < self.harmrange**2:
				self.attack(alien)
				return


# Alien base class
class Attacker(Sprite):
	walkspeed = 0.025
	runspeed = 0.05
	hp0 = 3
	minicolor = 255, 255, 0
	size = 6
	attackrange = 1
	seerange = 6
	strength = 1
	shootable = False

	def __init__(self, *args, **kw):
		Sprite.__init__(self, *args, **kw)
		self.target = None
		self.path = None
		self.tractors = []

	def settarget(self, target):
		self.target = target
		self.waypoint = None

	def setpath(self, path):
		self.path = path
	
	def addtractor(self, tractor):
		if tractor not in self.tractors:
			self.tractors.append(tractor)
	
	def removetractor(self, tractor):
		if tractor in self.tractors:
			self.tractors.remove(tractor)

	def speedfactor(self):
		v = math.sqrt(self.vx**2 + self.vy**2)
		if v <= 0: return 1
		gx, gy = terrain.grad(self.x, self.y)
		d = (self.vx * gx + self.vy * gy) / v
		t = 0.5 if self.tractors else 1
		f = 2.0 if self.freerange else 1
		return min(max(1 - 0.12 * d, 0.4), 1) * t * f

	def approachtarget(self, scene):
		self.v = self.runspeed
		dx, dy = self.target.x - self.x, self.target.y - self.y
		if dx**2 + dy**2 < self.attackrange ** 2:
			self.vx, self.vy = 0, 0
			self.attack(self.target)
			return
		# choose the next place to walk to
		if not self.waypoint:
			dirs = [(-1,-1),(-1,1),(1,-1),(1,1)]
			dirs.sort(key = lambda d: -d[0]*dx - d[1]*dy)
			d0, d1 = dirs[0:2]
			a0, a1 = d0[0]*dx + d0[1]*dy, d1[0]*dx + d1[1]*dy
			# first choice of direction with probability a0/(a0+a1)
			fdir = d0 if random.random() * (a0 + a1) <= a0 else d1
			if self.cango(scene.empty_tile, self.x + fdir[0], self.y + fdir[1], self.target):
				self.waypoint = self.x + fdir[0], self.y + fdir[1]
			else:
				d0 = d0 if fdir == d1 else d1
				d1 = dirs[2]
				# second choice of direction with probability 5*a1/(a0+5*a1)
				fdir = d0 if random.random() * (a0 + 5 * a1) < 5 * a1 else d1
				if self.cango(scene.empty_tile, self.x + fdir[0], self.y + fdir[1], self.target):
					self.waypoint = self.x + fdir[0], self.y + fdir[1]
				else:
					fdir = d0 if fdir == d1 else d1
					self.waypoint = self.x + fdir[0], self.y + fdir[1]
		dx, dy = self.waypoint[0] - self.x, self.waypoint[1] - self.y
		if dx**2 + dy**2 < self.v**2:
			self.x, self.y = self.waypoint
			self.waypoint = None
		else:
			d = math.sqrt(dx**2 + dy**2)
			self.move(dx/d, dy/d)

	# attack the player if close enough, otherwise go in some random direction
	def wander(self, scene):
		if random.random() < 0.1:
			dx, dy = self.x - scene.player.x, self.y - scene.player.y
			if dx ** 2 + dy ** 2 < self.seerange ** 2:
				self.settarget(scene.player)
			else:
				self.v = self.walkspeed
				if self.vx or self.vy:
					self.move(0, 0)
				else:
					dx = 0.707 if random.random() < 0.5 else -0.707
					dy = 0.707 if random.random() < 0.5 else -0.707
					self.move(dx, dy)

	def update(self, scene):
		if self.target:
			self.approachtarget(scene)
		self.walk(scene.empty_tile, self.speedfactor())
		self.setheight()

	def attack(self, target):
		self.target.hurt(self.strength,self)
		self.alive = False

	def drawmini(self, surf, x0, y0):
		px, py = int((self.x - x0)//1), int((-self.y + y0)//1)
		surf.set_at((px, py), self.minicolor)

	def drawtractor(self, screen, looker=None):
		if not self.tractors: return
		looker = looker or camera
		x0, y0 = looker.screenpos(self.x, self.y, self.z + 3)
		w, h = 3+int(random.random() * 6), 3+int(random.random()*6)
		pygame.draw.rect(screen, effects.Tractor.color, (x0-w,y0-h,2*w,2*h))

class Alien(Attacker):
	shootable = True
	hp0 = 1
	walkspeed = 0.5
	runspeed = 0.1
	strength = 1
	frames = {}
	fname = "purplealien.png"
	fcounter = 0
	diesound = "squish"

	def __init__(self, x, y, freerange=False):
		self.freerange = freerange
		Attacker.__init__(self, x, y)

	def update(self, scene):
		t0 = time.time()
		if self.target:
			self.approachtarget(scene)
		else:
			self.wander(scene)
		self.walk(scene.empty_tile, self.speedfactor())
		self.setheight()
#		print time.time() - t0

	def render(self, screen, looker=None):
		looker = looker or camera
		px, py = self.screenpos(looker)
		if not looker.isvisible(px, py, 100):
			return
#		self.rendershadow(screen)
		if not self.frames:
			self.frames.update(images.spritesheet(self.fname, 4, 3))
		self.drawtractor(screen, looker)
		self.fcounter += 1
		a = [0,1,0,2][int(self.fcounter * self.v * 3) % 4] if self.vx or self.vy else 0
		frame = self.frames[(self.last_direction//2, a)]
		screen.blit(frame, (px-10, py-15))

	def die(self):
		Attacker.die(self)
		effects.add(effects.Splat(self.x, self.y, self.z))

class CheapAlien(Alien):
	minicolor = 200, 0, 200
	hp0 = 10
	runspeed = 0.08
	walkspeed = 0.04
	strength = 1
	frames = {}
	fname = "bluealien.png"
	awardnumber = 1

class QuickAlien(Alien):
	minicolor = 200, 0, 200
	hp0 = 10
	runspeed = 0.15
	walkspeed = 0.08
	strength = 1
	frames = {}
	fname = "greenalien.png"
	awardnumber = 2

class StrongAlien(Alien):
	minicolor = 200, 0, 200
	hp0 = 30
	runspeed = 0.05
	walkspeed = 0.025
	strength = 3
	frames = {}
	fname = "purplealien.png"
	awardnumber = 3


class Seeker(Attacker):
	minicolor = 200, 200, 200
	runspeed = 0.08
	strength = 1
	attackrange = 3.5
	chargetime = 25
	t = 0
	hp0 = 10
	frames = {}
	fname = "seekerbot.png"
	fcounter = 0

	def attack(self, target):
		if self.t >= self.chargetime:
			self.t = 0
			effects.add(effects.BotBeam(self.x, self.y, self.z, target.x, target.y, self.z))
			target.hurt(self.strength, self)

	def update(self, scene):
		self.t += 1
		self.approachtarget(scene)
		self.walk(scene.empty_tile, self.speedfactor())
		self.setheight(3)

	def render(self, screen, looker=None):
		looker = looker or camera
		px, py = self.screenpos(looker)
		if not looker.isvisible(px, py, 100):
			return
		self.rendershadow(screen)
		if not self.frames:
			self.frames.update(images.spritesheet(self.fname, 1, 2))
		self.drawtractor(screen, looker)
		self.fcounter += 1
		a = [0,1][int(self.fcounter * 0.5) % 2]
		frame = self.frames[(0, a)]
		screen.blit(frame, (px-12, py-15))

class CheapBot(Seeker):
	runspeed = 0.08
	attackrange = 3.5
	chargetime = 40
	hp0 = 30
	strength = 2
	frames = {}
	fname = "seekerbot_blue.png"

class QuickBot(Seeker):
	runspeed = 0.2
	attackrange = 3.5
	chargetime = 20
	hp0 = 15
	strength = 2
	frames = {}
	fname = "seekerbot_green.png"

class StrongBot(Seeker):
	runspeed = 0.05
	attackrange = 3.5
	chargetime = 50
	strength = 6
	hp0 = 50
	frames = {}
	fname = "seekerbot_purple.png"


