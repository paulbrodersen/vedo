from __future__ import division, print_function
import vtk, sys
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray
import numpy as np
import vtkplotter.colors as colors
import vtkplotter.docs as docs
import time

__doc__ = (
    """
Utilities submodule.
"""
    + docs._defs
)

__all__ = [
    "ProgressBar",
    "geometry",
    "isSequence",
    "vector",
    "mag",
    "mag2",
    "versor",
    "precision",
    "pointIsInTriangle",
    "pointToLineDistance",
    "grep",
    "printInfo",
    "makeBands",
    "spher2cart",
    "cart2spher",
    "cart2pol",
    "pol2cart",
    "humansort",
    "resampleArrays",
    "printHistogram",
    "plotMatrix",
    "cameraFromQuaternion",
    "cameraFromNeuroglancer",
    "orientedCamera",
    "vtkCameraToK3D",
    "vtk2trimesh",
    "trimesh2vtk",
]

###########################################################################
class ProgressBar:
    """
    Class to print a progress bar with optional text message.

    :Example:
        .. code-block:: python

            import time
            pb = ProgressBar(0,400, c='red')
            for i in pb.range():
                time.sleep(.1)
                pb.print('some message') # or pb.print(counts=i)

        |progbar|
    """

    def __init__(self, start, stop, step=1, c=None, ETA=True, width=24, char=u"\U000025AC"):

        char_arrow = u"\U000025BA"
        if sys.version_info[0]<3:
            char="="
            char_arrow = '>'

        self.start = start
        self.stop = stop
        self.step = step
        self.color = c
        self.width = width
        self.char = char
        self.char_arrow = char_arrow
        self.bar = ""
        self.percent = 0
        self.clock0 = 0
        self.ETA = ETA
        self.clock0 = time.time()
        self._remt = 1e10
        self._update(0)
        self._counts = 0
        self._oldbar = ""
        self._lentxt = 0
        self._range = np.arange(start, stop, step)
        self._len = len(self._range)

    def print(self, txt="", counts=None):
        """Print the progress bar and optional message."""
        if counts:
            self._update(counts)
        else:
            self._update(self._counts + self.step)
        if self.bar != self._oldbar:
            self._oldbar = self.bar
            eraser = [" "] * self._lentxt + ["\b"] * self._lentxt
            eraser = "".join(eraser)
            if self.ETA:
                tdenom = (time.time() - self.clock0)
                if tdenom:
                    vel = self._counts / tdenom
                    self._remt = (self.stop - self._counts) / vel
                else:
                    vel = 1
                    self._remt = 0.
                if self._remt > 60:
                    mins = int(self._remt / 60)
                    secs = self._remt - 60 * mins
                    mins = str(mins) + "m"
                    secs = str(int(secs + 0.5)) + "s "
                else:
                    mins = ""
                    secs = str(int(self._remt + 0.5)) + "s "
                vel = str(round(vel, 1))
                eta = "ETA: " + mins + secs + "(" + vel + " it/s) "
                if self._remt < 1:
                    dt = time.time() - self.clock0
                    if dt > 60:
                        mins = int(dt / 60)
                        secs = dt - 60 * mins
                        mins = str(mins) + "m"
                        secs = str(int(secs + 0.5)) + "s "
                    else:
                        mins = ""
                        secs = str(int(dt + 0.5)) + "s "
                    eta = "Elapsed time: " + mins + secs + "(" + vel + " it/s)        "
                    txt = ""
            else:
                eta = ""
            txt = eta + str(txt)
            s = self.bar + " " + eraser + txt + "\r"
            if self.color:
                colors.printc(s, c=self.color, end="")
            else:
                sys.stdout.write(s)
                sys.stdout.flush()
            if self.percent == 100:
                print("")
            self._lentxt = len(txt)

    def range(self):
        """Return the range iterator."""
        return self._range

    def len(self):
        """Return the number of steps."""
        return self._len

    def _update(self, counts):
        if counts < self.start:
            counts = self.start
        elif counts > self.stop:
            counts = self.stop
        self._counts = counts
        self.percent = (self._counts - self.start) * 100
        dd = self.stop - self.start
        if dd:
            self.percent /= self.stop - self.start
        else:
            self.percent = 0
        self.percent = int(round(self.percent))
        af = self.width - 2
        nh = int(round(self.percent / 100 * af))
        if nh == 0:
            self.bar = "["+self.char_arrow+"%s]" % (" " * (af - 1))
        elif nh == af:
            self.bar = "[%s]" % (self.char * af)
        else:
            self.bar = "[%s%s%s]" % (self.char *(nh-1), self.char_arrow, " " *(af-nh))
        if self.percent < 100:  # and self._remt > 1:
            ps = " " + str(self.percent) + "%"
        else:
            ps = ""
        self.bar += ps


###########################################################
def geometry(obj, extent=None):
    """
    Apply the ``vtkGeometryFilter``.
    This is a general-purpose filter to extract geometry (and associated data)
    from any type of dataset.
    This filter also may be used to convert any type of data to polygonal type.
    The conversion process may be less than satisfactory for some 3D datasets.
    For example, this filter will extract the outer surface of a volume
    or structured grid dataset.

    Returns an ``Actor`` object.

    :param list extent: set a `[xmin,xmax, ymin,ymax, zmin,zmax]` bounding box to clip data.
    """
    from vtkplotter.actors import Actor
    gf = vtk.vtkGeometryFilter()
    gf.SetInputData(obj)
    if extent is not None:
        gf.SetExtent(extent)
    gf.Update()
    return Actor(gf.GetOutput())


def buildPolyData(vertices, faces=None, lines=None, indexOffset=0, fast=True):
    """
    Build a ``vtkPolyData`` object from a list of vertices
    where faces represents the connectivity of the polygonal mesh.

    E.g. :
        - ``vertices=[[x1,y1,z1],[x2,y2,z2], ...]``
        - ``faces=[[0,1,2], [1,2,3], ...]``

    Use ``indexOffset=1`` if face numbering starts from 1 instead of 0.

    if fast=False the mesh is built "manually" by setting polygons and triangles
    one by one. This is the fallback case when a mesh contains faces of
    different number of vertices.
    """

    if len(vertices[0]) < 3: # make sure it is 3d
        vertices = np.c_[np.array(vertices), np.zeros(len(vertices))]
        if len(vertices[0]) == 2:
            vertices = np.c_[np.array(vertices), np.zeros(len(vertices))]

    poly = vtk.vtkPolyData()

    sourcePoints = vtk.vtkPoints()
    sourcePoints.SetData(numpy_to_vtk(np.ascontiguousarray(vertices), deep=True))
    poly.SetPoints(sourcePoints)

    if lines is not None:
        # Create a cell array to store the lines in and add the lines to it
        linesarr = vtk.vtkCellArray()

        for i in range(1, len(lines)-1):
            vline = vtk.vtkLine()
            vline.GetPointIds().SetId(0,lines[i])
            vline.GetPointIds().SetId(1,lines[i+1])
            linesarr.InsertNextCell(vline)
        poly.SetLines(linesarr)


    if faces is None:
        sourceVertices = vtk.vtkCellArray()
        for i in range(len(vertices)):
            sourceVertices.InsertNextCell(1)
            sourceVertices.InsertCellPoint(i)
        poly.SetVerts(sourceVertices)

        return poly ###################

    # faces exist
    sourcePolygons = vtk.vtkCellArray()
    faces = np.array(faces)
    if len(faces.shape) == 2 and indexOffset==0 and fast:
        #################### all faces are composed of equal nr of vtxs, FAST

        ast = np.int32
        if vtk.vtkIdTypeArray().GetDataTypeSize() != 4:
            ast = np.int64

        nf, nc = faces.shape
        hs = np.hstack((np.zeros(nf)[:,None] + nc, faces)).astype(ast).ravel()
        arr = numpy_to_vtkIdTypeArray(hs, deep=True)
        sourcePolygons.SetCells(nf, arr)

    else: ########################################## manually add faces, SLOW

        showbar = False
        if len(faces) > 25000:
            showbar = True
            pb = ProgressBar(0, len(faces), ETA=False)

        for f in faces:
            n = len(f)

            if n == 3:
                ele = vtk.vtkTriangle()
                pids = ele.GetPointIds()
                for i in range(3):
                    pids.SetId(i, f[i] - indexOffset)
                sourcePolygons.InsertNextCell(ele)

            elif n == 4:
                # do not use vtkTetra() because it fails
                # with dolfin faces orientation
                ele0 = vtk.vtkTriangle()
                ele1 = vtk.vtkTriangle()
                ele2 = vtk.vtkTriangle()
                ele3 = vtk.vtkTriangle()
                if indexOffset:
                    for i in [0,1,2,3]:
                        f[i] -= indexOffset
                f0, f1, f2, f3 = f
                pid0 = ele0.GetPointIds()
                pid1 = ele1.GetPointIds()
                pid2 = ele2.GetPointIds()
                pid3 = ele3.GetPointIds()

                pid0.SetId(0, f0)
                pid0.SetId(1, f1)
                pid0.SetId(2, f2)

                pid1.SetId(0, f0)
                pid1.SetId(1, f1)
                pid1.SetId(2, f3)

                pid2.SetId(0, f1)
                pid2.SetId(1, f2)
                pid2.SetId(2, f3)

                pid3.SetId(0, f2)
                pid3.SetId(1, f3)
                pid3.SetId(2, f0)

                sourcePolygons.InsertNextCell(ele0)
                sourcePolygons.InsertNextCell(ele1)
                sourcePolygons.InsertNextCell(ele2)
                sourcePolygons.InsertNextCell(ele3)

            else:
                ele = vtk.vtkPolygon()
                pids = ele.GetPointIds()
                pids.SetNumberOfIds(n)
                for i in range(n):
                    pids.SetId(i, f[i] - indexOffset)
                sourcePolygons.InsertNextCell(ele)
            if showbar:
                pb.print("converting mesh...    ")

    poly.SetPolys(sourcePolygons)
    return poly

##############################################################################
def isSequence(arg):
    """Check if input is iterable."""
    if hasattr(arg, "strip"):
        return False
    if hasattr(arg, "__getslice__"):
        return True
    if hasattr(arg, "__iter__"):
        return True
    return False


def flatten(list_to_flatten):
    """Flatten out a list."""

    def genflatten(lst):
        for elem in lst:
            if isinstance(elem, (list, tuple)):
                for x in flatten(elem):
                    yield x
            else:
                yield elem

    return list(genflatten(list_to_flatten))


def humansort(l):
    """Sort in place a given list the way humans expect.

    NB: input list is modified

    E.g. ['file11', 'file1'] -> ['file1', 'file11']
    """
    import re

    def alphanum_key(s):
        # Turn a string into a list of string and number chunks.
        # e.g. "z23a" -> ["z", 23, "a"]
        def tryint(s):
            if s.isdigit():
                return int(s)
            return s

        return [tryint(c) for c in re.split("([0-9]+)", s)]

    l.sort(key=alphanum_key)
    return l  # NB: input list is modified


def sortByColumn(array, n):
    '''Sort a numpy array by the `n-th` column'''
    #Author: Steve Tjoa, at https://github.com/rougier/numpy-100
    return array[array[:,n].argsort()]


def findDistanceToLines2D(P0,P1, pts):
    """Consider 2 sets of points P0,P1 describing lines (2D) and a set of points pts,
    compute distance from each point j (P[j]) to each line i (P0[i],P1[i]).
    """
    #Author: Italmassov Kuanysh, at https://github.com/rougier/numpy-100
    def distance(P0, P1, p):
        T = P1 - P0
        L = (T**2).sum(axis=1)
        U = -((P0[:,0]-p[...,0])*T[:,0] + (P0[:,1]-p[...,1])*T[:,1]) / L
        U = U.reshape(len(U),1)
        D = P0 + U*T - p
        return np.sqrt((D**2).sum(axis=1))
    return [distance(P0,P1,p_i) for p_i in pts]


def lin_interp(x, rangeX, rangeY):
    """
    Interpolate linearly variable x in rangeX onto rangeY.
    E.g. if x runs in rangeX=[x0,x1] and the target range is
    rangeY=[y0,y1] then
    y = lin_interp(x, rangeX, rangeY) will interpolate x onto rangeY.
    """
    s = (x - rangeX[0]) / (rangeX[1] - rangeX[0])
    return rangeY[0] * (1 - s) + rangeY[1] * s


def vector(x, y=None, z=0.0):
    """Return a 3D np array representing a vector (of type `np.float64`).

    If `y` is ``None``, assume input is already in the form `[x,y,z]`.
    """
    if y is None:  # assume x is already [x,y,z]
        return np.array(x, dtype=np.float64)
    return np.array([x, y, z], dtype=np.float64)


def versor(v):
    """Return the unit vector. Input can be a list of vectors."""
    if isinstance(v[0], np.ndarray):
        return np.divide(v, mag(v)[:, None])
    else:
        return v / mag(v)


def mag(z):
    """Get the magnitude of a vector."""
    if isinstance(z[0], np.ndarray):
        return np.array(list(map(np.linalg.norm, z)))
    else:
        return np.linalg.norm(z)


def mag2(z):
    """Get the squared magnitude of a vector."""
    return np.dot(z, z)


def precision(x, p, vrange=None):
    """
    Returns a string representation of `x` formatted with precision `p`.

    :param float vrange: range in which x exists (to snap it to '0' if below precision).

    Based on the webkit javascript implementation taken
    `from here <https://code.google.com/p/webkit-mirror/source/browse/JavaScriptCore/kjs/number_object.cpp>`_,
    and implemented by `randlet <https://github.com/randlet/to-precision>`_.
    """
    if isSequence(x):
        out = '('
        for ix in x:
            out += precision(ix, p)
            if ix == x[-1]:
                pass
            else:
                out += ', '
        return out+')'

    import math

    x = float(x)

    if x == 0.0 or (vrange is not None and abs(x) < vrange/pow(10,p)):
        return "0"

    out = []
    if x < 0:
        out.append("-")
        x = -x

    e = int(math.log10(x))
    tens = math.pow(10, e - p + 1)
    n = math.floor(x / tens)

    if n < math.pow(10, p - 1):
        e = e - 1
        tens = math.pow(10, e - p + 1)
        n = math.floor(x / tens)

    if abs((n + 1.0) * tens - x) <= abs(n * tens - x):
        n = n + 1

    if n >= math.pow(10, p):
        n = n / 10.0
        e = e + 1

    m = "%.*g" % (p, n)
    if e < -2 or e >= p:
        out.append(m[0])
        if p > 1:
            out.append(".")
            out.extend(m[1:p])
        out.append("e")
        if e > 0:
            out.append("+")
        out.append(str(e))
    elif e == (p - 1):
        out.append(m)
    elif e >= 0:
        out.append(m[: e + 1])
        if e + 1 < len(m):
            out.append(".")
            out.extend(m[e + 1 :])
    else:
        out.append("0.")
        out.extend(["0"] * -(e + 1))
        out.append(m)
    return "".join(out)


def pointIsInTriangle(p, p1, p2, p3):
    """
    Return True if a point is inside (or above/below) a triangle defined by 3 points in space.
    """
    p = np.array(p)
    u = np.array(p2) - p1
    v = np.array(p3) - p1
    n = np.cross(u, v)
    w = p - p1
    ln = np.dot(n, n)
    if not ln:
        return True  # degenerate triangle
    gamma = (np.dot(np.cross(u, w), n)) / ln
    beta = (np.dot(np.cross(w, v), n)) / ln
    alpha = 1 - gamma - beta
    if 0 < alpha < 1 and 0 < beta < 1 and 0 < gamma < 1:
        return True
    return False


def pointToLineDistance(p, p1, p2):
    """Compute the distance of a point to a line (not the segment) defined by `p1` and `p2`."""
    d = np.sqrt(vtk.vtkLine.DistanceToLine(p, p1, p2))
    return d


def cart2spher(x, y, z):
    """Cartesian to Spherical coordinate conversion."""
    hxy = np.hypot(x, y)
    rho = np.hypot(hxy, z)
    if not rho:
        return (0,0,0)
    theta = np.arctan2(hxy, z)
    phi = np.arctan2(y, x)
    return rho, theta, phi

def spher2cart(rho, theta, phi):
    """Spherical to Cartesian coordinate conversion."""
    st = np.sin(theta)
    sp = np.sin(phi)
    ct = np.cos(theta)
    cp = np.cos(phi)
    rst = rho * st
    x = rst * cp
    y = rst * sp
    z = rho * ct
    return np.array([x, y, z])


def cart2pol(x, y):
    """Cartesian to Polar coordinates conversion."""
    theta = np.arctan2(y, x)
    rho = np.hypot(x, y)
    return theta, rho

def pol2cart(theta, rho):
    """Polar to Cartesian coordinates conversion."""
    x = rho * np.cos(theta)
    y = rho * np.sin(theta)
    return x, y


def isIdentity(M, tol=1e-06):
    """Check if vtkMatrix4x4 is Identity."""
    for i in [0, 1, 2, 3]:
        for j in [0, 1, 2, 3]:
            e = M.GetElement(i, j)
            if i == j:
                if np.abs(e - 1) > tol:
                    return False
            elif np.abs(e) > tol:
                return False
    return True


def grep(filename, tag, firstOccurrence=False):
    """Greps the line that starts with a specific `tag` string from inside a file."""
    import re

    try:
        afile = open(filename, "r")
    except:
        print("Error in utils.grep(): cannot open file", filename)
        raise RuntimeError()
    content = None
    for line in afile:
        if re.search(tag, line):
            content = line.split()
            if firstOccurrence:
                break
    if content:
        if len(content) == 2:
            content = content[1]
        else:
            content = content[1:]
    afile.close()
    return content


def printInfo(obj):
    """Print information about a vtk object."""

    def printvtkactor(actor, tab=""):

        if not actor.GetPickable():
            return

        mapper = actor.GetMapper()
        if hasattr(actor, "polydata"):
            poly = actor.polydata()
        else:
            poly = mapper.GetInput()

        pro = actor.GetProperty()
        pos = actor.GetPosition()
        bnds = actor.GetBounds()
        col = pro.GetColor()
        colr = precision(col[0], 3)
        colg = precision(col[1], 3)
        colb = precision(col[2], 3)
        alpha = pro.GetOpacity()
        npt = poly.GetNumberOfPoints()
        ncl = poly.GetNumberOfCells()
        npl = poly.GetNumberOfPolys()

        print(tab, end="")
        colors.printc("Mesh", c="g", bold=1, invert=1, dim=1, end=" ")

        if hasattr(actor, "_legend") and actor._legend:
            colors.printc("legend: ", c="g", bold=1, end="")
            colors.printc(actor._legend, c="g", bold=0)
        else:
            print()

        if hasattr(actor, "filename") and actor.filename:
            colors.printc(tab + "           file: ", c="g", bold=1, end="")
            colors.printc(actor.filename, c="g", bold=0)

        if not actor.GetMapper().GetScalarVisibility():
            colors.printc(tab + "          color: ", c="g", bold=1, end="")
            #colors.printc("defined by point or cell data", c="g", bold=0)
        #else:
            colors.printc(colors.getColorName(col) + ', rgb=('+colr+', '
                          + colg+', '+colb+'), alpha='+str(alpha), c='g', bold=0)

            if actor.GetBackfaceProperty():
                bcol = actor.GetBackfaceProperty().GetDiffuseColor()
                bcolr = precision(bcol[0], 3)
                bcolg = precision(bcol[1], 3)
                bcolb = precision(bcol[2], 3)
                colors.printc(tab+'     back color: ', c='g', bold=1, end='')
                colors.printc(colors.getColorName(bcol) + ', rgb=('+bcolr+', '
                              + bcolg+', ' + bcolb+')', c='g', bold=0)

        colors.printc(tab + "         points: ", c="g", bold=1, end="")
        colors.printc(npt, c="g", bold=0)

        colors.printc(tab + "          cells: ", c="g", bold=1, end="")
        colors.printc(ncl, c="g", bold=0)

        colors.printc(tab + "       polygons: ", c="g", bold=1, end="")
        colors.printc(npl, c="g", bold=0)

        colors.printc(tab + "       position: ", c="g", bold=1, end="")
        colors.printc(pos, c="g", bold=0)

        if hasattr(actor, "polydata") and actor.N():
            colors.printc(tab + " center of mass: ", c="g", bold=1, end="")
            cm = tuple(actor.centerOfMass())
            colors.printc(precision(cm, 3), c="g", bold=0)

            colors.printc(tab + "   average size: ", c="g", bold=1, end="")
            colors.printc(precision(actor.averageSize(), 6), c="g", bold=0)

            colors.printc(tab + "  diagonal size: ", c="g", bold=1, end="")
            colors.printc(precision(actor.diagonalSize(), 6), c="g", bold=0)

            _area = actor.area()
            if _area:
                colors.printc(tab + "           area: ", c="g", bold=1, end="")
                colors.printc(precision(_area, 6), c="g", bold=0)

            _vol = actor.volume()
            if _vol:
                colors.printc(tab + "         volume: ", c="g", bold=1, end="")
                colors.printc(precision(_vol, 6), c="g", bold=0)

        colors.printc(tab + "         bounds: ", c="g", bold=1, end="")
        bx1, bx2 = precision(bnds[0], 3), precision(bnds[1], 3)
        colors.printc("x=(" + bx1 + ", " + bx2 + ")", c="g", bold=0, end="")
        by1, by2 = precision(bnds[2], 3), precision(bnds[3], 3)
        colors.printc(" y=(" + by1 + ", " + by2 + ")", c="g", bold=0, end="")
        bz1, bz2 = precision(bnds[4], 3), precision(bnds[5], 3)
        colors.printc(" z=(" + bz1 + ", " + bz2 + ")", c="g", bold=0)

        if actor.picked3d is not None:
            colors.printc(tab + "  clicked point: ", c="g", bold=1, end="")
            colors.printc(vector(actor.picked3d), c="g", bold=0)

        ptdata = poly.GetPointData()
        cldata = poly.GetCellData()
        if ptdata.GetNumberOfArrays() + cldata.GetNumberOfArrays():

            arrtypes = dict()
            arrtypes[vtk.VTK_UNSIGNED_CHAR] = "UNSIGNED_CHAR"
            arrtypes[vtk.VTK_SIGNED_CHAR]   = "SIGNED_CHAR"
            arrtypes[vtk.VTK_UNSIGNED_INT]  = "UNSIGNED_INT"
            arrtypes[vtk.VTK_INT]           = "INT"
            arrtypes[vtk.VTK_CHAR]          = "CHAR"
            arrtypes[vtk.VTK_SHORT]         = "SHORT"
            arrtypes[vtk.VTK_LONG]          = "LONG"
            arrtypes[vtk.VTK_ID_TYPE]       = "ID"
            arrtypes[vtk.VTK_FLOAT]         = "FLOAT"
            arrtypes[vtk.VTK_DOUBLE]        = "DOUBLE"
            colors.printc(tab + "    scalar mode:", c="g", bold=1, end=" ")
            colors.printc(mapper.GetScalarModeAsString(),
                          '  coloring =', mapper.GetColorModeAsString(), c="g", bold=0)

            colors.printc(tab + " active scalars: ", c="g", bold=1, end="")
            if ptdata.GetScalars():
                colors.printc(ptdata.GetScalars().GetName(), "(point data)  ", c="g", bold=0, end="")
            if cldata.GetScalars():
                colors.printc(cldata.GetScalars().GetName(), "(cell data)", c="g", bold=0, end="")
            print()

            for i in range(ptdata.GetNumberOfArrays()):
                name = ptdata.GetArrayName(i)
                if name and ptdata.GetArray(i):
                    colors.printc(tab + "     point data: ", c="g", bold=1, end="")
                    try:
                        tt = arrtypes[ptdata.GetArray(i).GetDataType()]
                    except:
                        tt = str(ptdata.GetArray(i).GetDataType())
                    ncomp = str(ptdata.GetArray(i).GetNumberOfComponents())
                    colors.printc("name=" + name, "("+ncomp+" "+tt+"),", c="g", bold=0, end="")
                    rng = ptdata.GetArray(i).GetRange()
                    colors.printc(" range=(" + precision(rng[0],4) + ',' +
                                            precision(rng[1],4) + ')', c="g", bold=0)

            for i in range(cldata.GetNumberOfArrays()):
                name = cldata.GetArrayName(i)
                if name and cldata.GetArray(i):
                    colors.printc(tab + "      cell data: ", c="g", bold=1, end="")
                    try:
                        tt = arrtypes[cldata.GetArray(i).GetDataType()]
                    except:
                        tt = str(cldata.GetArray(i).GetDataType())
                    ncomp = str(cldata.GetArray(i).GetNumberOfComponents())
                    colors.printc("name=" + name, "("+ncomp+" "+tt+"),", c="g", bold=0, end="")
                    rng = cldata.GetArray(i).GetRange()
                    colors.printc(" range=(" + precision(rng[0],4) + ',' +
                                            precision(rng[1],4) + ')', c="g", bold=0)
        else:
            colors.printc(tab + "        scalars:", c="g", bold=1, end=" ")
            colors.printc('no point or cell scalars are present.', c="g", bold=0)


    if not obj:
        return

    elif isinstance(obj, vtk.vtkActor):
        colors.printc("_" * 65, c="g", bold=0)
        printvtkactor(obj)

    elif isinstance(obj, vtk.vtkAssembly):
        colors.printc("_" * 65, c="g", bold=0)
        colors.printc("vtkAssembly", c="g", bold=1, invert=1, end=" ")
        if hasattr(obj, "_legend"):
            colors.printc("legend: ", c="g", bold=1, end="")
            colors.printc(obj._legend, c="g", bold=0)
        else:
            print()

        pos = obj.GetPosition()
        bnds = obj.GetBounds()
        colors.printc("          position: ", c="g", bold=1, end="")
        colors.printc(pos, c="g", bold=0)

        colors.printc("            bounds: ", c="g", bold=1, end="")
        bx1, bx2 = precision(bnds[0], 3), precision(bnds[1], 3)
        colors.printc("x=(" + bx1 + ", " + bx2 + ")", c="g", bold=0, end="")
        by1, by2 = precision(bnds[2], 3), precision(bnds[3], 3)
        colors.printc(" y=(" + by1 + ", " + by2 + ")", c="g", bold=0, end="")
        bz1, bz2 = precision(bnds[4], 3), precision(bnds[5], 3)
        colors.printc(" z=(" + bz1 + ", " + bz2 + ")", c="g", bold=0)

        cl = vtk.vtkPropCollection()
        obj.GetActors(cl)
        cl.InitTraversal()
        for i in range(obj.GetNumberOfPaths()):
            act = vtk.vtkActor.SafeDownCast(cl.GetNextProp())
            if isinstance(act, vtk.vtkActor):
                printvtkactor(act, tab="     ")

    elif isinstance(obj, vtk.vtkVolume):
        colors.printc("_" * 65, c="b", bold=0)
        colors.printc("vtkVolume", c="b", bold=1, invert=1, end=" ")
        if hasattr(obj, "_legend") and obj._legend:
            colors.printc("legend: ", c="b", bold=1, end="")
            colors.printc(obj._legend, c="b", bold=0)
        else:
            print()

        pos = obj.GetPosition()
        bnds = obj.GetBounds()
        img = obj.GetMapper().GetInput()
        colors.printc("         position: ", c="b", bold=1, end="")
        colors.printc(pos, c="b", bold=0)

        colors.printc("       dimensions: ", c="b", bold=1, end="")
        colors.printc(img.GetDimensions(), c="b", bold=0)
        colors.printc("          spacing: ", c="b", bold=1, end="")
        colors.printc(img.GetSpacing(), c="b", bold=0)
        colors.printc("   data dimension: ", c="b", bold=1, end="")
        colors.printc(img.GetDataDimension(), c="b", bold=0)

        colors.printc("      memory size: ", c="b", bold=1, end="")
        colors.printc(int(img.GetActualMemorySize()/1024), 'Mb', c="b", bold=0)

        colors.printc("    scalar #bytes: ", c="b", bold=1, end="")
        colors.printc(img.GetScalarSize(), c="b", bold=0)

        colors.printc("           bounds: ", c="b", bold=1, end="")
        bx1, bx2 = precision(bnds[0], 3), precision(bnds[1], 3)
        colors.printc("x=(" + bx1 + ", " + bx2 + ")", c="b", bold=0, end="")
        by1, by2 = precision(bnds[2], 3), precision(bnds[3], 3)
        colors.printc(" y=(" + by1 + ", " + by2 + ")", c="b", bold=0, end="")
        bz1, bz2 = precision(bnds[4], 3), precision(bnds[5], 3)
        colors.printc(" z=(" + bz1 + ", " + bz2 + ")", c="b", bold=0)

        colors.printc("     scalar range: ", c="b", bold=1, end="")
        colors.printc(img.GetScalarRange(), c="b", bold=0)

        printHistogram(obj, horizontal=True,
                       logscale=True, bins=8, height=15, c='b', bold=0)

    elif hasattr(obj, "interactor"):  # dumps Plotter info
        axtype = {
            0: "(no axes)",
            1: "(three customizable gray grid walls)",
            2: "(cartesian axes from origin",
            3: "(positive range of cartesian axes from origin",
            4: "(axes triad at bottom left)",
            5: "(oriented cube at bottom left)",
            6: "(mark the corners of the bounding box)",
            7: "(ruler at the bottom of the window)",
            8: "(the vtkCubeAxesActor object)",
            9: "(the bounding box outline)",
            10: "(circles of maximum bounding box range)",
        }
        bns, totpt = [], 0
        for a in obj.actors:
            b = a.GetBounds()
            if a.GetBounds() is not None:
                if isinstance(a, vtk.vtkActor):
                    totpt += a.GetMapper().GetInput().GetNumberOfPoints()
                bns.append(b)
        if len(bns) == 0:
            return
        acts = obj.getActors()
        colors.printc("_" * 65, c="c", bold=0)
        colors.printc("Plotter", invert=1, dim=1, c="c", end=" ")
        otit = obj.title
        if not otit:
            otit = None
        colors.printc("   title:", otit, bold=0, c="c")
        colors.printc(" active renderer:", obj.renderers.index(obj.renderer), bold=0, c="c")
        colors.printc("   nr. of actors:", len(acts), bold=0, c="c", end="")
        colors.printc(" (" + str(totpt), "vertices)", bold=0, c="c")
        max_bns = np.max(bns, axis=0)
        min_bns = np.min(bns, axis=0)
        colors.printc("      max bounds: ", c="c", bold=0, end="")
        bx1, bx2 = precision(min_bns[0], 3), precision(max_bns[1], 3)
        colors.printc("x=(" + bx1 + ", " + bx2 + ")", c="c", bold=0, end="")
        by1, by2 = precision(min_bns[2], 3), precision(max_bns[3], 3)
        colors.printc(" y=(" + by1 + ", " + by2 + ")", c="c", bold=0, end="")
        bz1, bz2 = precision(min_bns[4], 3), precision(max_bns[5], 3)
        colors.printc(" z=(" + bz1 + ", " + bz2 + ")", c="c", bold=0)
        if isinstance(obj.axes, dict): obj.axes=1
        colors.printc("       axes type:", obj.axes, axtype[obj.axes], bold=0, c="c")

        for a in obj.getVolumes():
            if a.GetBounds() is not None:
                img = a.GetMapper().GetDataSetInput()
                colors.printc('_'*65, c='b', bold=0)
                colors.printc('Volume', invert=1, dim=1, c='b')
                colors.printc('      scalar range:',
                              np.round(img.GetScalarRange(), 4), c='b', bold=0)
                bnds = a.GetBounds()
                colors.printc("            bounds: ", c="b", bold=0, end="")
                bx1, bx2 = precision(bnds[0], 3), precision(bnds[1], 3)
                colors.printc("x=(" + bx1 + ", " + bx2 + ")", c="b", bold=0, end="")
                by1, by2 = precision(bnds[2], 3), precision(bnds[3], 3)
                colors.printc(" y=(" + by1 + ", " + by2 + ")", c="b", bold=0, end="")
                bz1, bz2 = precision(bnds[4], 3), precision(bnds[5], 3)
                colors.printc(" z=(" + bz1 + ", " + bz2 + ")", c="b", bold=0)

        colors.printc(" Click actor and press i for Actor info.", c="c")

    else:
        colors.printc("_" * 65, c="g", bold=0)
        colors.printc(type(obj), c="g", invert=1)



def printHistogram(data, bins=10, height=10, logscale=False, minbin=0,
                   horizontal=False, char=u"\U00002589",
                   c=None, bold=True, title='Histogram'):
    """
    Ascii histogram printing.
    Input can also be ``Volume`` or ``Actor``.
    Returns the raw data before binning (useful when passing vtk objects).

    :param int bins: number of histogram bins
    :param int height: height of the histogram in character units
    :param bool logscale: use logscale for frequencies
    :param int minbin: ignore bins before minbin
    :param bool horizontal: show histogram horizontally
    :param str char: character to be used
    :param str,int c: ascii color
    :param bool char: use boldface
    :param str title: histogram title

    :Example:
        .. code-block:: python

            from vtkplotter import printHistogram
            import np as np
            d = np.random.normal(size=1000)
            data = printHistogram(d, c='blue', logscale=True, title='my scalars')
            data = printHistogram(d, c=1, horizontal=1)
            print(np.mean(data)) # data here is same as d

        |printhisto|
    """
    # Adapted from http://pyinsci.blogspot.com/2009/10/ascii-histograms.html

    if not horizontal: # better aspect ratio
        bins *= 2

    isimg = isinstance(data, vtk.vtkImageData)
    isvol = isinstance(data, vtk.vtkVolume)
    if isimg or isvol:
        if isvol:
            img = data.imagedata()
        else:
            img = data
        dims = img.GetDimensions()
        nvx = min(100000, dims[0]*dims[1]*dims[2])
        idxs = np.random.randint(0, min(dims), size=(nvx, 3))
        data = []
        for ix, iy, iz in idxs:
            d = img.GetScalarComponentAsFloat(ix, iy, iz, 0)
            data.append(d)
    elif isinstance(data, vtk.vtkActor):
        arr = data.polydata().GetPointData().GetScalars()
        if not arr:
            arr = data.polydata().GetCellData().GetScalars()
            if not arr:
                return

        from vtk.util.numpy_support import vtk_to_numpy
        data = vtk_to_numpy(arr)

    h = np.histogram(data, bins=bins)

    if minbin:
        hi = h[0][minbin:-1]
    else:
        hi = h[0]

    if sys.version_info[0] < 3 and char == u"\U00002589":
        char = "*" # python2 hack
    if char == u"\U00002589" and horizontal:
        char = u"\U00002586"

    entrs = "\t(entries=" + str(len(data)) + ")"
    if logscale:
        h0 = np.log10(hi+1)
        maxh0 = int(max(h0)*100)/100
        title = '(logscale) ' + title + entrs
    else:
        h0 = hi
        maxh0 = max(h0)
        title = title + entrs

    def _v():
        his = ""
        if title:
            his += title +"\n"
        bars = h0 / maxh0 * height
        for l in reversed(range(1, height + 1)):
            line = ""
            if l == height:
                line = "%s " % maxh0
            else:
                line = "   |" + " " * (len(str(maxh0))-3)
            for c in bars:
                if c >= np.ceil(l):
                    line += char
                else:
                    line += " "
            line += "\n"
            his += line
        his += "%.2f" % h[1][0] + "." * (bins) + "%.2f" % h[1][-1] + "\n"
        return his

    def _h():
        his = ""
        if title:
            his += title +"\n"
        xl = ["%.2f" % n for n in h[1]]
        lxl = [len(l) for l in xl]
        bars = h0 / maxh0 * height
        his += " " * int(max(bars) + 2 + max(lxl)) + "%s\n" % maxh0
        for i, c in enumerate(bars):
            line = (xl[i] + " " * int(max(lxl) - lxl[i]) + "| " + char * int(c) + "\n")
            his += line
        return his

    if horizontal:
        height *= 2
        colors.printc(_h(), c=c, bold=bold)
    else:
        colors.printc(_v(), c=c, bold=bold)
    return data


def makeBands(inputlist, numberOfBands):
    """
    Group values of a list into bands of equal value.

    :param int numberOfBands: number of bands, a positive integer > 2.
    :return: a binned list of the same length as the input.
    """
    if numberOfBands < 2:
        return inputlist
    vmin = np.min(inputlist)
    vmax = np.max(inputlist)
    bb = np.linspace(vmin, vmax, numberOfBands, endpoint=0)
    dr = bb[1] - bb[0]
    bb += dr / 2
    tol = dr / 2 * 1.001

    newlist = []
    for s in inputlist:
        for b in bb:
            if abs(s - b) < tol:
                newlist.append(b)
                break

    return np.array(newlist)



def resampleArrays(source, target, tol=None):
        """Resample point and cell data of a dataset on points from another dataset.

        :param float tol: set the tolerance used to compute whether
            a point in the target is in a cell of the source.
            Points without resampled values, and their cells, are be marked as blank.
        """
        rs = vtk.vtkResampleWithDataSet()
        rs.SetSourceData(target.polydata())
        rs.SetInputData(source.polydata())
        rs.SetPassPointArrays(True)
        rs.SetPassCellArrays(True)
        if tol:
            rs.SetComputeTolerance(False)
            rs.SetTolerance(tol)
        rs.Update()
        return rs.GetOutput()


def plotMatrix(M, title='matrix', continuous=True, cmap='Greys'):
    """
	 Plot a matrix using `matplotlib`.

    :Example:
        .. code-block:: python

            from vtkplotter.dolfin import plotMatrix
            import numpy as np

            M = np.eye(9) + np.random.randn(9,9)/4

            plotMatrix(M)

        |pmatrix|
    """
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    M    = np.array(M)
    m,n  = np.shape(M)
    M    = M.round(decimals=2)

    fig  = plt.figure()
    ax   = fig.add_subplot(111)
    cmap = mpl.cm.get_cmap(cmap)
    if not continuous:
        unq  = np.unique(M)
    im      = ax.imshow(M, cmap=cmap, interpolation='None')
    divider = make_axes_locatable(ax)
    cax     = divider.append_axes("right", size="5%", pad=0.05)
    dim     = r'$%i \times %i$ ' % (m,n)
    ax.set_title(dim + title)
    ax.axis('off')
    cb = plt.colorbar(im, cax=cax)
    if not continuous:
       cb.set_ticks(unq)
       cb.set_ticklabels(unq)
    plt.show()


#################################################################
# Functions adapted from:
# https://github.com/sdorkenw/MeshParty/blob/master/meshparty/trimesh_vtk.py
def cameraFromQuaternion(pos, quaternion, distance=10000, ngl_correct=True):
    """Define a ``vtkCamera`` with a particular orientation.

        Parameters
        ----------
        pos: np.array, list, tuple
            an iterator of length 3 containing the focus point of the camera
        quaternion: np.array, list, tuple
            a len(4) quaternion (x,y,z,w) describing the rotation of the camera
            such as returned by neuroglancer x,y,z,w all in [0,1] range
        distance: float
            the desired distance from pos to the camera (default = 10000 nm)

        Returns
        -------
        vtk.vtkCamera
            a vtk camera setup according to these rules.
    """
    camera = vtk.vtkCamera()
    # define the quaternion in vtk, note the swapped order
    # w,x,y,z instead of x,y,z,w
    quat_vtk = vtk.vtkQuaterniond(
        quaternion[3], quaternion[0], quaternion[1], quaternion[2]
    )
    # use this to define a rotation matrix in x,y,z
    # right handed units
    M = np.zeros((3, 3), dtype=np.float32)
    quat_vtk.ToMatrix3x3(M)
    # the default camera orientation is y up
    up = [0, 1, 0]
    # calculate default camera position is backed off in positive z
    pos = [0, 0, distance]

    # set the camera rototation by applying the rotation matrix
    camera.SetViewUp(*np.dot(M, up))
    # set the camera position by applying the rotation matrix
    camera.SetPosition(*np.dot(M, pos))
    if ngl_correct:
        # neuroglancer has positive y going down
        # so apply these azimuth and roll corrections
        # to fix orientatins
        camera.Azimuth(-180)
        camera.Roll(180)

    # shift the camera posiiton and focal position
    # to be centered on the desired location
    p = camera.GetPosition()
    p_new = np.array(p) + pos
    camera.SetPosition(*p_new)
    camera.SetFocalPoint(*pos)
    return camera


def cameraFromNeuroglancer(state, zoom=300):
    """Define a ``vtkCamera`` from a neuroglancer state dictionary.

        Parameters
        ----------
        state: dict
            an neuroglancer state dictionary.
        zoom: float
            how much to multiply zoom by to get camera backoff distance
            default = 300 > ngl_zoom = 1 > 300 nm backoff distance.

        Returns
        -------
        vtk.vtkCamera
            a vtk camera setup that matches this state.
    """
    orient = state.get("perspectiveOrientation", [0.0, 0.0, 0.0, 1.0])
    pzoom = state.get("perspectiveZoom", 10.0)
    position = state["navigation"]["pose"]["position"]
    pos_nm = np.array(position["voxelCoordinates"]) * position["voxelSize"]
    return cameraFromQuaternion(pos_nm, orient, pzoom * zoom, ngl_correct=True)


def orientedCamera(center, upVector=(0,-1,0), backoffVector=(0,0,1), backoff=500):
    """
    Generate a ``vtkCamera`` pointed at a specific location,
    oriented with a given up direction, set to a backoff.
    """
    vup = np.array(upVector)
    vup = vup / np.linalg.norm(vup)

    pt_backoff = center - backoff * 1000 * np.array(backoffVector)

    camera = vtk.vtkCamera()
    camera.SetFocalPoint(*center)
    camera.SetViewUp(*vup)
    camera.SetPosition(*pt_backoff)
    return camera


def vtkCameraToK3D(vtkcam):
    """
    Convert a ``vtkCamera`` object into a 9-element list to be used by K3D backend.

    Output format is: [posx,posy,posz, targetx,targety,targetz, upx,upy,upz]
    """
    cdis = vtkcam.GetDistance()
    cpos = np.array(vtkcam.GetPosition())*cdis
    kam = [cpos.tolist()]
    kam.append(vtkcam.GetFocalPoint())
    kam.append(vtkcam.GetViewUp())
    return np.array(kam).ravel()



############################################################################
#Trimesh support
#
#Install trimesh with:
#
#    sudo apt install python3-rtree
#    pip install rtree shapely
#    conda install trimesh
#
#Check the example gallery in: examples/other/trimesh>
###########################################################################

def vtk2trimesh(actor):
    """
    Convert vtk ``Actor`` to ``Trimesh`` object.
    """
    if isSequence(actor):
        tms = []
        for a in actor:
            tms.append(vtk2trimesh(a))
        return tms

    from trimesh import Trimesh

    lut = actor.mapper.GetLookupTable()

    tris = actor.faces()
    carr = actor.scalars('CellColors', datatype='cell')
    ccols = None
    if carr is not None and len(carr)==len(tris):
        ccols = []
        for i in range(len(tris)):
            r,g,b,a = lut.GetTableValue(carr[i])
            ccols.append((r*255, g*255, b*255, a*255))
        ccols = np.array(ccols, dtype=np.int16)

    points = actor.coordinates()
    varr = actor.scalars('VertexColors', datatype='point')
    vcols = None
    if varr is not None and len(varr)==len(points):
        vcols = []
        for i in range(len(points)):
            r,g,b,a = lut.GetTableValue(varr[i])
            vcols.append((r*255, g*255, b*255, a*255))
        vcols = np.array(vcols, dtype=np.int16)

    if len(tris)==0:
        tris = None

    return Trimesh(vertices=points, faces=tris,
                   face_colors=ccols, vertex_colors=vcols)


def trimesh2vtk(inputobj, alphaPerCell=False):
    """
    Convert ``Trimesh`` object to ``Actor(vtkActor)`` or ``Assembly`` object.
    """
    if isSequence(inputobj):
        vms = []
        for ob in inputobj:
            vms.append(trimesh2vtk(ob))
        return vms

    # print('trimesh2vtk inputobj', type(inputobj))

    inputobj_type = str(type(inputobj))

    if "Trimesh" in inputobj_type or "primitives" in inputobj_type:
        from vtkplotter import Actor

        faces = inputobj.faces
        poly = buildPolyData(inputobj.vertices, faces)
        tact = Actor(poly)
        if inputobj.visual.kind == "face":
            trim_c = inputobj.visual.face_colors
        else:
            trim_c = inputobj.visual.vertex_colors

        if isSequence(trim_c):
            if isSequence(trim_c[0]):
                trim_cc = (trim_c[:, [0, 1, 2]] / 255)
                trim_al = trim_c[:, 3] / 255
                if inputobj.visual.kind == "face":
                    tact.cellColors(trim_cc, mode='colors',
                                    alpha=trim_al, alphaPerCell=alphaPerCell)
                else:
                    tact.pointColors(trim_cc, mode='colors', alpha=trim_al)
        return tact

    elif "PointCloud" in inputobj_type:
        from vtkplotter.shapes import Points

        trim_cc, trim_al = "black", 1
        if hasattr(inputobj, "vertices_color"):
            trim_c = inputobj.vertices_color
            if len(trim_c):
                trim_cc = trim_c[:, [0, 1, 2]] / 255
                trim_al = trim_c[:, 3] / 255
                trim_al = np.sum(trim_al) / len(trim_al)  # just the average
        return Points(inputobj.vertices, r=8, c=trim_cc, alpha=trim_al)

    elif "path" in inputobj_type:
        from vtkplotter.shapes import Line
        from vtkplotter.actors import Assembly

        lines = []
        for e in inputobj.entities:
            # print('trimesh entity', e.to_dict())
            l = Line(inputobj.vertices[e.points], c="k", lw=2)
            lines.append(l)
        return Assembly(lines)

    return None