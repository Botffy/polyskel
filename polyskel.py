import logging as log
from euclid import *
from Queue import PriorityQueue
from itertools import cycle, chain, islice, izip, tee
from collections import namedtuple

def _window(lst):
	prevs, items, nexts = tee(lst, 3)
	prevs = islice(cycle(prevs), len(lst)-1, None)
	nexts = islice(cycle(nexts), 1, None)
	return izip(prevs, items, nexts)

Event = namedtuple("Event", "distance intersection_point vertex_a vertex_b")

class _LAVertex:
	def __init__(self, point, edge_left, edge_right):
		self.point = point
		self.edge_right = edge_right
		self.edge_left = edge_left
		self.prev = None
		self.next = None
		self._bisector = Ray2(self.point, edge_left.v.normalize() + edge_right.v.normalize())
		self._valid = True;

	@property
	def bisector(self):
		return self._bisector

	def intersect_event(self):
		i_prev = self.bisector.intersect(self.prev.bisector)
		i_next = self.bisector.intersect(self.next.bisector)

		if i_prev is None and i_next is None:
			return None

		prevdist = self.point.distance(i_prev) if i_prev is not None else float("inf")
		nextdist = self.point.distance(i_next) if i_next is not None else float("inf")

		if prevdist < nextdist:
			event = Event(self.point.distance(i_prev), i_prev, self.prev, self)
		else:
			event = Event(self.point.distance(i_next), i_next, self, self.next)
		return event

	def invalidate(self):
		self._valid = False

	@property
	def is_valid(self):
		return self._valid

	def __str__(self):
		return "({0};{1})".format(self.point.x, self.point.y)

	def __eq__(self, other):
		if other is None:
			return False
		return self.point == other.point


class _LAV:
	def __init__(self, polygon):
		self.head = None

		for prev, point, next in _window(polygon):
			vertex = _LAVertex(point, LineSegment2(point, prev), LineSegment2(point, next))
			if self.head == None:
				self.head = vertex
				vertex.prev = vertex.next = vertex
			else:
				vertex.next = self.head
				vertex.prev = self.head.prev
				vertex.prev.next = vertex
				self.head.prev = vertex

	def unify(self, vertex_a, vertex_b, point):
		replacement =_LAVertex(point, vertex_a.edge_left, vertex_b.edge_right)
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
	lav = _LAV(polygon)
	output = []
	prioque = _EventQueue()

	for vertex in lav:
		prioque.put(vertex.intersect_event())

	while not prioque.empty():
		i = prioque.get()

		if not (i.vertex_a.is_valid or i.vertex_b.is_valid):
			continue
		else:
			if i.vertex_a.prev.prev == i.vertex_b:
				# peak event
				log.debug("Peak event at intersection %s from <%s,%s,%s>", i.intersection_point, i.vertex_a, i.vertex_b, i.vertex_a.prev)
				output.append((i.intersection_point, i.vertex_a.point))
				output.append((i.intersection_point, i.vertex_b.point))
				output.append((i.intersection_point, i.vertex_a.prev.point))
				break
			else:
				# edge event
				log.debug("Edge event at intersection %s from <%s,%s>", i.intersection_point, i.vertex_a, i.vertex_b)
				vertex = lav.unify(i.vertex_a, i.vertex_b, i.intersection_point)
				output.append((i.intersection_point, i.vertex_a.point))
				output.append((i.intersection_point, i.vertex_b.point))
				prioque.put(vertex.intersect_event())
	return output


if __name__ == "__main__":
	import Image, ImageDraw

	log.basicConfig(level=log.DEBUG)

	poly = [
		Point2(30., 20.),
		Point2(30., 120.),
		Point2(90., 70.),
		Point2(160., 140.),
		Point2(178., 93.),
		Point2(160., 20.),
	]

	im = Image.new("RGB", (200, 200), "white");
	draw = ImageDraw.Draw(im);

	for point, next in zip(poly, poly[1:]+poly[:1]):
		draw.line((point.x, point.y, next.x, next.y), fill=0)

	skeleton = skeletonize(poly)
	for res in skeleton:
		print res

	for line in skeleton:
		draw.line((line[0].x, line[0].y, line[1].x, line[1].y), fill="red")
	im.show();
