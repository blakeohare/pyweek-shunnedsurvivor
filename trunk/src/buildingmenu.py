from src.menus import *
from src import network
import math

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
	
	def process_input(self, events, pressed):
		for event in events:
			if event.type == 'key':
				if event.action == 'back' or event.action == 'action':
					if event.down:
						self.next = self.playscene
						self.playscene.next = self.playscene
						break
	
	def update(self):
		UiScene.update(self)
		self.playscene.update()
		
		if self.initialized == False:
			if self.building.btype == 'radar':
				x, y = self.building.getModelXY()
				self.radar_signal = network.send_radar(self.user_id, self.playscene.password, int(x), int(y))
				self.rx = x
				self.ry = y
			self.initialized = True
	
	def render(self, screen):
		self.playscene.render(screen)
		UiScene.render(self, screen)
		# This won't be centered on full screen. 
		# Will need to pass in a 400x300 transparent image and then reblit in middle
		# I'll do that if people care deeply.
		
		if self.building.btype == 'radar':
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
	