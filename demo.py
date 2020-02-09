import logging
import argparse
import re
import polyskel
from PIL import Image, ImageDraw

if __name__ == "__main__":
	logging.basicConfig()

	argparser = argparse.ArgumentParser(description="Construct the straight skeleton of a polygon. The polygon is to be given as a counter-clockwise series of vertices specified by their coordinates: see the example files for the exact format.")
	argparser.add_argument('polygon_file', metavar="<polygon-file>", type=argparse.FileType('r'), help="text file describing the polygon ('-' for standard input)")
	argparser.add_argument('--verbose', '--v', action="store_true", default=False, help="Show construction of the skeleton")
	argparser.add_argument('--log', dest="loglevel", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='WARNING', help="Set log level")
	args = argparser.parse_args()

	polyskel.log.setLevel(getattr(logging, args.loglevel))
	polygon_line_pat = re.compile(r"\s*(?P<coord_x>\d+(\.\d+)?)\s*,\s*(?P<coord_y>\d+(\.\d+)?)\s*(#.*)?")

	contours = []
	poly = []
	for line in args.polygon_file:
		line = line.strip()
		if not line or line.startswith('#'):
			continue

		if line.startswith('-'):
			contours.append(poly)
			poly = []
			continue

		match = polygon_line_pat.match(line)
		poly.append((float(match.group("coord_x")), float(match.group("coord_y"))))

	if not args.polygon_file.isatty():
		args.polygon_file.close()

	contours.append(poly)
	poly = contours[0]
	holes = contours[1:] if len(contours) > 0 else None
	bbox_end_x = int(max(poly, key=lambda x: x[0])[0]+20)
	bbox_end_y = int(max(poly, key=lambda x: x[1])[1]+20)

	im = Image.new("RGB", (bbox_end_x, bbox_end_y), "white")
	draw = ImageDraw.Draw(im)
	if args.verbose:
		polyskel.set_debug((im, draw))


	for contour in contours:
		for point, next in zip(contour, contour[1:]+contour[:1]):
			draw.line((point[0], point[1], next[0], next[1]), fill=0)

	skeleton = polyskel.skeletonize(poly, holes)

	for res in skeleton:
		print(res)

	for arc in skeleton:
		for sink in arc.sinks:
			draw.line((arc.source.x, arc.source.y, sink.x, sink.y), fill="red")
	im.show()
