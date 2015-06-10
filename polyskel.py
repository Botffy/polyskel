import logging as log
from euclid import *
from Queue import PriorityQueue
from itertools import cycle, chain, islice, izip, tee
from collections import namedtuple

import Image, ImageDraw

im = Image.new("RGB", (600, 600), "white");
draw = ImageDraw.Draw(im);

def _window(lst):
	prevs, items, nexts = tee(lst, 3)
	prevs = islice(cycle(prevs), len(lst)-1, None)
	nexts = islice(cycle(nexts), 1, None)
	return izip(prevs, items, nexts)

EdgeEvent = namedtuple("EdgeEvent", "distance intersection_point vertex_a vertex_b")
SplitEvent = namedtuple("SplitEvent", "distance, intersection_point, vertex")

class _LAVertex:
	def __init__(self, point, edge_left, edge_right, slav=None):
		self.point = point
		self.edge_right = edge_right
		self.edge_left = edge_left
		self.prev = None
		self.next = None
		self._slav = slav
		self._bisector = Ray2(self.point, (edge_left.v.normalize() + edge_right.v.normalize())*(-1 if self.is_reflex else 1) )
		self._valid = True;

	@property
	def bisector(self):
		return self._bisector

	@property
	def is_reflex(self):
		return (self.edge_left.v.x * self.edge_right.v.y - self.edge_left.v.y * self.edge_right.v.x) < 0

	def intersect_event(self):
		events = []
		if self.is_reflex and self in self._slav.polygon:
			for vertex in self._slav.polygon:
				if vertex in (self, self.prev, self.next):
					continue

				#intersect egde's line with the line of self's edge
				i = Line2(self.edge_left).intersect(Line2(vertex.edge_left))
				if i is not None:
					line = Line2(self.point, i)
					bisector = Line2(i, line.v.normalize() + vertex.edge_left.v.normalize())
					#draw.line( (bisector.p.x-bisector.v.x*400, bisector.p.y-bisector.v.y*400, bisector.p.x+bisector.v.x*400, bisector.p.y+bisector.v.y*400), fill="purple" )
					b = bisector.intersect(self.bisector)
					if b is not None:
						events.append( SplitEvent(self.point.distance(b), b, self) )

		if self.is_reflex:
			return None

		i_prev = self.bisector.intersect(self.prev.bisector)
		i_next = self.bisector.intersect(self.next.bisector)

		if i_prev is None and i_next is None:
			return None

		prevdist = self.point.distance(i_prev) if i_prev is not None else float("inf")
		nextdist = self.point.distance(i_next) if i_next is not None else float("inf")

		if prevdist < nextdist:
			event = EdgeEvent(self.point.distance(i_prev), i_prev, self.prev, self)
		else:
			event = EdgeEvent(self.point.distance(i_next), i_next, self, self.next)
		return event

	def invalidate(self):
		self._valid = False

	@property
	def is_valid(self):
		return self._valid

	def __str__(self):
		return "({0:.2f};{1:.2f})".format(self.point.x, self.point.y)

	def __eq__(self, other):
		if other is None:
			return False
		return self.point == other.point

class _SLAV:
	def __init__(self, polygon):
		self._lav = _LAV(polygon, self)

		#store original polygon for calculating split events
		self.polygon = [vertex for vertex in self._lav]

	@property
	def lav(self):
		return _lav

class _LAV:
	def __init__(self, polygon, slav):
		self.head = None
		self._slav = slav

		for prev, point, next in _window(polygon):
			vertex = _LAVertex(point, LineSegment2(point, prev), LineSegment2(point, next), self._slav)
			if self.head == None:
				self.head = vertex
				vertex.prev = vertex.next = vertex
			else:
				vertex.next = self.head
				vertex.prev = self.head.prev
				vertex.prev.next = vertex
				self.head.prev = vertex

	def unify(self, vertex_a, vertex_b, point):
		replacement =_LAVertex(point, vertex_a.edge_left, vertex_b.edge_right, self._slav)
		vertex_a.prev.next = replacement
		vertex_b.next.prev = replacement
		replacement.prev = vertex_a.prev
		replacement.next = vertex_b.next

		vertex_a.invalidate()
		vertex_b.invalidate()

		return replacement

	def __iter__(self):
		cur = self.head
		while True:
			yield cur
			cur = cur.next
			if cur == self.head:
				raise StopIteration

	def _show(self):
		cur = self.head
		while True:
			print cur
			cur = cur.next
			if cur == self.head:
				break

class _EventQueue(PriorityQueue):
	def put(self, value):
		if value is not None:
			PriorityQueue.put(self, value)

def skeletonize(polygon):
	slav = _SLAV(polygon)
	lav = slav._lav
	output = []
	prioque = _EventQueue()

	for vertex in lav:
		prioque.put(vertex.intersect_event())
		draw.line((vertex.bisector.p.x, vertex.bisector.p.y, vertex.bisector.p.x+vertex.bisector.v.x*100, vertex.bisector.p.y+vertex.bisector.v.y*100), fill="blue")

	while not prioque.empty():
		i = prioque.get()
		if not (i.vertex_a.is_valid or i.vertex_b.is_valid):
			continue
		elif isinstance(i, EdgeEvent):
			if i.vertex_a.prev.prev == i.vertex_b:
				# peak event
				log.debug("%.2f Peak event at intersection %s from <%s,%s,%s>", i.distance, i.intersection_point, i.vertex_a, i.vertex_b, i.vertex_a.prev)
				output.append((i.intersection_point, i.vertex_a.point))
				output.append((i.intersection_point, i.vertex_b.point))
				output.append((i.intersection_point, i.vertex_a.prev.point))
				break
			else:
				# edge event
				log.debug("%.2f Edge event at intersection %s from <%s,%s>", i.distance, i.intersection_point, i.vertex_a, i.vertex_b)
				vertex = lav.unify(i.vertex_a, i.vertex_b, i.intersection_point)
				output.append((i.intersection_point, i.vertex_a.point))
				output.append((i.intersection_point, i.vertex_b.point))
				prioque.put(vertex.intersect_event())
	return output


if __name__ == "__main__":

	log.basicConfig(level=log.DEBUG)


	poly = [
		Point2(50,20),
		Point2(50, 340),
		Point2(117,200),
		Point2(260,340),
		Point2(400,200),
		Point2(540,340),
		Point2(540,20)
	]
	#poly = [
	#	Point2(30., 20.),
	#	Point2(30., 120.),
	#	Point2(90., 70.),
	#	Point2(160., 140.),
	#	Point2(178., 93.),
	#	Point2(160., 20.),
	#]


	for point, next in zip(poly, poly[1:]+poly[:1]):
		draw.line((point.x, point.y, next.x, next.y), fill=0)

	skeleton = skeletonize(poly)
	#for res in skeleton:
		#print res

	for line in skeleton:
		draw.line((line[0].x, line[0].y, line[1].x, line[1].y), fill="red")
	im.show();
