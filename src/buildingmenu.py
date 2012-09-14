from src.menus import *
from src import network, structure, settings
from src.font import get_tiny_text
import math
import random

def abs(x):
	if x < 0: return -x
	return x

class BuildingMenu(UiScene):
	def __init__(self, playscene, building):
		UiScene.__init__(self)
		self.user_id = playscene.user_id
		self.building = building
		self.playscene = playscene
		bg = pygame.Surface((200, 180)).convert_alpha()
		bg.fill((0, 0, 0, 180))
		self.add_element(Image(100, 60, bg))
		self.initialized = False
		self.hovering = -1
		self.hover_regions = []
		
		top = 65
		left = 105
		bottom = 240 - 5
		right = 295
		if building.btype == 'hq': 
			self.init_hq(playscene, left, top, right, bottom)
		elif building.btype == 'radar':
			self.init_radar(left, top, right, bottom)
		elif building.btype == 'machinerylab':
			top = self.add_title(left, top, "Machinery Lab")
			self.init_build_bot(1, playscene, left, top, right, bottom)
		elif building.btype == 'foundry':
			top = self.add_title(left, top, "Foundry")
			self.init_build_bot(2, playscene, left, top, right, bottom)
		elif building.btype == 'sciencelab':
			top = self.add_title(left, top, "Science Lab")
			self.init_build_bot(3, playscene, left, top, right, bottom)
		elif building.btype == 'drill':
			top = self.add_title(left, top, "Drill")
		elif building.btype == 'quarry':
			top = self.add_title(left, top, "Quarry")
			self.init_quarry(left, top, right, bottom)
		elif building.btype == 'beacon':
			top = self.add_title(left, top, "Shield Generator")
			self.init_beacon(left, top, right, bottom)
		elif building.btype == 'turret':
			top = self.add_title(left, top, "Basic Turret")
			self.init_turret(1, left, top, right, bottom)
		elif building.btype == 'fireturret':
			top = self.add_title(left, top, "Fire Turret")
			self.init_turret(2, left, top, right, bottom)
		elif building.btype == 'teslaturret':
			top = self.add_title(left, top, "Tesla Turret")
			self.init_turret(3, left, top, right, bottom)
		elif building.btype == 'lazorturret':
			top = self.add_title(left, top, "Laz0r Turret")
			self.init_turret(4, left, top, right, bottom)
		elif building.btype == 'medicaltent':
			top = self.add_title(left, top, "Medical Tent")
			self.init_medtent(left, top, right, bottom)
		self.add_cancel_button(left, bottom)
	
	def init_turret(self, type, left, top, right, bottom):
		description = [[''],
			# Lines are this long:
			#"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
			
			# Basic
			["Shoots things. Good for some basic",
			 "defense."],
			
			# Fire
			["Mmmm...Fire"],
			
			# Tesla
			["Bazat!"],
			
			# Lazor
			["PEW PEW!"]
			][type]
		
		y = top
		for line in description:
			img = get_tiny_text(line)
			self.add_element(Image(left, y, img))
			y += img.get_height() + 3
	
	
	
	def add_label(self, x, y, text, size):
		img = get_text(text, (255, 255, 255), size)
		h = img.get_height()
		img = Image(x, y, img)
		self.add_element(img)
		return h
	
	def init_quarry(self, left, top, right, bottom):
		x, y = self.building.getModelXY()
		x = int(x // 1)
		y = int(y // 1)
		sx = x // 60
		sy = y // 60
		x = x % 60
		y = y % 60
		
		
		self.quarry_done = False
		self.quarry_analysis = network.send_quarry(
			self.playscene.user_id, self.playscene.password,
			str(sx) + '^' + str(sy),
			str(x) + '^' + str(y))
		
	def init_medtent(self, left, top, right, bottom):
		a = self.building.x * 3 + 13
		b = self.building.y * 7 + 4
		papercuts = a % 36
		facelifts = b % 17
		warts = (a + b) % 4
		y = top
		y += 4 + self.add_label(left, y, "Papercuts treated: " + str(papercuts), 14)
		y += 4 + self.add_label(left, y, "Facelifts performed: " + str(facelifts), 14)
		y += 4 + self.add_label(left, y, "Warts removed: " + str(warts), 14)
		
		y += 10
		y += self.add_label(left, y, "First Aid Advice of the Day:", 14) + 3
		
		
		advice = random.choice([
			['Undercooked space goats can lead to',
			 'discoloration of the stool. Do not',
			 'panic for this is temporary and',
			 '(relatively) harmless.'],
			 
			['lorem ipsum dolar sit amet consicutor',
			 'lksdfjkldja jfklaj lkj lkf'],
			 
			['lorem ipsum dolar sit amet consicutor',
			 'lksdfjkldja jfklaj lkj lkf'],
			 
			['lorem ipsum dolar sit amet consicutor',
			 'lksdfjkldja jfklaj lkj lkf'],
			
			['lorem ipsum dolar sit amet consicutor',
			 'lksdfjkldja jfklaj lkj lkf']
		])
		
		for line in advice:
			img = get_tiny_text(line)
			self.add_element(Image(left, y, img))
			y += img.get_height() + 2
		
	
	def init_radar(self, left, top, right, bottom):
		x, y = self.building.getModelXY()
		self.radar_signal = network.send_radar(self.user_id, self.playscene.password, int(x), int(y))
		self.rx = x
		self.ry = y
	
	def add_title(self, left, top, title):
		y = top
		title = get_text(title, (255, 255, 255), 24)
		self.add_element(Image(left, y, title))
		y += title.get_height() + 5
		return y
		
	def init_build_bot(self, type, playscene, left, top, right, bottom):
		pass
	
	def add_cancel_button(self, left, bottom):
		self.add_element(Button(left, bottom - 17, "Close", self.dismiss, True))
	
	def init_drill(self, playscene, left, top, right, bottom):
		pass
	
	def init_hq(self, playscene, left, top, right, bottom):
		y = top
		title = get_text("Headquarters", (255, 255, 255), 24)
		y += 5
		self.add_element(Image(left, y, title))
		y += 5 + title.get_height()
		text = get_tiny_text("Research available:")
		self.add_element(Image(left, y, text))
		y += 5 + text.get_height()
		buildings = playscene.potato.buildings_to_research()[:4]
		for building in buildings:
			x = left
			icon = playscene.toolbar.buttons['build_' + building[0]]
			self.add_element(Image(x, y, icon))
			x += icon.get_width() + 7
			img = get_tiny_text(structure.get_structure_name(building[0]))
			self.add_element(Image(x, y + 5, img))
			self.hover_regions.append((building[0], left, y, right, y + icon.get_height()))
			y += icon.get_height() + 3
		
		self.add_element(Image(left, y + 5, get_tiny_text(
			"Research will cause a mainframe reboot")))
		self.add_element(Image(left, y + 5 + 10, get_tiny_text(
			"which lowers your shields during time.")))
	
	def press_hover_region(self, arg):
		print (arg)
	
	def dismiss(self):
		self.next = self.playscene
		self.playscene.next = self.playscene
	
	def process_input(self, events, pressed):
		UiScene.process_input(self, events, pressed)
		for event in events:
			if event.type == 'key':
				if event.action == 'back' or event.action == 'action':
					if event.down:
						self.dismiss()
						break
			elif event.type == 'mousemove':
				self.hovering = -1
				i = 0
				while i < len(self.hover_regions):
					hr = self.hover_regions[i]
					if hr[1] < event.x and hr[2] < event.y and hr[3] > event.x and hr[4] > event.y:
						self.hovering = i
					i += 1
			elif event.type == 'mouseleft':
				if event.down:
					if self.hovering != -1:
						self.press_hover_region(self.hover_regions[self.hovering][0])
	
	def update(self):
		UiScene.update(self)
		self.playscene.update()
		
	
	def render_hq(self, screen):
		pass
	
	def render_radar(self, screen):
		if self.radar_signal != None and self.radar_signal.has_response():
			signal = self.radar_signal.get_response()
			if signal != None and signal.get('success', False):
				data = signal.get('neighbors', [])
				rows = []
				for datum in data:
					
					user = datum[0]
					dx = datum[1] - self.rx
					dy = datum[2] - self.ry
					distance = (dx * dx + dy * dy) ** .5
					if distance == 0: distance = 1 # don't know why this would happen
					distance = int(distance / 6) / 10.0
					direction = '-'
					
					angle = math.atan2(dy, dx) / (2 * 3.14159)
					
					
					angle = int(angle * 2 * 7.9999999)
					# my head hurts
					directions = {
						0 : "Southeast",
						1 : "South",
						2 : "South",
						3 : "Southwest",
						4 : "Southwest",
						5 : "West",
						6 : "West",
						7 : "Northwest",
						-1 : "East",
						-2 : "East",
						-3 : "Northeast",
						-4 : "Northeast",
						-5 : "North",
						-6 : "North",
						-7 : "Northwest"
					}
					direction = directions.get(angle, "")
					rows.append(get_text(str(user) + " " + str(distance) + " km " + direction, (255, 255, 255), 14)) 
				
				y = 105
				x = 100
				for row in rows:
					screen.blit(row, (x, y))
					y += row.get_height() + 5
				
			else:
				text = "Radar is broken right now. Might be the clouds."
				if signal != None:
					text = signal.get('message', text)
				img = get_text(text, (255, 0, 0), 18)
				screen.blit(img, (screen.get_width() // 2 - img.get_width() // 2, screen.get_height() // 2 - img.get_height() // 2))
		else:
			img = get_text("Scanning...", (255, 255, 255), 18)
			screen.blit(img, (screen.get_width() // 2 - img.get_width() // 2, screen.get_height() // 2 - img.get_height() // 2))

	
	def render_quarry(self, screen):
		left = 105
		top = 90
		if not self.quarry_done:
			if self.quarry_analysis.has_response():
				response = self.quarry_analysis.get_response()
				y = top
				if response != None:
					aluminum = response.get('a', 0)
					copper = response.get('c', 0)
					silicon = response.get('s', 0)
					
					y += 5 + self.add_label(left, y, settings.RESOURCE_ALUMINUM + ": " + str(aluminum) + " upm", 18)
					y += 5 + self.add_label(left, y, settings.RESOURCE_COPPER + ": " + str(copper) + " upm", 18)
					y += 5 + self.add_label(left, y, settings.RESOURCE_SILICON + ": " + str(silicon) + " upm", 18)
				else:
					self.add_label(left, y, "Information is not available", 14)
				self.quarry_done = True
			img = get_text("Analyzing Soil...", (255, 255, 255), 18)
			screen.blit(img, (left, top))
		
		if self.quarry_done:
			pass
				
	
	def render(self, screen):
		self.playscene.render(screen)
		UiScene.render(self, screen)
		
		if self.building.btype == 'radar':
			self.render_radar(screen)
		elif self.building.btype == 'hq':
			self.render_hq(screen)
		elif self.building.btype == 'quarry':
			self.render_quarry(screen)
			
		i = 0
		while i < len(self.hover_regions):
			hr = self.hover_regions[i]
			r = pygame.Rect(hr[1], hr[2], hr[3] - hr[1], hr[4] - hr[2])
			color = (80, 80, 80)
			if self.hovering == i:
				color = (0, 128, 255)
			pygame.draw.rect(screen, color, r, 1)
			i += 1