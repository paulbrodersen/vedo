# Example that shows how to draw very large number of 
# spheres (same for points, lines) with different color
# or different radius.
# (vtk versions<8.0 might be slow)
#
from __future__ import division, print_function
from plotter import vtkPlotter
from random import gauss

N=100000

vp = vtkPlotter(N=2, axes=3, interactive=0)

cols = range(N) #color numbers
pts  = [(gauss(0,1), gauss(0,2), gauss(0,1)) for i in cols]
rads = [abs(pts[i][1])/10 for i in cols] # radius=0 for y=0
print ('..spheres generated:', N)

# all have same radius but different colors:
s0 = vp.spheres(pts, c=cols, r=0.1, alpha=0.9) 

# all have same color but different radius along y:
s1 = vp.spheres(pts, c='r', r=rads, alpha=0.1) 
print ('..spheres built:', N*2)

vp.show(s0, at=0)
vp.show(s1, at=1, legend='N='+str(N), interactive=1)

