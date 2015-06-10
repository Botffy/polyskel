import logging as log
from euclid import *
from Queue import PriorityQueue
from itertools import cycle, chain, islice, izip, tee
from collections import namedtuple

import Image, ImageDraw

im = Image.new("RGB", (650, 650), "white");
draw = ImageDraw.Draw(im);

def _window(lst):
	prevs, items, nexts = tee(lst, 3)
	prevs = islice(cycle(prevs), len(lst)-1, None)
	nexts = islice(cycle(nexts), 1, None)
	return izip(prevs, items, nexts)

EdgeEvent = namedtuple("EdgeEvent", "distance intersection_point vertex_a vertex_b")
SplitEvent = namedtuple("SplitEvent", "distance, intersection_point, vertex, opposite_edge")

class _LAVertex:
	def __init__(self, point, edge_left, edge_right, lav=None):
		self.point = point
		self.edge_right = edge_right
		self.edge_left = edge_left
		self.prev = None
		self.next = None
		self.lav = lav
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
		if self.is_reflex:
			candidates = []
			for vertex in self.lav.original_polygon:
				if vertex in (self, self.prev, self.next):
					continue

				#intersect egde's line with the line of self's edge
				i = Line2(self.edge_left).intersect(Line2(vertex.edge_left))	#???
				if i is not None:
					line = Line2(self.point, i)
					bisector = Line2(i, line.v.normalize() + vertex.edge_left.v.normalize())
					b = bisector.intersect(self.bisector)
					if b is not None:
						events.append( SplitEvent(self.point.distance(b), b, self, vertex.edge_left) )

		i_prev = self.bisector.intersect(self.prev.bisector)
		i_next = self.bisector.intersect(self.next.bisector)

		if i_prev is not None:
			events.append(EdgeEvent(Line2(self.edge_left).distance(i_prev), i_prev, self.prev, self))
		if i_next is not None:
			events.append(EdgeEvent(Line2(self.edge_right).distance(i_next), i_next, self, self.next))

		return None if not events else min(events, key=lambda event: event.distance)

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
		root = _LAV.from_polygon(polygon, self)
		self._lavs = [root]

		#store original polygon for calculating split events
		self._polygon = [vertex for vertex in root]

	def unify(self, vertex_a, vertex_b, point):
		replacement =_LAVertex(point, vertex_a.edge_left, vertex_b.edge_right, vertex_a.lav)
		vertex_a.prev.next = replacement
		vertex_b.next.prev = replacement
		replacement.prev = vertex_a.prev
		replacement.next = vertex_b.next

		vertex_a.invalidate()
		vertex_b.invalidate()

		return replacement

	def split(self, event):
		result = []

		x = None
		for v in event.vertex.lav:
			if v.edge_left == event.opposite_edge:
				x = v
				break
		y = x.prev

		v1 = _LAVertex(event.intersection_point, event.vertex.edge_left, x.edge_left)
		v2 = _LAVertex(event.intersection_point, x.edge_left, event.vertex.edge_right)

		v1.lav = event.vertex.lav
		v1.prev = event.vertex.prev
		v1.next = x
		event.vertex.prev.next = v1
		x.prev = v1

		v2.prev = y
		v2.next = event.vertex.next
		event.vertex.next.prev = v2
		y.next = v2

		idx = self._lavs.index(event.vertex.lav)
		new_lav = _LAV.from_chain(v2, self)
		self._lavs.insert(idx, new_lav)

		event.vertex.invalidate()
		return (v1, v2)

	@property
	def original_polygon(self):
		return self._polygon

class _LAV:
	def __init__(self, slav):
		self.head = None
		self._slav = slav


	@classmethod
	def from_polygon(cls, polygon, slav):
		lav = cls(slav)
		for prev, point, next in _window(polygon):
			vertex = _LAVertex(point, LineSegment2(point, prev), LineSegment2(point, next), lav)
			if lav.head == None:
				lav.head = vertex
				vertex.prev = vertex.next = vertex
			else:
				vertex.next = lav.head
				vertex.prev = lav.head.prev
				vertex.prev.next = vertex
				lav.head.prev = vertex
		return lav

	@classmethod
	def from_chain(cls, head, slav):
		lav = cls(slav)
		lav.head = head
		for vertex in lav:
			vertex.lav = lav
		return lav

	@property
	def original_polygon(self):
		return self._slav.original_polygon

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
	output = []
	prioque = _EventQueue()

	for vertex in slav.original_polygon:
		prioque.put(vertex.intersect_event())

	while not prioque.empty():
		i = prioque.get()
		if isinstance(i, EdgeEvent):
			if not (i.vertex_a.is_valid and i.vertex_b.is_valid):	# or?
				continue

			if i.vertex_a.prev.prev == i.vertex_b:
				# peak event
				log.debug("%.2f Peak event at intersection %s from <%s,%s,%s>", i.distance, i.intersection_point, i.vertex_a, i.vertex_b, i.vertex_a.prev)
				i.vertex_a.invalidate()
				i.vertex_b.invalidate()
				i.vertex_a.prev.invalidate()
				output.append((i.intersection_point, i.vertex_a.point))
				draw.line(((output[-1])[0].x, (output[-1])[0].y, (output[-1])[1].x, (output[-1])[1].y), fill="red")
				output.append((i.intersection_point, i.vertex_b.point))
				draw.line(((output[-1])[0].x, (output[-1])[0].y, (output[-1])[1].x, (output[-1])[1].y), fill="red")
				output.append((i.intersection_point, i.vertex_a.prev.point))
				draw.line(((output[-1])[0].x, (output[-1])[0].y, (output[-1])[1].x, (output[-1])[1].y), fill="red")
				im.show()
			else:
				# edge event
				log.debug("%.2f Edge event at intersection %s from <%s,%s>", i.distance, i.intersection_point, i.vertex_a, i.vertex_b)
				vertex = slav.unify(i.vertex_a, i.vertex_b, i.intersection_point)
				output.append((i.intersection_point, i.vertex_a.point))
				draw.line(((output[-1])[0].x, (output[-1])[0].y, (output[-1])[1].x, (output[-1])[1].y), fill="red")
				output.append((i.intersection_point, i.vertex_b.point))
				draw.line(((output[-1])[0].x, (output[-1])[0].y, (output[-1])[1].x, (output[-1])[1].y), fill="red")
				im.show()
				prioque.put(vertex.intersect_event())
		elif isinstance(i, SplitEvent):
			if not i.vertex.is_valid:
				continue

			log.debug("%.2f Split event at intersection %s from vertex %s, for edge %s", i.distance, i.intersection_point, i.vertex, i.opposite_edge)
			vertices = slav.split(i)
			output.append((i.intersection_point, i.vertex.point))
			draw.line((output[-1][0].x, output[-1][0].y, output[-1][1].x, output[-1][1].y), fill="red")
			im.show()
			prioque.put(vertices[0].intersect_event())
			prioque.put(vertices[1].intersect_event())
	return output


if __name__ == "__main__":

	log.basicConfig(level=log.DEBUG)


	poly = [
		Point2(40,50),
		Point2(40, 520),
		Point2(625,425),
		Point2(500,325),
		Point2(635,250),
		Point2(635,10),
		Point2(250,40),
		Point2(200,200),
		Point2(100,50)
	]
	#poly = [
	#	Point2(30., 20.),
	#	Point2(30., 120.),
	#	Point2(90., 70.), #170
	#	Point2(160., 140.),
	#	Point2(178., 93.),
	#	Point2(160., 20.),
	#]


	for point, next in zip(poly, poly[1:]+poly[:1]):
		draw.line((point.x, point.y, next.x, next.y), fill=0)

	skeleton = skeletonize(poly)
	for res in skeleton:
		print res

	for line in skeleton:
		draw.line((line[0].x, line[0].y, line[1].x, line[1].y), fill="red")
	im.show();
