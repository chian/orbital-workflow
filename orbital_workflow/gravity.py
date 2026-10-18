"""Fixed gravitational sources: one point mass or an exact circular binary.

G=1. A binary's two massive sources follow their mutual Newtonian circular
solution about the barycenter. The test spaceship has no backreaction.
"""
from dataclasses import asdict, dataclass
import math
from numbers import Real


def finite(value):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError('Gravity parameters require finite real numbers')
    return float(value)


@dataclass(frozen=True)
class GravitySystem:
    kind: str = 'single'
    masses: tuple[float, ...] = (1.0,)
    separation: float = 0.0
    phase: float = 0.0
    collision_radii: tuple[float, ...] = (0.0,)

    def __post_init__(self):
        if self.kind not in ('single','circular_binary'):
            raise ValueError('Unknown gravity system')
        for name in ('masses','collision_radii'):
            object.__setattr__(self,name,tuple(finite(v) for v in getattr(self,name)))
        for name in ('separation','phase'):
            object.__setattr__(self,name,finite(getattr(self,name)))
        count=1 if self.kind=='single' else 2
        if len(self.masses)!=count or len(self.collision_radii)!=count:
            raise ValueError('Each attractor requires a mass and collision radius')
        if any(m<=0 for m in self.masses) or any(r<0 for r in self.collision_radii):
            raise ValueError('Masses must be positive and collision radii nonnegative')
        if self.kind=='single' and self.separation!=0:
            raise ValueError('Single source has zero separation')
        if self.kind=='circular_binary' and (self.separation<=0 or sum(self.collision_radii)>=self.separation):
            raise ValueError('Binary sources require positive separation and disjoint surfaces')

    @classmethod
    def from_record(cls,value):
        return value if isinstance(value,cls) else cls(**value)

    @property
    def body_ids(self):return tuple('body_'+str(i+1) for i in range(len(self.masses)))

    @property
    def angular_speed(self):
        return math.sqrt(sum(self.masses)/self.separation**3) if self.kind=='circular_binary' else 0.0

    def sources(self,time):
        angle=self.phase+self.angular_speed*time
        c,s=math.cos(angle),math.sin(angle)
        radii=(0.0,) if self.kind=='single' else (
            -self.separation*self.masses[1]/sum(self.masses),self.separation*self.masses[0]/sum(self.masses))
        return [{'id':name,'mass':mass,'collision_radius':surface,
                 'position':[radius*c,radius*s],
                 'velocity':[-self.angular_speed*radius*s,self.angular_speed*radius*c]}
                for name,mass,surface,radius in zip(self.body_ids,self.masses,self.collision_radii,radii)]

    def acceleration(self,time,x,y,active_bodies=None,mode='resolved'):
        active=set(self.body_ids if active_bodies is None else active_bodies)
        if mode=='monopole':
            sources=[{'mass':sum(m for name,m in zip(self.body_ids,self.masses) if name in active),'position':[0,0]}]
        else:sources=[body for body in self.sources(time) if body['id'] in active]
        ax=ay=0.0
        for body in sources:
            dx,dy=x-body['position'][0],y-body['position'][1]
            radius=math.hypot(dx,dy)
            if radius==0:raise ValueError('Point-mass field is singular at a source')
            factor=-body['mass']/radius**3
            ax+=factor*dx;ay+=factor*dy
        return ax,ay

    def as_record(self):return asdict(self)


def source_model(gravity,active_bodies=None,mode='resolved'):
    gravity=GravitySystem.from_record(gravity)
    active=set(gravity.body_ids if active_bodies is None else active_bodies)
    if not active:return 'bodies:0'
    if mode=='monopole' and gravity.kind!='single':return 'monopole'
    return 'bodies:'+str(sum(1<<i for i,name in enumerate(gravity.body_ids) if name in active))


def scenario_problem(settings):
    supplied=settings.get('scenario',{})
    return {'id':supplied.get('id','scenario_01'), 'name':supplied.get('name','Single gravitational attractor'),
            'initial_position':supplied.get('initial_position',[1.0,0.0]),
            'reference_velocity':supplied.get('reference_velocity',[0.0,1.0]),
            'radial_limits':supplied.get('radial_limits',[0.5,2.0]),
            'suggested_a':supplied.get('suggested_a',.15),'suggested_sigma':supplied.get('suggested_sigma',.03),
            'gravity':GravitySystem.from_record(supplied.get('gravity',{})).as_record()}
