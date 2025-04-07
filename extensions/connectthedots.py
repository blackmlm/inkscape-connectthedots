#!/usr/bin/env python
'''
Connect the Dots extension for Inkscape Vector Graphics Editor
Copyright (C) 2013  Manuel Grauwiler (HereticPilgrim)
Copyright (C) 2025  Jose Garza

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

2025 - Fixed to work with inkscape 1.4
'''

from random import randint, choice
from math import pi, acos, sqrt, degrees

import inkex
from inkex import PathElement
from inkex.paths import Path

class ConnectTheDots(inkex.EffectExtension):
	TOP_RIGHT = 1
	TOP_LEFT = 2
	BOTTOM_LEFT = 3
	BOTTOM_RIGHT = 4
	
	def add_arguments(self, pars):
		pars.add_argument('-p', '--hidepath', type=inkex.Boolean, default=True,
						  help='Hide the original path after completion?')
		pars.add_argument('-r', '--radius', type=float, default=10,
						  help='Radius of the dots at every vertex of the path')
		pars.add_argument('-f', '--fontsize', type=float, default=10,
						  help='Font size of the numbers')


	def effect(self):
		svg = self.svg

		# create new layers for dots and for numbers
		dotLayer = svg.add(inkex.Layer.new('ConnectTheDots dotLayer'))
		numberLayer = svg.add(inkex.Layer.new('ConnectTheDots numberLayer'))

		# iterate over every path, start numbering from 1 every time
		for path in self.svg.selection.filter(PathElement):
			# radius and fontsize as offsets to avoid placing numbers inside dots
			r = float(self.options.radius)
			f = 0.5 * self.options.fontsize

			# iterate over vertices and draw dots on each as well as the number next to it
			d = path.get('d')
			path_object = Path(d)
			vertices = path_object.to_arrays()
			
			for idx, v in enumerate(vertices):
				x, y = self.getXY(v)

				# create dots
				style = {
					'stroke': 'none',
					'stroke-width': '0',
					'fill': '#000000'
				}
				name = 'pbn_%i' % idx
				
				# Create a circle element for the dot
				circle = inkex.Circle()
				circle.set('cx', str(x))
				circle.set('cy', str(y))
				circle.set('r', str(r))
				circle.style = style
				circle.set('id', name)
				dotLayer.add(circle)

				if idx > 0 and idx < len(vertices)-1:
					# block two quadrants, one for the previous and one for the next
					freeQuads = self.findFreeQuadrants((x,y), self.getXY(vertices[idx-1]), self.getXY(vertices[idx+1]))
				elif idx > 0:
					# special case for end nodes, only block one quadrant
					freeQuads = self.findFreeQuadrants((x,y), self.getXY(vertices[idx-1]))
				else:
					# special case for first node when it's the only one
					if len(vertices) > 1:
						freeQuads = self.findFreeQuadrants((x,y), self.getXY(vertices[idx+1]))
					else:
						# If there's only one vertex, use all quadrants
						freeQuads = [self.TOP_LEFT, self.TOP_RIGHT, self.BOTTOM_RIGHT, self.BOTTOM_LEFT]

				# randomly place number in one of the free quadrants
				q = choice(freeQuads)
				if q == self.TOP_RIGHT:
					nx = x+2*r
					ny = y+2*r+f
					textAnchor = 'start'
				elif q == self.TOP_LEFT:
					nx = x-2*r
					ny = y+r+f
					textAnchor = 'end'
				elif q == self.BOTTOM_LEFT:
					nx = x-r
					ny = y-r
					textAnchor = 'end'
				else: # BOTTOM_RIGHT
					nx = x+r
					ny = y-r
					textAnchor = 'start'

				# create the number element
				text = inkex.TextElement()
				text.text = str(idx+1)
				text.set('x', str(nx))
				text.set('y', str(ny))
				text.set('font-size', str(self.options.fontsize))
				text.set('text-anchor', textAnchor)
				numberLayer.add(text)

			# hide the original path if specified in options
			if self.options.hidepath:
				path.style['display'] = 'none'

	
	def getXY(self, vertex):
		# split vertex info into command and list of parameters
		cmd, params = vertex
		
		# Handle path commands with coordinate parameters
		if cmd == 'M' or cmd == 'L':
			# Move to or Line to
			if len(params) >= 2:
				x, y = params[0], params[1]
			else:
				# Handle case with insufficient parameters
				return (0, 0)
		elif cmd == 'H':
			# Horizontal line - only has x coordinate
			if len(params) >= 1:
				x = params[0]
				# Use previous y (not implemented, return 0)
				y = 0
			else:
				return (0, 0)
		elif cmd == 'V':
			# Vertical line - only has y coordinate
			if len(params) >= 1:
				# Use previous x (not implemented, return 0)
				x = 0
				y = params[0]
			else:
				return (0, 0)
		elif cmd == 'Z' or cmd == 'z':
			# Close path - no coordinates
			return (0, 0)
		else:
			# Curve commands (C, S, Q, T, A)
			if len(params) >= 2:
				x, y = params[-2:]
			else:
				# Handle case with insufficient parameters
				return (0, 0)
				
		return (x, y)


	def findFreeQuadrants(self, current, previous, next = None):
		'''Determines which quadrants around the current vertex are still available
		for number placement. Returns a list of at least two free quadrants. If next
		is None, the current vertex is treated as a start/end vertex and only one
		vertex is considered for blocking quadrants.'''
		freeQuads = [self.TOP_LEFT, self.TOP_RIGHT, self.BOTTOM_RIGHT, self.BOTTOM_LEFT]
		freeQuads.remove(self.findBlockedQuadrant(current, previous))
		if next != None:
			q = self.findBlockedQuadrant(current, next)
			if q in freeQuads:
				freeQuads.remove(q)
		return freeQuads

		
	def findBlockedQuadrant(self, current, reference):
		'''Determines which quadrant of the current point is blocked for number
		placement by the reference point. E.g. if the reference point is in the
		top right relative to the current point, the TOP_RIGHT quadrant will
		not be allowed for number placement.'''
		x1,y1 = current
		x2,y2 = reference
		if x2 > x1:
			# reference is on the right side
			if y2 > y1:
				return self.TOP_RIGHT
			else:
				return self.BOTTOM_RIGHT
		else:
			# reference is on the left side
			if y2 > y1:
				return self.TOP_LEFT
			else:
				return self.BOTTOM_LEFT

if __name__ == '__main__':
    ConnectTheDots().run()