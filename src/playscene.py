import pygame
import time, random

from src import camera
from src import data
from src import network
from src import settings
from src import sprite
from src import structure
from src import util
from src import worldmap
from src import terrain
from src import battle
from src import buildingmenu
from src import effects

from src.font import get_text
from src.images import get_image


class LoadingScene:
	def __init__(self, user_id, password, sector, loc, new):
		self.next = self
		self.user_id = user_id
		self.password = password
		self.counter = 0
		self.new = new
		self.sector = sector
		self.loc = loc
		self.poll = network.send_poll(user_id, password, sector, {})
		self.potato = data.MagicPotato()
		self.loading_x = 200 - get_text("Loading..", (255, 255, 255), 22).get_width() // 2
	
	def process_input(self, events, pressed):
		pass
	
	def update(self):
		if self.poll.has_response():
			response = self.poll.get_response()
			if response.get('success', False):
				self.potato.apply_poll_data(response)
				self.poll = None
				self.next = PlayScene(self.user_id, self.password, self.potato, util.totuple(self.sector), util.totuple(self.loc), self.new)
			else:
				print("Something terrible has happened.")
				self.next = None
	
	def render(self, screen):
		self.counter += 1
		z = (self.counter // 15) % 4
		loading = get_text("Loading" + ("." * z), (255, 255, 255), 22)
		screen.fill((0, 0, 0))
		screen.blit(loading, (self.loading_x, 100))


class Curiosity:
	def __init__(self, user_id):
		self.counter = 0
		self.hq = structure.HQ(user_id, 0, 0)
		self.hq.landing_hack = True
	
	def update(self):
		self.counter += 1

	def is_done(self):
		return self.counter >= settings.fps * 10
	
	def get_hq_height(self):
		if self.counter < 100:
			return None
		if self.counter < 200:
			c = (self.counter - 100) / 2.0
			
			return int(100 - c * 2) * 1 // 5
		self.hq.landing_hack = False
		return 0
	
	def render_skycrane(self, screen):
		path = ('lander1.png', 'lander2.png')[(self.counter // 3) % 2]
		lander = get_image(path)
		y = 10
		if self.counter < 100:
			y = self.counter // 10
			
		x = screen.get_width() // 2 - lander.get_width() // 2 + 16
		
		if self.counter > 100 and self.counter < 230:
			y1 = y + 20
			y2 = self.hq.last_render_y
			if y2 != None:
				pygame.draw.rect(screen, (0, 0, 0), pygame.Rect(screen.get_width() // 2 + 16, y1, 1, y2 - y1))
		
		if self.counter > 230:
			d = self.counter - 230
			x += d * 4
			y += d * 2
		
		screen.blit(lander, (x, y))
		
		
		
	
class PlayScene:
	def __init__(self, user_id, password, potato, starting_sector, starting_xy, show_landing_sequence):
		self.curiosity = None
		if show_landing_sequence:
			self.curiosity = Curiosity(user_id)
		self.potato = potato
		self.user_id = user_id
		self.password = password
		self.next = self
		self.hq = None
		self.potato.get_user_name(user_id)
		self.show_landing_sequence = show_landing_sequence
		self.cx = starting_sector[0] * 60 + starting_xy[0]
		self.cy = starting_sector[1] * 60 + starting_xy[1]
		self.player = sprite.You(self.cx, self.cy + 1)
		self.player.lookatme()
		self.sprites = [self.player]
		for _ in range(10):
			self.sprites.append(sprite.Alien(self.cx + random.uniform(-30, 30), self.cy + random.uniform(-30, 30)))
		self.shots = []
		self.poll_countdown = 0
		self.poll = []
		self.toolbar = ToolBar()
		self.last_width = 400
		self.build_mode = None
		self.client_token = [
			util.md5(str(time.time()) + "client token for session" + str(self.user_id))[:10],
			1]
		self.battle = None
	
	def get_new_client_token(self):
		self.client_token[1] += 1
		return self.client_token[0] + '^' + str(self.client_token[1])

	def empty_tile(self, x, y):
		p = terrain.toiModel(x, y)
		return self.potato.buildings_by_coord.get(p) == None
	
	def can_walk_there(self, oldx, oldy, newx, newy):
		# underwater check
		#if terrain.height(*terrain.nearesttile(newx, newy)) <= 0: return False
		old_coord = terrain.toiModel(oldx, oldy)
		new_coord = terrain.toiModel(newx, newy)
		
		# Allow walking through buildins you're already stuck in.
		# Allows escaping from buildings you just built. 
		if old_coord == new_coord: return True
		
		return self.potato.buildings_by_coord.get(new_coord) == None
	
	def process_input(self, events, pressed):
		building_menu = False
		demolish_building = False
		if self.curiosity != None:
			pass
		else:
			direction = ''
			dx, dy = 0, 0
			if pressed['up']: dy = 1.0
			if pressed['down']: dy = -1.0
			if pressed['left']: dx = -1.0
			if pressed['right']: dx = 1.0
			
			if dx != 0 and dy != 0:
				dx *= .7071
				dy *= .7071
			
			self.player.move(dx, dy)
			# I'm moving the move logic into the sprite class so that I reuse it for aliens too. -Cosmo
			
			if self.battle:
				for event in events:
					if event.type == 'mouseleft':
						pass
					elif event.type == 'mousemove':
						pass
					elif event.type == 'key':
						if event.down and event.action == 'shoot':
							shot = self.player.shoot()
							if shot:
								self.shots.append(shot)
			else:
				for event in events:
					if event.type == 'mouseleft':
						if event.down:
							self.toolbar.click(event.x, event.y, self.last_width, self)
					elif event.type == 'mousemove':
						self.toolbar.hover(event.x, event.y, self.last_width)
					elif event.type == 'key':
						if event.down and event.action == 'debug':
							buildings = self.potato.get_all_buildings_of_player_SLOW(self.user_id)
							self.battle = battle.Battle(self.user_id, buildings, None)
						elif event.down and event.action == 'build':
							if self.build_mode != None:
								self.build_thing(self.build_mode)
							elif self.toolbar.mode == 'demolish':
								demolish_building = True
						elif event.down and event.action == 'action':
							building_menu = True
						elif event.down and event.action == 'back':
							self.toolbar.press_back()
						elif event.down and event.action == 'shoot':
							shot = self.player.shoot()
							if shot:
								self.shots.append(shot)
		you_x, you_y = terrain.toModel(self.player.x, self.player.y)
		selected_building = self.potato.get_building_selection(you_x, you_y)
		
		if building_menu and selected_building != None:
			self.next = buildingmenu.BuildingMenu(self, selected_building)
		if demolish_building and selected_building != None:
			x, y = selected_building.getModelXY()
			self.blow_stuff_up(x, y)
	
	def blow_stuff_up(self, x, y):
		col = util.floor(x)
		row = util.floor(y)
		sx = col // 60
		sy = row // 60
		x = col % 60
		y = row % 60
		network.send_demolish(
			self.user_id, self.password,
			sx, sy, x, y, self.get_new_client_token())
	
	def build_thing(self, type):
		# TODO: verify you can build this item
		sx,sy = self.get_current_sector()
		x,y = self.player.getModelXY()
		client_token = self.get_new_client_token()
		self.poll.append(
			network.send_build(
				self.user_id, self.password,
				type,
				util.floor(sx), util.floor(sy), util.floor(x % 60), util.floor(y % 60), (util.floor(sx), util.floor(sy)), self.potato.last_id_by_sector, client_token)
			)
			
	
	def get_current_sector(self):
		x,y = self.player.getModelXY()
		return (util.floor(x // 60), util.floor(y // 60))
	
	def update(self):
		if self.curiosity != None:
			self.curiosity.update()
			if self.curiosity.is_done():
				self.curiosity = None
		
		self.potato.update()
		self.poll_countdown -= 1
		if self.poll_countdown < 0 and len(self.poll) == 0:
			self.poll.append(network.send_poll(
				self.user_id, self.password,
				self.get_current_sector(),
				self.potato.last_id_by_sector))
		
		i = 0
		while i < len(self.poll):
			if self.poll[i].has_response():
				if not self.poll[i].is_error():
					self.potato.apply_poll_data(self.poll[i].get_response())
				self.poll = self.poll[:i] + self.poll[i + 1:]
			else:
				i += 1
		
		if len(self.poll) == 0 and self.poll_countdown < 0:
			self.poll_countdown = 10 * settings.fps
		worldmap.killtime(0.01)  # Helps remove jitter when exploring
		
		if self.battle != None:
			self.battle.update(self)
			if self.battle.is_complete():
				# TODO: do logic to apply results
				self.battle.hq.healfull()   # Repair the HQ after the battle
				self.battle = None
		
		for s in self.sprites: s.update(self)
		for s in self.shots:
			s.update(self)
			s.handlealiens(self.sprites)
			if self.battle:
				s.handlealiens(self.battle.aliens)
		self.sprites = [s for s in self.sprites if s.alive]
		self.shots = [s for s in self.shots if s.alive]
		
		if not self.player.alive:
			self.player.x, self.player.y = terrain.toCenterRender(self.cx, self.cy + 1)
			self.player.healall()
			self.sprites.append(self.player)
			self.player.alive = True
		effects.update()
		
	def render(self, screen):
		self.last_width = screen.get_width()
		cx = self.player.x
		cy = self.player.y
		cz = self.player.z
		camera.track(cx, cy, cz)
		structures = self.potato.get_structures_for_screen(cx, cy)
		labels = []
		
		if self.curiosity != None:
			cur = self.curiosity
			for structure in structures:
				if structure.btype == 'hq' and structure.user_id == self.user_id:
					cur.hq.x = structure.x
					cur.hq.y = structure.y
			entities = [cur.hq]
			height = cur.get_hq_height()
			if height != None:
				cur.hq.setheight(height)
			else:
				entities = []
		else:
			for structure in structures:
				if structure.btype == 'hq':
					owner_id = structure.user_id
					name = self.potato.get_user_name(owner_id)
					img = get_text(name, (255, 255, 255), 18)
					px, py = camera.screenpos(structure.x, structure.y, structure.z - 20)
					labels.append([img, px-img.get_width()//2, py])
			entities = structures + self.sprites + self.shots
			if self.battle != None:
				entities += self.battle.get_sprites()
			
		worldmap.drawscene(screen, entities + effects.effects, (cx, cy))
		
		if self.curiosity != None:
			self.curiosity.render_skycrane(screen)
		
		for label in labels:
			screen.blit(label[0], (label[1], label[2]))
		if settings.showminimap:
		    worldmap.drawminimap(screen, entities)
		mx, my = self.player.getModelXY()
		lx, ly = int(mx // 1), int(my // 1)
		coords = get_text("R: (%0.1f, %0.1f) M: (%0.1f, %0.1f) L: (%i, %i)" % (cx, cy, mx, my, lx, ly), (255, 255, 0), 16)
		screen.blit(coords, (5, screen.get_height() - 25 - coords.get_height()))
		self.toolbar.render(screen)
		self.player.drawhealth(screen)

		if self.battle != None:
			data = self.battle.bytes_stolen()
			
			if self.battle.is_computer_attacking():
				text = "Bytes lost: " + str(data)
				color = (255, 0, 0)
			else:
				text = "Bytes learned: " + str(data)
				color = (0, 100, 255)
			if data == 0:
				text = "Attack in progress"
			
			text = get_text(text, color, 22)
			x = ((screen.get_width() - text.get_width()) // 2)
			y = screen.get_height() * 4 // 5
			screen.blit(text, (x, y))
			

class ToolBar:
	def __init__(self):
		self.bg = None
		self.mode = None
		self.hovering = -1
		buttons = {}
		self.buttons = buttons
		
		ex = {
			'build_turret': (0, 8),
			'build_farm': (0, -8),
			'build_watertreatment': (0, -11)
		}
		
		bg = get_image('toolbar/button_background.png')
		
		buttons['main_build'] = get_image('toolbar/main_build.png')
		buttons['main_demolish'] = get_image('toolbar/main_demolish.png')
		buttons['main_exit'] = get_image('toolbar/main_exit.png')
		buttons['back'] = get_image('toolbar/back.png')
		
		eras = structure.get_eras()
		for era in eras.keys():
			for building in eras[era]:
				img = pygame.Surface(bg.get_size())
				img.blit(bg, (0, 0))
				b = get_image('buildings/' + building[0] + '.png')
				e = ex.get('build_' + building[0], (0, 0))
				img.blit(b, (img.get_width() // 2 - b.get_width() // 2 + e[0], e[1] + img.get_height() // 2 - b.get_height() // 2))
				buttons['build_' + building[0]] = img
		
		buttons['era_landing'] = buttons['build_medicaltent']
		buttons['era_agriculture'] = buttons['build_farm']
		
	def create_bg(self, screen):
		if self.bg == None or self.bg.get_width() != screen.get_width():
			self.bg = pygame.Surface((screen.get_width(), 35), pygame.SRCALPHA)
			self.bg.fill((0, 0, 0, 150))
	
	def find_button(self, x, y, screen_width):
		if y < 35:
			if x < 30:
				return 0
			if x > screen_width - 60:
				return 100
			x -= 30
			x = x // 60
			return x + 1
		return -1
	
	def click(self, x, y, screen_width, playscene):
		id = self.find_button(x, y, screen_width)
		if id == 0:
			self.press_back()
		elif id == 100 and self.mode == None:	
			self.press_exit(playscene)
		elif id > 0:
			self.press_button(id, playscene)
	
	def press_exit(self, playscene):
		playscene.next = None
		
	def hover(self, x, y, screen_width):
		self.hovering = self.find_button(x, y, screen_width)
		
	def press_back(self):
		if self.mode == None:
			pass # how did you get here?
		elif self.mode in ('build', 'demolish'):
			self.mode = None
		elif self.mode.startswith('era_'):
			self.mode = 'build'
		elif self.mode.startswith('build_'):
			id = self.mode.split('_')[1]
			s = structure.get_structure_by_id(id)
			self.mode = 'era_' + s[1]
		
	
	def press_button(self, column, playscene):
		playscene.build_mode = None
		if self.mode == None:
			if column == 1:
				self.mode = 'build'
			elif column == 2:
				self.mode = 'demolish'
		elif self.mode == 'build':
			if column == 1:
				self.mode = 'era_landing'
			elif column == 2:
				self.mode = 'era_agriculture'
		elif self.mode.startswith('era_'):
			era = self.mode.split('_')[1]
			structures = structure.get_eras()[era]
			index = column - 1
			if index < len(structures):
				s = structures[index]
				self.mode = 'build_' + s[0]
				playscene.build_mode = s[0]
				# TODO: verify you have resources
				# Otherwise play an error noise and a 
				# "You require more vespene gas"
				
	
	def render(self, screen):
		self.create_bg(screen)
		screen.blit(self.bg, (0, 0))
		y = 5
		if self.mode == None:
			self.draw_button('main_build', 1, screen)
			self.draw_button('main_demolish', 2, screen)
			self.draw_button('main_exit', 100, screen)
		elif self.mode == 'build':
			self.draw_button('back', 0, screen)
			self.draw_button('era_landing', 1, screen)
			self.draw_button('era_agriculture', 2, screen)
		elif self.mode == 'demolish':
			self.draw_button('back', 0, screen)
			text = get_text("Demolish", (255, 255, 255), 24)
			screen.blit(text, (40, 9))
		elif self.mode.startswith('era'):
			era = self.mode.split('_')[1]
			structures = structure.get_eras()[era]
			self.draw_button('back', 0, screen)
			i = 1
			for s in structures:
				self.draw_button('build_' + s[0], i, screen)
				i += 1
			
		elif self.mode.startswith('build_'):
			id = self.mode.split('_')[1]
			s = structure.get_structure_by_id(id)
			self.draw_button('back', 0, screen)
			text = get_text("Build " + s[7], (255, 255, 255), 24)
			screen.blit(text, (40, 9))
			button = self.buttons['build_' + id]
			r = screen.blit(button, (screen.get_width() - button.get_width() - 8, 5))
			pygame.draw.rect(screen, (0, 128, 255), r, 1)
			# TODO: show costs
			
			
	def draw_button(self, id, index, screen):
		y = 5
		hide_border = False
		if index == 0:
			x = 2
			hide_border = True
		elif index == 100:
			x = screen.get_width() - 50
		else:
			x = 40 + 60 * (index - 1)
		
		screen.blit(self.buttons[id], (x, y))
		if not hide_border:
			pygame.draw.rect(
				screen,
				(255, 255, 255) if self.hovering == index else (128, 128, 128),
				pygame.Rect(x, y, 40, 24),
				1)
			
		
