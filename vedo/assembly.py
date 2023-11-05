#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
from weakref import ref as weak_ref_to

import vedo.vtkclasses as vtk

import vedo
from vedo.transformations import LinearTransform
from vedo.visual import CommonVisual

__docformat__ = "google"

__doc__ = """
Submodule for managing groups of vedo objects

![](https://vedo.embl.es/images/basic/align4.png)
"""

__all__ = ["Group", "Assembly", "procrustes_alignment"]


#################################################
def procrustes_alignment(sources, rigid=False):
    """
    Return an `Assembly` of aligned source meshes with the `Procrustes` algorithm.
    The output `Assembly` is normalized in size.

    The `Procrustes` algorithm takes N set of points and aligns them in a least-squares sense
    to their mutual mean. The algorithm is iterated until convergence,
    as the mean must be recomputed after each alignment.

    The set of average points generated by the algorithm can be accessed with
    `algoutput.info['mean']` as a numpy array.

    Arguments:
        rigid : bool
            if `True` scaling is disabled.

    Examples:
        - [align4.py](https://github.com/marcomusy/vedo/tree/master/examples/basic/align4.py)

        ![](https://vedo.embl.es/images/basic/align4.png)
    """

    group = vtk.new("MultiBlockDataGroupFilter")
    for source in sources:
        if sources[0].npoints != source.npoints:
            vedo.logger.error("sources have different nr of points")
            raise RuntimeError()
        group.AddInputData(source.dataset)
    procrustes = vtk.new("ProcrustesAlignmentFilter")
    procrustes.StartFromCentroidOn()
    procrustes.SetInputConnection(group.GetOutputPort())
    if rigid:
        procrustes.GetLandmarkTransform().SetModeToRigidBody()
    procrustes.Update()

    acts = []
    for i, s in enumerate(sources):
        poly = procrustes.GetOutput().GetBlock(i)
        mesh = vedo.mesh.Mesh(poly)
        mesh.actor.SetProperty(s.actor.GetProperty())
        mesh.properties = s.actor.GetProperty()
        if hasattr(s, "name"):
            mesh.name = s.name
        acts.append(mesh)
    assem = Assembly(acts)
    assem.transform = procrustes.GetLandmarkTransform()
    assem.info["mean"] = vedo.utils.vtk2numpy(procrustes.GetMeanPoints().GetData())
    return assem


#################################################
class Group(CommonVisual, vtk.vtkPropAssembly):
    """Form groups of generic objects (not necessarily meshes)."""

    def __init__(self, objects=()):
        """Form groups of generic objects (not necessarily meshes)."""

        super().__init__()

        self.actor = self

        self.name = "Group"
        self.filename = ""
        self.trail = None
        self.trail_points = []
        self.trail_segment_size = 0
        self.trail_offset = None
        self.shadows = []
        self.info = {}
        self.rendered_at = set()
        self.scalarbar = None

        self.transform = LinearTransform()

        for a in vedo.utils.flatten(objects):
            if a:
                self.AddPart(a.actor)

        self.PickableOff()


    def __iadd__(self, obj):
        """
        Add an object to the group
        """
        if not vedo.utils.is_sequence(obj):
            obj = [obj]
        for a in obj:
            if a:
                self.AddPart(a)
        return self

    def unpack(self):
        """Unpack the group into its elements"""
        elements = []
        self.InitPathTraversal()
        parts = self.GetParts()
        parts.InitTraversal()
        for i in range(parts.GetNumberOfItems()):
            ele = parts.GetItemAsObject(i)
            elements.append(ele)

        # gr.InitPathTraversal()
        # for _ in range(gr.GetNumberOfPaths()):
        #     path  = gr.GetNextPath()
        #     print([path])
        #     path.InitTraversal()
        #     for i in range(path.GetNumberOfItems()):
        #         a = path.GetItemAsObject(i).GetViewProp()
        #         print([a])

        return elements

    def clear(self):
        """Remove all parts"""
        for a in self.unpack():
            self.RemovePart(a)
        return self

    def on(self):
        """Switch on visibility"""
        self.VisibilityOn()
        return self

    def off(self):
        """Switch off visibility"""
        self.VisibilityOff()
        return self

    def pickable(self, value=None):
        """Set/get the pickability property of an object."""
        if value is None:
            return self.GetPickable()
        self.SetPickable(value)
        return self

    def draggable(self, value=None):
        """Set/get the draggability property of an object."""
        if value is None:
            return self.GetDragable()
        self.SetDragable(value)
        return self

    def pos(self, x=None, y=None):
        """Set/Get object position."""
        if x is None:  # get functionality
            return np.array(self.GetPosition())

        if y is None:  # assume x is of the form (x,y)
            x, y = x
        self.SetPosition(x, y)
        return self

    def shift(self, ds):
        """Add a shift to the current object position."""
        p = np.array(self.GetPosition())

        self.SetPosition(p + ds)
        return self

    def bounds(self):
        """
        Get the object bounds.
        Returns a list in format [xmin,xmax, ymin,ymax].
        """
        return self.GetBounds()


    def show(self, **options):
        """
        Create on the fly an instance of class `Plotter` or use the last existing one to
        show one single object.

        This method is meant as a shortcut. If more than one object needs to be visualised
        please use the syntax `show(mesh1, mesh2, volume, ..., options)`.

        Returns the `Plotter` class instance.
        """
        return vedo.plotter.show(self, **options)


#################################################
class Assembly(CommonVisual, vtk.vtkAssembly):
    """
    Group many objects and treat them as a single new object.
    """

    def __init__(self, *meshs):
        """
        Group many objects and treat them as a single new object,
        keeping track of internal transformations.

        Examples:
            - [gyroscope1.py](https://github.com/marcomusy/vedo/tree/master/examples/simulations/gyroscope1.py)

            ![](https://vedo.embl.es/images/simulations/39766016-85c1c1d6-52e3-11e8-8575-d167b7ce5217.gif)
        """
        super().__init__()

        if len(meshs) == 1:
            meshs = meshs[0]
        else:
            meshs = vedo.utils.flatten(meshs)

        self.actor = self
        self.actor.retrieve_object = weak_ref_to(self)

        self.name = "Assembly"
        self.filename = ""
        self.rendered_at = set()
        self.scalarbar = None
        self.info = {}
        self.time = 0

        self.transform = LinearTransform()

        self.objects = [m for m in meshs if m]
        self.actors  = [m.actor for m in self.objects]

        scalarbars = []
        for a in self.actors:
            if isinstance(a, vtk.get_class("Prop3D")): # and a.GetNumberOfPoints():
                self.AddPart(a)
            if hasattr(a, "scalarbar") and a.scalarbar is not None:
                scalarbars.append(a.scalarbar)

        if len(scalarbars) > 1:
            self.scalarbar = Group(scalarbars)
        elif len(scalarbars) == 1:
            self.scalarbar = scalarbars[0]

        self.pipeline = vedo.utils.OperationNode(
            "Assembly",
            parents=self.objects,
            comment=f"#meshes {len(self.objects)}",
            c="#f08080",
        )
        ##########################################

    def __str__(self):
        """Print info about Assembly object."""
        module = self.__class__.__module__
        name = self.__class__.__name__
        out = vedo.printc(
            f"{module}.{name} at ({hex(id(self))})".ljust(75),
            bold=True, invert=True, return_string=True,
        )
        out += "\x1b[0m"

        if self.name:
            out += "name".ljust(14) + ": " + self.name
            if "legend" in self.info.keys() and self.info["legend"]:
                out+= f", legend='{self.info['legend']}'"
            out += "\n"

        n = len(self.unpack())
        out += "n. of objects".ljust(14) + ": " + str(n) + " "
        names = [a.name for a in self.unpack() if a.name]
        if names:
            out += str(names).replace("'","")[:56]
        out += "\n"

        pos = self.GetPosition()
        out += "position".ljust(14) + ": " + str(pos) + "\n"

        bnds = self.GetBounds()
        bx1, bx2 = vedo.utils.precision(bnds[0], 3), vedo.utils.precision(bnds[1], 3)
        by1, by2 = vedo.utils.precision(bnds[2], 3), vedo.utils.precision(bnds[3], 3)
        bz1, bz2 = vedo.utils.precision(bnds[4], 3), vedo.utils.precision(bnds[5], 3)
        out+= "bounds".ljust(14) + ":"
        out+= " x=(" + bx1 + ", " + bx2 + "),"
        out+= " y=(" + by1 + ", " + by2 + "),"
        out+= " z=(" + bz1 + ", " + bz2 + ")\n"
        return out.rstrip() + "\x1b[0m"

    def print(self):
        """Print info about Assembly object."""
        print(self.__str__())
        return self

    def _repr_html_(self):
        """
        HTML representation of the Assembly object for Jupyter Notebooks.

        Returns:
            HTML text with the image and some properties.
        """
        import io
        import base64
        from PIL import Image

        library_name = "vedo.assembly.Assembly"
        help_url = "https://vedo.embl.es/docs/vedo/assembly.html"

        arr = self.thumbnail(zoom=1.1, elevation=-60)

        im = Image.fromarray(arr)
        buffered = io.BytesIO()
        im.save(buffered, format="PNG", quality=100)
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        url = "data:image/png;base64," + encoded
        image = f"<img src='{url}'></img>"

        # statisitics
        bounds = "<br/>".join(
            [
                vedo.utils.precision(min_x, 4) + " ... " + vedo.utils.precision(max_x, 4)
                for min_x, max_x in zip(self.bounds()[::2], self.bounds()[1::2])
            ]
        )

        help_text = ""
        if self.name:
            help_text += f"<b> {self.name}: &nbsp&nbsp</b>"
        help_text += '<b><a href="' + help_url + '" target="_blank">' + library_name + "</a></b>"
        if self.filename:
            dots = ""
            if len(self.filename) > 30:
                dots = "..."
            help_text += f"<br/><code><i>({dots}{self.filename[-30:]})</i></code>"

        allt = [
            "<table>",
            "<tr>",
            "<td>",
            image,
            "</td>",
            "<td style='text-align: center; vertical-align: center;'><br/>",
            help_text,
            "<table>",
            "<tr><td><b> nr. of objects </b></td><td>"
            + str(self.GetNumberOfPaths())
            + "</td></tr>",
            "<tr><td><b> position </b></td><td>" + str(self.GetPosition()) + "</td></tr>",
            "<tr><td><b> diagonal size </b></td><td>"
            + vedo.utils.precision(self.diagonal_size(), 5)
            + "</td></tr>",
            "<tr><td><b> bounds </b> <br/> (x/y/z) </td><td>" + str(bounds) + "</td></tr>",
            "</table>",
            "</table>",
        ]
        return "\n".join(allt)

    def __add__(self, obj):
        """
        Add an object to the assembly
        """
        if isinstance(obj, vtk.get_class("Prop3D")):

            self.objects.append(obj)
            self.actors.append(obj.actor)
            self.AddPart(obj.actor)

            if hasattr(obj, "scalarbar") and obj.scalarbar is not None:
                if self.scalarbar is None:
                    self.scalarbar = obj.scalarbar
                    return self

                def unpack_group(scalarbar):
                    if isinstance(scalarbar, Group):
                        return scalarbar.unpack()
                    else:
                        return scalarbar

                if isinstance(self.scalarbar, Group):
                    self.scalarbar += unpack_group(obj.scalarbar)
                else:
                    self.scalarbar = Group([unpack_group(self.scalarbar), unpack_group(obj.scalarbar)])
            self.pipeline = vedo.utils.OperationNode("add mesh", parents=[self, obj], c="#f08080")
        return self

    def __contains__(self, obj):
        """Allows to use `in` to check if an object is in the `Assembly`."""
        return obj in self.objects


    def apply_transform(self, LT, concatenate=True):
        """Apply a linear transformation to the object."""
        if concatenate:
            self.transform.concatenate(LT)
        self.SetPosition(self.transform.T.GetPosition())
        self.SetOrientation(self.transform.T.GetOrientation())
        self.SetScale(self.transform.T.GetScale())
        return self

    # TODO ####
    # def propagate_transform(self):
    #     """Propagate the transformation to all parts."""
    #     # navigate the assembly and apply the transform to all parts
    #     # and reset position, orientation and scale of the assembly
    #     for i in range(self.GetNumberOfPaths()):
    #         path = self.GetPath(i)
    #         obj = path.GetLastNode().GetViewProp()
    #         obj.SetUserTransform(self.transform.T)
    #         obj.SetPosition(0, 0, 0)
    #         obj.SetOrientation(0, 0, 0)
    #         obj.SetScale(1, 1, 1)
    #     raise NotImplementedError()


    def pos(self, x=None, y=None, z=None):
        """Set/Get object position."""
        if x is None:  # get functionality
            return self.transform.position

        if z is None and y is None:  # assume x is of the form (x,y,z)
            if len(x) == 3:
                x, y, z = x
            else:
                x, y = x
                z = 0
        elif z is None:  # assume x,y is of the form x, y
            z = 0

        q = self.transform.position
        LT = LinearTransform().translate([x,y,z]-q)
        return self.apply_transform(LT)

    def shift(self, dx, dy=0, dz=0):
        """Add a vector to the current object position."""
        if vedo.utils.is_sequence(dx):
            vedo.utils.make3d(dx)
            dx, dy, dz = dx
        LT = LinearTransform().translate([dx, dy, dz])
        return self.apply_transform(LT)

    def scale(self, s):
        """Multiply object size by `s` factor."""
        LT = LinearTransform().scale(s)
        return self.apply_transform(LT)

    def x(self, val=None):
        """Set/Get object position along x axis."""
        p = self.transform.position
        if val is None:
            return p[0]
        self.pos(val, p[1], p[2])
        return self

    def y(self, val=None):
        """Set/Get object position along y axis."""
        p = self.transform.position
        if val is None:
            return p[1]
        self.pos(p[0], val, p[2])
        return self

    def z(self, val=None):
        """Set/Get object position along z axis."""
        p = self.transform.position
        if val is None:
            return p[2]
        self.pos(p[0], p[1], val)
        return self

    def rotate_x(self, angle):
        """Rotate object around x axis."""
        LT = LinearTransform().rotate_x(angle)
        return self.apply_transform(LT)

    def rotate_y(self, angle):
        """Rotate object around y axis."""
        LT = LinearTransform().rotate_y(angle)
        return self.apply_transform(LT)

    def rotate_z(self, angle):
        """Rotate object around z axis."""
        LT = LinearTransform().rotate_z(angle)
        return self.apply_transform(LT)

    def reorient(self, old_axis, new_axis, rotation=0, rad=False):
        """Rotate object to a new orientation."""
        if rad:
            rotation *= 57.3
        axis = old_axis / np.linalg.norm(old_axis)
        direction = new_axis / np.linalg.norm(new_axis)
        angle = np.arccos(np.dot(axis, direction)) * 57.3
        self.RotateZ(rotation)
        a,b,c = np.cross(axis, direction)
        self.RotateWXYZ(angle, c,b,a)
        return self

    def bounds(self):
        """
        Get the object bounds.
        Returns a list in format `[xmin,xmax, ymin,ymax, zmin,zmax]`.
        """
        return self.GetBounds()

    def xbounds(self, i=None):
        """Get the bounds `[xmin,xmax]`. Can specify upper or lower with i (0,1)."""
        b = self.bounds()
        if i is not None:
            return b[i]
        return (b[0], b[1])

    def ybounds(self, i=None):
        """Get the bounds `[ymin,ymax]`. Can specify upper or lower with i (0,1)."""
        b = self.bounds()
        if i == 0:
            return b[2]
        if i == 1:
            return b[3]
        return (b[2], b[3])

    def zbounds(self, i=None):
        """Get the bounds `[zmin,zmax]`. Can specify upper or lower with i (0,1)."""
        b = self.bounds()
        if i == 0:
            return b[4]
        if i == 1:
            return b[5]
        return (b[4], b[5])
    
    def diagonal_size(self):
        """Get the diagonal size of the bounding box."""
        b = self.bounds()
        return np.sqrt((b[1]-b[0])**2 + (b[3]-b[2])**2 + (b[5]-b[4])**2)

    def use_bounds(self, value):
        """Consider object bounds in rendering."""
        self.SetUseBounds(value)
        return self


    def copy(self):
        """Return a copy of the object. Alias of `clone()`."""
        return self.clone()

    def clone(self):
        """Make a clone copy of the object."""
        newlist = []
        for a in self.objects:
            newlist.append(a.clone())
        return Assembly(newlist)

    def unpack(self, i=None):
        """Unpack the list of objects from a `Assembly`.

        If `i` is given, get `i-th` object from a `Assembly`.
        Input can be a string, in this case returns the first object
        whose name contains the given string.

        Examples:
            - [custom_axes4.py](https://github.com/marcomusy/vedo/tree/master/examples/pyplot/custom_axes4.py)
        """
        if i is None:
            return self.objects
        elif isinstance(i, int):
            return self.objects[i]
        elif isinstance(i, str):
            for m in self.objects:
                if i in m.name:
                    return m

    def recursive_unpack(self):
        """Flatten out an Assembly."""

        def _genflatten(lst):
            if not lst:
                return []
            ##
            if isinstance(lst[0], Assembly):
                lst = lst[0].unpack()
            ##
            for elem in lst:
                if isinstance(elem, Assembly):
                    apos = elem.GetPosition()
                    asum = np.sum(apos)
                    for x in elem.unpack():
                        if asum:
                            yield x.clone().shift(apos)
                        else:
                            yield x
                else:
                    yield elem

        return list(_genflatten([self]))


    def pickable(self, value=True):
        """Set/get the pickability property of an assembly and its elements"""
        self.SetPickable(value)
        # set property to each element
        for elem in self.recursive_unpack():
            elem.pickable(value)
        return self

    def show(self, **options):
        """
        Create on the fly an instance of class `Plotter` or use the last existing one to
        show one single object.

        This method is meant as a shortcut. If more than one object needs to be visualised
        please use the syntax `show(mesh1, mesh2, volume, ..., options)`.

        Returns the `Plotter` class instance.
        """
        return vedo.plotter.show(self, **options)

