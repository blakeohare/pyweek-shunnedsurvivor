import random, pygame, time, math
from collections import defaultdict
from src import camera, settings, images


# Python 2.5 shim
try:
    next
except NameError:
    def next(i):
        i.next()

# seed the RNG for reproducible noise map
try:
    random.seed(settings.noiseseed, version = 1)
except TypeError:
    random.seed(settings.noiseseed)
assert random.random() == settings.rngcheck, "Something wrong with the random number generation. Aborting!"
# Generate the noise map to be used for all terrain
noisemap = [[(random.random() * 2 - 1) * settings.tscale for x in range(settings.nmapsize)]
               for y in range(settings.nmapsize)]
noisemap = [row + row[0:1] for row in noisemap]
noisemap += noisemap[0:1]

# Reference implementation - slow
def noisevalue(x, y):
    x %= settings.nmapsize
    y %= settings.nmapsize
    tx, ty = x - int(x), y - int(y)
    x, y = int(x), int(y)
    return ((noisemap[x][y] * (1-tx) + noisemap[x+1][y] * tx) * (1-ty) + 
            (noisemap[x][y+1] * (1-tx) + noisemap[x+1][y+1] * tx) * ty)

# Reference implementation - slow
def height0(x, y):
    h = -settings.sealevel
    for f in settings.tfactors:
        h += noisevalue(x*f*settings.tf0, y*f*settings.tf0) / f
    if h > 0: h -= min(h/2, 20)
    return int(h)


# Convert between axis-aligned (render) coordinates and tilted (model) coordinates
def toModel(x, y):
    return (x-y)/2, (-x-y)/2
def toRender(X, Y):
    return X-Y, -X-Y


def hcolor(h, gx, gy):
    a = 0.8 + 0.08 * gx
    if h <= 0: r = (0,0,100)
    elif h < 4: r = (160,160,80)
    elif h < 16: r = (90,90,0)
    elif h < 25: r = (100,50,0)
    elif h < 40: r = (100,100,100)
    else: r = (140,140,140)
    return [min(max(int(x*a),0),255) for x in r]

# This is a set of cached values to speed up height calculations - don't worry about it.
dpcache, dpmin, dpmax = {}, 0, 0
def setdp(xx):
    xs = [xx*f*settings.tf0 % settings.nmapsize for f in settings.tfactors]
    dpcache[xx] = [(int(x), x - int(x)) for x in xs]
setdp(0)
def dpextend(x0, x1):
    global dpmin, dpmax
    while dpmin > x0:
        dpmin -= 1
        setdp(dpmin)
    while dpmax < x1:
        dpmax += 1
        setdp(dpmax)

pcs = settings.parcelsize
class Parcel(object):
    def __init__(self, x0, y0):
        self.x0, self.y0 = x0, y0
        self.ready = False
        self.compiter = self.compute()

    def compute(self):
        dpextend(min(self.x0, self.y0) - 4, max(self.x0, self.y0) + pcs + 4)
        yield
        # Determine heights for corners
        self.h = {}
        for y in range(self.y0 - 3, self.y0 + pcs + 5):
            for x in range(self.x0 - 3 + y % 2, self.x0 + pcs + 5, 2):
                # TODO: easy integer map to actual h values
                h = -settings.sealevel
                for f, (xx, tx), (yy, ty) in zip(settings.tfactors, dpcache[x], dpcache[y]):
                    h += ((noisemap[xx][yy] * (1-tx) + noisemap[xx+1][yy] * tx) * (1-ty) + 
                        (noisemap[xx][yy+1] * (1-tx) + noisemap[xx+1][yy+1] * tx) * ty) / f
                if h > 0: h -= min(h/2, 20)
                self.h[(x, y)] = max(int(h), 0)
            yield
        self.hcorners = {}
        self.hcmax = {}
        self.grad = {}
        # Determine heights for tiles
        for y in range(self.y0 - 2, self.y0 + pcs + 4):
            for x in range(self.x0 - 2 + y % 2, self.x0 + pcs + 4, 2):
                hs = self.h[(x-1,y)], self.h[(x,y-1)], self.h[(x+1,y)], self.h[(x,y+1)]
                self.hcorners[(x,y)] = hs
                self.hcmax[(x,y)] = max(hs)
                self.h[(x,y)] = sum(hs)/4.0
                self.grad[(x,y)] = hs[2]-hs[0], hs[3]-hs[1]
            yield
        self.ready = True

    def getheight(self, x, y):
        if self.compiter:
            for _ in self.compiter:
                pass
        if (x,y) in self.h: return self.h[(x, y)]
        X, Y = (x + y) / 2, (-x + y) / 2
        iX, iY = int(X//1), int(Y//1)
        ix, iy = iX - iY, iX + iY
        tX, tY = X - iX, Y - iY
        return ((self.h[(ix,iy)] * (1-tX) + self.h[(ix+1,iy+1)] * tX) * (1-tY) + 
                (self.h[(ix-1,iy-1)] * (1-tX) + self.h[(ix,iy+2)] * tX) * tY)

    def complete(self):
        if self.compiter:
            for _ in self.compiter:
                pass
            self.compiter = None

    # x and y must be integers
    def getiheight(self, x, y):
        self.complete()
        return self.h[(x, y)]

    def getigrad(self, x, y):
        self.complete()
        return self.grad[(x, y)]

    def getihcmax(self, x, y):
        self.complete()
        return self.hcmax[(x, y)]

    def getihcorners(self, x, y):
        self.complete()
        return self.hcorners[(x, y)]


class parceldict(defaultdict):
    def __missing__(self, key):
        x, y = key
        ret = self[key] = Parcel(x*pcs, y*pcs)
        return ret
parcels = parceldict()
parcelq = []

def dumpparcels():
    import cPickle
    ks = list(parcels)
    for k in ks:
        if parcels[k].compiter:
            del parcels[k]
    cPickle.dump(parcels, open("parcel-dump-test.pkl", "wb"))

def nearesttile(x, y):
    X, Y = (x + y) / 2, (-x + y) / 2
    iX, iY = int((X+0.5)//1), int((Y+0.5)//1)
    return iX - iY, iX + iY
def height(x, y):
    return parcels[(int(x//pcs), int(y//pcs))].getheight(x, y)
def iheight(x, y):
    return parcels[(int(x//pcs), int(y//pcs))].getiheight(int(x//1), int(y//1))
# maximum height of any of this tile's 4 corners
def ihcmax(x, y):
    return parcels[(int(x//pcs), int(y//pcs))].getihcmax(int(x//1), int(y//1))
# heights of the four corners
def ihcorners(x, y):
    return parcels[(int(x//pcs), int(y//pcs))].getihcorners(int(x//1), int(y//1))
def igrad(x, y):
    return parcels[(int(x//pcs), int(y//pcs))].getigrad(int(x//1), int(y//1))
def addparcels(x, y):
    x0, y0 = int(x // pcs), int(y // pcs)
    for x in range(x0-3, x0+4):
        for y in range(y0-3, y0+4):
            if (x,y) not in parcels:
                p = Parcel(x*pcs,y*pcs)
                parcels[(x,y)] = p
                parcelq.append(p)
def thinkparcels(dt=0):
    x0, y0 = int(camera.x0 / settings.tilex // pcs), int(-camera.y0 / settings.tiley // pcs)
    if not parcelq:
        return 0
    tf = time.time() + dt if dt else 0
    n = 0
    while True:
        n += 1
        topop = False
        if parcelq[0].compiter:
            try:
                next(parcelq[0].compiter)
            except StopIteration:
                topop = True
        else:
            topop = True
        if topop:
            parcelq.pop(0)
            parcelq.sort(key = lambda p: (x0 - p.x0)**2 + (y0-p.y0)**2)
        if time.time() > tf or not parcelq:
            return n

def highlighttile(surf, x, y, looker=None):
    h, gx, gy, ps = tileinfo(x, y, looker)
    x0, x1 = min(x for x,y in ps), max(x for x,y in ps)
    y0, y1 = min(y for x,y in ps), max(y for x,y in ps)
    s = pygame.Surface(((x1-x0+1), (y1-y0+1))).convert_alpha()
    s.fill((0,0,0,0))
    ps = [(x-x0,y-y0) for x,y in ps]
    pygame.draw.polygon(s, (255, 0, 0, 50), ps)
    pygame.draw.lines(s, (255, 0, 0, 100), True, ps, 1)
    surf.blit(s, (x0,y0))

def tileinfo(x, y, looker=None):
    looker = looker or camera
    x, y = int(x//1), int(y//1)
    h = iheight(x, y)
    gx, gy = igrad(x, y)
    ps = []
    ps.append(looker.screenpos(x-1, y, iheight(x-1, y)))
    ps.append(looker.screenpos(x, y-1, iheight(x, y-1)))
    ps.append(looker.screenpos(x+1, y, iheight(x+1, y)))
    ps.append(looker.screenpos(x, y+1, iheight(x, y+1)))
    return h, gx, gy, ps

minimaps = {}
def minichunk(x0, y0):
    if (x0, y0) not in minimaps:
#        t0 = time.time()
        a = settings.mchunksize
        s = pygame.Surface((a, a))
#        arr = pygame.surfarray.pixels3d(s)
        for y in range(a):
            for x in range(-1,a):
                if (x + y) % 2: continue
                c = hcolor(iheight(x0*a+x, y0*a+(a-1-y)), 0, 0)
                s.set_at((x, y), c)
                s.set_at((x+1, y), c)
#                arr[x,y,:] = hcolor(iheight(x0*a+x, y0*a+(a-1-y)), 0, 0)
        minimaps[(x0,y0)] = s.convert()
#        print x0, y0, time.time() - t0
    return minimaps[(x0,y0)]
# return a minimap centered at (x, y) with size (w, h)
def minimap(x, y, w, h):
    s = pygame.Surface((w, h)).convert()
    a = settings.mchunksize
    x0 = int((x-w//2)//a)
    x1 = int((x+w//2)//a)
    y0 = int((y-h//2)//a)
    y1 = int((y+h//2)//a)
    for ay in range(y0,y1+1):
        for ax in range(x0,x1+1):
            s.blit(minichunk(ax,ay), (ax*a - (x-w//2), (-ay-1)*a + y + h//2))
    return s
def dumpmap():
    if not minimaps: return
    x0 = min(x for x,y in minimaps)
    x1 = max(x for x,y in minimaps) + 1
    y0 = min(y for x,y in minimaps)
    y1 = max(y for x,y in minimaps) + 1
    a = settings.mchunksize
    s = pygame.Surface((a*(x1-x0), a*(y1-y0)))
    s.fill((0,0,0))
    for x in range(x0, x1):
        for y in range(y0, y1):
            if (x,y) not in minimaps: continue
            s.blit(minimaps[(x,y)], (a*(x-x0), a*(y1-1-y)))
    pygame.image.save(s, "map.png")
def thinkminimap(dt=0):
    tf = time.time() + dt if dt else 0
    tf = 0
    n = 0
    x0 = int(camera.x0 / settings.tilex // settings.mchunksize)
    y0 = int(-camera.y0 / settings.tiley // settings.mchunksize)
    for dx in range(-4, 5):
        for dy in range(-4, 5):
            if (x0+dx, y0+dy) not in minimaps:
                minichunk(x0+dx, y0+dy)
                n += 1
            if time.time() > tf:
                return n

# A cached version of the landscape, for fast blitting
class Panel(object):
    def __init__(self, x0, y0):
        self.x0 = x0
        self.y0 = y0
        self.w, self.h = settings.panelw, settings.panelh
        self.ready = False
        self.compiter = self.compute()

    def screenpos(self, x, y, z):
        return int(x * settings.tilex - self.x0 * self.w), int(-self.y0 * self.h - y * settings.tiley - z * settings.tilez)

    def putterrain(self, surf, h, g, ps):
        if not settings.usetgradient or h <= 0:
            return pygame.draw.polygon(surf, hcolor(h, g, 0), ps)
        tgrad = images.get_image("terrain-gradient.png")
        xs, ys = zip(*ps)
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        xs = [x-x0 for x in xs]
        ys = [y-y0 for y in ys]
        xc = 200 + int(g * 25)
        yc = 360 - int(h * 10)
        w, h = x1-x0+1, y1-y0+1
        s = pygame.Surface((w, h)).convert()
        mask = pygame.Surface((w, h)).convert()
        mask.fill((255,0,255))
        mask.set_colorkey((0,0,0))
        pygame.draw.polygon(mask, (0,0,0), [(x-x0,y-y0) for x,y in ps])
        s.blit(tgrad, (-xc, -yc))
        s.blit(mask, (0,0))
        s.set_colorkey((255,0,255))
        surf.blit(s, (x0, y0))

    def compute(self):
        self.surf = pygame.Surface((self.w, self.h)).convert()
        self.lines = bool(settings.tbcolor)
        if self.lines:
            lsurf = pygame.Surface((self.w, self.h)).convert_alpha()
            lsurf.fill((0,0,0,0))
        x0 = int(self.x0 * self.w / settings.tilex // 1) - 1
        x1 = int((self.x0 + 1) * self.w / settings.tilex // 1) + 2
        y0 = int(-(self.y0 + 1) * self.h / settings.tiley // 1)
        onscreen, y = True, y0
        while onscreen:
            onscreen = False
            for x in range(x0, x1):
                if (x + y) % 2: continue
                h, gx, gy, ps = tileinfo(x, y, self)
                self.putterrain(self.surf, h, gx, ps)
                if self.lines:
                    pygame.draw.lines(lsurf, settings.tbcolor, False, ps[0:3], 1)
                if max(py for px, py in ps) > 0:
                    onscreen = True
                yield
            y += 1
        onscreen, y = True, y0 - 1
        while onscreen:
            onscreen = False
            for x in range(x0, x1):
                if (x + y) % 2: continue
                h, gx, gy, ps = tileinfo(x, y, self)
                self.putterrain(self.surf, h, gx, ps)
                if self.lines:
                    pygame.draw.lines(lsurf, settings.tbcolor, False, ps[0:3], 1)
                if min(py for px, py in ps) < self.h:
                    onscreen = True
                yield
            y -= 1
        if self.lines:
            self.surf.blit(lsurf, (0,0))
        self.ready = True

    def getsurf(self):
        if self.compiter:
            for _ in self.compiter:
                pass
        return self.surf

panels = {}
panelq = []
def drawpanels(surf, x0, y0, w, h):
    for x in range(int(x0 // settings.panelw), int((x0 + w) // settings.panelw) + 1):
        for y in range(int(y0 // settings.panelh), int((y0 + h) // settings.panelh) + 1):
            if (x,y) not in panels:
                panels[(x,y)] = Panel(x, y)
            s = panels[(x, y)].getsurf()
            surf.blit(s, (x * settings.panelw - x0, y * settings.panelh - y0))
def addpanels(x, y):
    x0, y0 = int(x // settings.panelw), int(y // settings.panelh)
    for x in range(x0-2, x0+3):
        for y in range(y0-2, y0+3):
            if (x,y) not in panels:
                p = Panel(x,y)
                panels[(x,y)] = p
                panelq.append(p)
def thinkpanels(dt=0):
    x0, y0 = int(camera.x0 // settings.panelw), int(camera.y0 // settings.panelh)
    if not panelq:
        return 0
    tf = time.time() + dt if dt else 0
    n = 0
    while True:
        n += 1
        topop = False
        if panelq[0].compiter:
            try:
                next(panelq[0].compiter)
            except StopIteration:
                topop = True
        else:
            topop = True
        if topop:
            panelq.pop(0)
            panelq.sort(key = lambda p: (x0 - p.x0) ** 2 + (y0 - p.y0) ** 2)
        if time.time() > tf or not panelq:
            return n

# Call this function when you've got a little time to kill and you might as well
# be doing something useful.
def killtime(dt=0):
    addpanels(camera.x0, camera.y0)
    addparcels(camera.x0 / settings.tilex, -camera.y0 / settings.tiley)
    tf = time.time() + dt
    n = 0
    while time.time() < tf:
        dt = tf - time.time()
        m = thinkparcels(0.5 * dt)
        m += thinkpanels(0.4 * dt) 
        m += thinkminimap(0.1 * dt)
        if not m: break
        n += m
    return n


# How far do you have to go along this track before you hit water?
def dtrack(x0, y0, track, dmax = 100):
    n = 0
    x, y = x0, y0
    while True:
        for dx, dy in track:
            n += 1
            x += dx
            y += dy
            if iheight(x, y) <= 0 or n >= dmax:
                return n

def validstart(x, y):
    x, y = int(x//1), int(y//1)
    # send out feelers in a variety of directions until they hit water
    if iheight(x, y) < 0: return False
    waterhits = []
    for a,b,c,d in [(1,0,0,1), (0,1,-1,0), (-1,0,0,-1), (0,-1,1,0)]:
        dx, dy = (b,d), (a,c)
        waterhits.append(dtrack(x, y, [dx]))
        waterhits.append(dtrack(x, y, [dx,dy]))
        waterhits.append(dtrack(x, y, [dx,dx,dx,dy]))
    ws = sorted(waterhits)[3:-3]
    return ws[0] > 1 and ws[3] > 5 and ws[-3] > 40 and ws[-1] > 60

def choosevalidstart():
    random.seed()
    print("Choosing starting location....")
    while True:
        x = random.randint(-2000, 2000)
        y = random.randint(-2000, 2000)
        if validstart(x, y):
            break
    print("(%s,%s) looks like a good place to start...." % (x, y))
    return x, y

# Obviously doesn't take into account whether there's anything already built there
def canbuildhere(x, y):
    return (x + y) % 2 == 0 and iheight(x, y) > 0

def drawscene(screen, entities, cursortile = None):
    screen.fill((0,0,0))
    drawpanels(screen, camera.x0//1-settings.sx//2, camera.y0//1-settings.sy // 2, settings.sx, settings.sy)
    if cursortile:
        cx, cy = cursortile
        highlighttile(screen, cx, cy)
    esort = sorted(entities, key = lambda e: -e.y)
    for entity in esort:
        entity.render(screen)

def drawminimap(screen):
    a = settings.minimapsize
    pygame.draw.rect(screen, (255, 255, 255), (10, 10, a + 2, a + 2))
    screen.blit(minimap(int(camera.x0 // settings.tilex), -int(camera.y0 // settings.tiley), a, a), (11, 11))


if __name__ == "__main__":
    import pygame
    from pygame import *
    screen = display.set_mode((800, 600))
    display.set_caption("Don't worry, the real game will be much faster at this.")
    for y in range(600):
        for x in range(800):
            h = height(x, y)
            c = hcolor(h)
            screen.set_at((x, y), c)
        draw.rect(screen, (255, 255, 255), (100, 100, 20, 30), 1)
        pygame.display.flip()
        if any(event.type in (KEYDOWN, QUIT) for event in pygame.event.get()):
            exit()
    while not any(event.type in (KEYDOWN, QUIT) for event in pygame.event.get()):
        pass
    image.save(screen, "map-example.png")

