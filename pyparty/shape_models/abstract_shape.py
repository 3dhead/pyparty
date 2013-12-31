"""
Shape Models API
================

This module stores abstract base classes for Particle models.

"""
import logging
import numpy as np
from math import radians, cos

from traits.has_traits import CHECK_INTERFACES
from traits.api import Interface, implements, HasTraits, Tuple, Array, \
     Bool, Property, Str, Int, Instance, Range, Float, cached_property

import skimage.draw as draw
from skimage.measure import regionprops
from skimage.measure._regionprops import _RegionProperties

from pyparty.config import RADIUS_DEFAULT, CENTER_DEFAULT
from pyparty.utils import rr_cc_box
from pyparty.trait_types.intornone import IntOrNone
from pyparty.patterns.elements import simple

logger = logging.getLogger(__name__) 
CHECK_INTERFACES = 2    

class ParticleError(Exception):
    """ """

class ParticleInterface(Interface):
    """ Abstract class for storing particles as light objects which return
        rr and cc indicies for ndarray indexing (see skimage.draw) 
    
    Attributes
    ----------
    
    ptype : str
       Descriptor, used by ParticleManager and other classes
       to segregate out particle types.
       
    Notes
    -----
    Only traits in the contstructor (eg 'foo' vs. Str('foo') and public 
    and public methods (eg foo() vs. _foo()) will be recognized when 
    implementation is enforced.
       
    """

    ptype = Str('')
    psource = Str('')

    def _get_rr_cc(self):
        raise NotImplementedError
     
class Particle(HasTraits):

    implements(ParticleInterface)
    ptype = Str('general')    

    psource = Str('pyparty_builtin')
    fill = Bool(True)
    aa = Bool(False) #Anti Aliasing

    # Remove with implementation
    rr_cc = Property(Array)    
    ski_descriptor = Instance(_RegionProperties)
       
    #http://scikit-image.org/docs/dev/api/skimage.draw.html#circle
    def _get_rr_cc(self):
        raise NotImplementedError

    def _set_rr_cc(self):
        raise NotImplementedError
        
    # May want this to return the translation coordinates
    def boxed(self):
        """ Returns a binary bounding box with object inside"""
        return rr_cc_box(self.rr_cc)
    
    def ski_descriptor(self, attr):
        """ Return scikit image descriptor. """
        # Set RegionProps on first call
        if not hasattr(self, '_ski_descriptor'):                     #TEST IF FASTER W/ TRUE
            self._ski_descriptor = regionprops(self.boxed(), cache=True)[0]
        return getattr(self._ski_descriptor, attr)


class CenteredParticle(Particle):
    """ Base class for particles whose centers are set by user (circle,
        elipse, etc...) as opposed to particles whose center is computed
        after the object is drawn (eg line, beziercurve, polygon)
    """
    
    implements(ParticleInterface)
    pytpe = Str('abstract_centered')
    
    # CENTER = (CX, CY)  not (CY, CX)
    center = Tuple( CENTER_DEFAULT ) # in pixels 
    cx = Property(Int, depends_on = 'center')
    cy = Property(Int, depends_on = 'center')    

    # Center Property Interface
    # ----------------
    def _get_cx(self):
        return self.center[0]
    
    def _get_cy(self):
        return self.center[1]
    
    def _set_cx(self, value):
        self.center = (value, self.cy)
        
    def _set_cy(self, value):
        self.center = (self.cx, value)    


class SimplePattern(CenteredParticle):
    """  
         
    Notes
    -----
    Base class to wrap patterns.elements.simple.  Mainly implemented to reduce
    boilderplate.  _offangle is the angle between a line conncecting particle 
    centers vs. a line connecting the center of a paritcle to the center of the 
    object.  For a dimer, obviously, this is 0 (ie the same).  The cosine 
    between them is important for ensuring the partciles are not touching unless
    overlap is specificed."""
    
    implements(ParticleInterface)            
    ptype = Str('abstract_simple_element')    
        
    radius_1 = Int(RADIUS_DEFAULT)
    radius_2 = IntOrNone #defaults to None
    radius_3 = IntOrNone
    radius_4 = IntOrNone
    rs = Property(Array, depends_on = 'radius_1, radius_2, radius_3, radius_4')
    
    overlap = Range(0.0, 1.0)
    orientation = Float(0.0) #In degrees  
    skeleton = Property()    
    
    _offangle = Float(0.0)
    _n = Int(4)
    
    
    def _get_skeleton(self, old, new):
        rs = (1.0 - self.overlap) * (self.rs / cos(radians(self._offangle)))
        return simple(self.cx, self.cy, rs,  phi=self.orientation)
    
    def draw_skeleton(self):
        """ Would like to draw lines connecting verticies returned from skeleton.
            From center.  So line(center, r1) line(center, r2)"""
        raise NotImplementedError
    
    @cached_property
    def _get_rs(self):
        """ Returns current values of radius 1-4; if any of 2,3,4 is None,
        returns the value of r1"""
        
        r1 = self.radius_1
        r2, r3, r4 = r1, r1, r1
        
        if self.radius_2:
            r2 = self.radius_2

        if self.radius_3:
            r3 = self.radius_3

        if self.radius_4:
            r4 = self.radius_4
            
        return np.array( (r1, r2, r3, r4) )[0:self._n]

    def _get_rr_cc(self):
        """ Draws circle for each vertex pair returned by self.skeleton, then
        concatenates them in a final (rr, cc) array. """

        rr_all = []
        cc_all = []
        for idx, (vx, vy) in enumerate(self.skeleton):
            rs, cs = draw.circle( vy, vx, self.rs[idx] )
            rr_all.append(rs)
            cc_all.append(cs)
        
        rr = np.concatenate( rr_all )
        cc = np.concatenate( cc_all )
        return (rr, cc)

if __name__ == '__main__':
    p=Particle()

    