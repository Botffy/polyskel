import logging
from euclid import *
from Queue import PriorityQueue
from itertools import cycle, chain, islice, izip, tee
from collections import namedtuple


log = logging.getLogger(__name__)

def _window(lst):
	prevs, items, nexts = tee(lst, 3)
	prevs = islice(cycle(prevs), len(lst)-1, None)
	nexts = islice(cycle(nexts), 1, None)
	return izip(prevs, items, nexts)

def _cross(a, b):
	res = a.x*b.y - b.x*a.y
	return res

class _SplitEvent(namedtuple("_SplitEvent", "distance, intersection_point, vertex, opposite_edge")):
	__slots__ = ()
	def __str__(self):
		return "{} Split event @ {} from {} to {}".format(self.distance, self.intersection_point, self.vertex, self.opposite_edge)

class _EdgeEvent(namedtuple("_EdgeEvent", "distance intersection_point vertex_a vertex_b")):
	__slots__ = ()
	def __str__(self):
		return "{} Edge event @ {} between {} and {}".format(self.distance, self.intersection_point, self.vertex_a, self.vertex_b)

_OriginalEdge = namedtuple("_OriginalEdge", "edge bisector_left, bisector_right")

def _side(point, line):
	a = line.p.x
	b = line.p.y

class _LAVertex:
	def __init__(self, point, edge_left, edge_right, lav=None):
		self.point = point
		self.edge_left = edge_left
		self.edge_right = edge_right
		self.prev = None
		self.next = None
		self.lav = lav
		self._valid = True;
		self._bisector = Ray2(self.point, (edge_left.v.normalized()*-1 + edge_right.v.normalized())*(-1 if self.is_reflex else 1) )

	@property
	def bisector(self):
		return self._bisector

	@property
	def is_reflex(self):
		return (-self.edge_left.v.x * self.edge_right.v.y - self.edge_left.v.y * -self.edge_right.v.x) < 0

	def has_edge(self, edge):
		return edge.v.normalized() == self.edge_left.v.normalized() and edge.p == self.edge_left.p

	def intersect_event(self):
		events = []
		if self.is_reflex:
			candidates = []
			log.debug("looking for split candidates for vertex %s", self)
			for edge in self.lav.original_polygon:
				log.debug("\tconsidering EDGE %s", edge)
				#intersect egde's line with the line of self's edge
				i = Line2(self.edge_left).intersect(Line2(edge.edge))
				if i is not None and i != self.point:
					#locate candidate b
					line = LineSegment2(i, self.point)
					bisecvec = line.v.normalized() + edge.edge.v.normalized()
					if abs(bisecvec) == 0:
						continue
					bisector = Line2(i, bisecvec)
					b = bisector.intersect(self.bisector)
					if b is None:
						continue

					#check eligibility of b
					xleft = _cross(edge.bisector_left.v.normalized(), LineSegment2(edge.bisector_left.p, b).v.normalized())  > 0
					xright = _cross(edge.bisector_right.v.normalized(), LineSegment2(edge.bisector_right.p, b).v.normalized())  <  0
					xedge = _cross(edge.edge.v.normalized(), LineSegment2(edge.edge.p, b).v.normalized()) < 0

					if not (xleft and xright and xedge):
						log.debug("\t\tDiscarded candidate %s (%s-%s-%s)", b, xleft, xright, xedge)
						continue

					log.debug("\t\tFound valid candidate %s", b)
					candidates.append( _SplitEvent(Line2(edge.edge).distance(b), b, self, edge.edge) )
			if candidates:
				events.append( min(candidates, key=lambda event: self.point.distance(event.intersection_point)) )

		i_prev = self.bisector.intersect(self.prev.bisector)
		i_next = self.bisector.intersect(self.next.bisector)

		if i_prev is not None:
			events.append(_EdgeEvent(Line2(self.edge_left).distance(i_prev), i_prev, self.prev, self))
		if i_next is not None:
			events.append(_EdgeEvent(Line2(self.edge_right).distance(i_next), i_next, self, self.next))

		return None if not events else min(events, key=lambda event: event.distance)

	def invalidate(self):
		self.lav = None
		self._valid = False

	@property
	def is_valid(self):
		return self._valid

	def __str__(self):
		return "({0:.2f};{1:.2f})".format(self.point.x, self.point.y)

class _SLAV:
	def __init__(self, polygon):
		root = _LAV.from_polygon(polygon, self)
		self._lavs = [root]

		#store original polygon for calculating split events
		self._polygon = [_OriginalEdge(LineSegment2(vertex.prev.point, vertex.point), vertex.prev.bisector, vertex.bisector) for vertex in root]

	def unify(self, vertex_a, vertex_b, point):
		return vertex_a.lav.unify(vertex_a, vertex_b, point)

	def split(self, event):
		result = []

		x = None
		for v in event.vertex.lav:
			if v.has_edge(event.opposite_edge):
				x = v
				break
		y = x.prev

		v1 = _LAVertex(event.intersection_point, event.vertex.edge_left, LineSegment2(x.edge_left.p, x.edge_left.v))
		v2 = _LAVertex(event.intersection_point, x.edge_left, event.vertex.edge_right)

		idx = self._lavs.index(event.vertex.lav)

		v1.prev = event.vertex.prev
		v1.next = x
		event.vertex.prev.next = v1
		x.prev = v1

		v2.prev = y
		v2.next = event.vertex.next
		event.vertex.next.prev = v2
		y.next = v2

		res = []
		new_lavs = [_LAV.from_chain(v1, self), _LAV.from_chain(v2, self)]
		colors = ["orange", "blue"]
		offset = [0, 5]
		for l, col, o in zip(new_lavs, colors, offset):
			if len(l) > 2:
				self._lavs.insert(idx, l)
				res.append(l.head)
				idx += 1
			else:
				for v in l:
					v.invalidate()

		del self._lavs[idx]

		event.vertex.invalidate()
		return res

	@property
	def original_polygon(self):
		return self._polygon

class _LAV:
	def __init__(self, slav):
		self.head = None
		self._slav = slav
		self._len = 0


	@classmethod
	def from_polygon(cls, polygon, slav):
		lav = cls(slav)
		for prev, point, next in _window(polygon):
			lav._len += 1
			vertex = _LAVertex(point, LineSegment2(prev, point), LineSegment2(point, next), lav)
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
			lav._len += 1
			vertex.lav = lav
		return lav

	@property
	def original_polygon(self):
		return self._slav.original_polygon

	def unify(self, vertex_a, vertex_b, point):
		replacement =_LAVertex(point, vertex_a.edge_left, vertex_b.edge_right, vertex_a.lav)

		if self.head in [vertex_a, vertex_b]:
			self.head = replacement

		vertex_a.prev.next = replacement
		vertex_b.next.prev = replacement
		replacement.prev = vertex_a.prev
		replacement.next = vertex_b.next

		vertex_a.invalidate()
		vertex_b.invalidate()
		return replacement

	def __len__(self):
		return self._len

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

	for vertex in slav._lavs[0]: # fixme
		prioque.put(vertex.intersect_event())

	while not prioque.empty():
		i = prioque.get()
		if isinstance(i, _EdgeEvent):
			if not i.vertex_a.is_valid or not i.vertex_b.is_valid:
				continue

			if i.vertex_a.prev.prev == i.vertex_b:
				# peak event
				log.info("%.2f Peak event at intersection %s from <%s,%s,%s>", i.distance, i.intersection_point, i.vertex_a, i.vertex_b, i.vertex_a.prev)
				i.vertex_a.invalidate()
				i.vertex_b.invalidate()
				i.vertex_a.prev.invalidate()
				output.append((i.intersection_point, i.vertex_a.point))
				output.append((i.intersection_point, i.vertex_b.point))
				output.append((i.intersection_point, i.vertex_a.prev.point))
			else:
				# edge event
				log.info("%.2f Edge event at intersection %s from <%s,%s>", i.distance, i.intersection_point, i.vertex_a, i.vertex_b)
				vertex = slav.unify(i.vertex_a, i.vertex_b, i.intersection_point)
				output.append((i.intersection_point, i.vertex_a.point))
				output.append((i.intersection_point, i.vertex_b.point))
				prioque.put(vertex.intersect_event())
		elif isinstance(i, _SplitEvent):
			if not i.vertex.is_valid:
				continue

			log.info("%.2f Split event at intersection %s from vertex %s, for edge %s", i.distance, i.intersection_point, i.vertex, i.opposite_edge)
			vertices = slav.split(i)
			output.append((i.intersection_point, i.vertex.point))
			for v in vertices:
				prioque.put(v.intersect_event())
	return output


if __name__ == "__main__":
	import Image, ImageDraw

	im = Image.new("RGB", (650, 650), "white");
	draw = ImageDraw.Draw(im);

	logging.basicConfig(level=logging.DEBUG)

	examples = {
		'the sacred polygon': [
			Point2(40,50),
			Point2(40, 520),
			Point2(625,425),
			Point2(500,325),
			Point2(635,250),
			Point2(635,10),
			Point2(250,40),
			Point2(200,200),
			Point2(100,50)
		],
		'simple': [
			Point2(30., 20.),
			Point2(30., 120.),
			Point2(90., 70.), #170
			Point2(160., 140.),
			Point2(178., 93.),
			Point2(160., 20.),
		],
		"multiply split": [
			Point2(40., 60.),
			Point2(100., 310.),
			Point2(180., 180.),
			Point2(260., 310.),
			Point2(340., 150.),
			Point2(420., 310.),
			Point2(500., 180.),
			Point2(580., 310.),
			Point2(640., 60.)
		],
		'rectangle': [
			Point2(40., 40.),
			Point2(40., 310.),
			Point2(520., 310.),
			Point2(520., 40.)
		],
		"iron cross": [	# doesn't work
			Point2(100., 50),
			Point2(300., 50),
			Point2(250., 150.),
			Point2(350., 100.),
			Point2(350., 350.),
			Point2(50., 350.),
			Point2(50., 100.),
			Point2(150., 150.)
		]
	}

	poly = examples["iron cross"]
	for point, next in zip(poly, poly[1:]+poly[:1]):
		draw.line((point.x, point.y, next.x, next.y), fill=0)

	skeleton = skeletonize(poly)
	for res in skeleton:
		print res

	for line in skeleton:
		draw.line((line[0].x, line[0].y, line[1].x, line[1].y), fill="red")
	im.show();
