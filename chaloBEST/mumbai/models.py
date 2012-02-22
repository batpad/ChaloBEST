from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
import json

STOP_CHOICES = ( ('U','Up'),
                 ('D', 'Down'),
                 )

DAYS = {
    1: 'Monday',
    2: 'Tuesday',
    3: 'Wednesday',
    4: 'Thursday',
    5: 'Friday',
    6: 'Saturday',
    7: 'Sunday',
    8: 'Holiday'
    }

SCHED = {
    'MS':[1,2,3,4,5,6], 
    'HOL':[8], 
    'SUN':[7], 
    'MF&HOL':[1,2,3,4,5,8],  
    'SAT':[6], 
    'MF':[1,2,3,4,5], 
    'SH':[7,8], 
    'AD':[1,2,3,4,5,6,7,8], 
    'SAT&SUN':[6,7], 
    'MS&HOL':[1,2,3,4,5,6,8], 
    'FW':[1,2,3,4,5,6,7], 
    'SAT/SH':[6,7,8], 
    'FH':['???'], 
    'SAT&HOL':[6,8], 
    'SAT&SH':[6,7,8], 
    'SAT/SUND&HOL':[6,7,8], 
    'S/H':[7,8], 
    'SAT,SUN&HOL':[6,7,8], 
    '2nd &4th':['???']
    }

class Area(models.Model):
    code = models.IntegerField() #primary_key=True)
    slug = models.SlugField(null=True)
    name = models.TextField(blank=True, max_length=255)
    name_mr= models.TextField(null=True, blank=True, max_length=512) #null=True, 
    display_name = models.TextField(blank=True, max_length=255)
    geometry = models.PolygonField(blank=True, null=True)
    alt_names = generic.GenericRelation("AlternativeName")

    def get_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'slug': self.slug,
            'name': self.name,
            'name_mr': self.name_mr,
            'display_name': self.display_name
            #FIXME add alt_names and geometry
        }

    def get_absolute_url(self):
        return "/area/%s/" % self.name

    def __unicode__(self):
        return self.name   
    
class Road(models.Model):
    code = models.IntegerField()#primary_key=True)
    slug = models.SlugField(null=True)
    name = models.TextField(blank=True, max_length=255)
    name_mr= models.TextField(null=True, blank=True, max_length=512)
    display_name = models.TextField(blank=True, max_length=255)
    geometry = models.LineStringField(blank=True, null=True)
    alt_names = generic.GenericRelation("AlternativeName")

    def __unicode__(self):
        return self.name   


class Fare(models.Model):
    slab = models.DecimalField(max_digits=5, decimal_places=2) 
    ordinary = models.PositiveIntegerField()
    limited = models.PositiveIntegerField()
    express = models.PositiveIntegerField()
    ac = models.PositiveIntegerField()
    ac_express = models.PositiveIntegerField()
    def __unicode__(self):
        return str(self.slab)   


class Stop(models.Model):
    code = models.IntegerField()
    slug = models.SlugField(null=True)
    name = models.TextField(blank=True, max_length=255)
    display_name = models.TextField(blank=True, max_length=255)
    dbdirection = models.CharField(null=True, blank=True, max_length=5, choices=STOP_CHOICES) #stopfl - > direction
    chowki = models.NullBooleanField(null=True, blank=True) # this is nullable since in the next datafeed , they might have blank to represent a 0.
    road = models.ForeignKey(Road, default=None, null=True, blank=True)
    area = models.ForeignKey(Area, default=None, null=True, blank=True)
    depot = models.ForeignKey("Depot", default=None, null=True, blank=True, related_name="is_depot_for") #models.CharField(null=True, blank=True, max_length=5)
    name_mr= models.TextField(null=True, blank=True, max_length=512)#null=True, 

    point = models.PointField(null=True)
    alt_names = generic.GenericRelation("AlternativeName")

    def get_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'slug': self.slug,
            'official_name': self.name,
            'display_name': self.display_name,
            'road': self.road.name,
            'area': self.area.name,
            'name_mr': self.name_mr,
            'routes': ", ".join([r.route.alias for r in RouteDetail.objects.filter(stop=self)]),
            'alternative_names': ", ".join([a.name for a in self.alt_names.all().filter(typ='common')])
        }

    def get_geojson(self, srid=4326):
        print srid
        if self.point is not None:
            geom = json.loads(self.point.transform(srid, True).geojson)
        else:
            geom = {}

        properties = self.get_dict()

        return {
            'type': 'Feature',
            'properties': properties,
            'geometry': geom
        }        

    def from_geojson(self, geojson, srid=4326):
        geom = geojson['geometry']['coordinates']
        data = geojson['properties']
        self.point = Point(geom[0], geom[1], srid=srid).transform(4326, True) #FIXME: srid should be passed as param
        self.display_name = data['display_name']
        self.name_mr = data['name_mr']
        if data.has_key('alternative_names') and data['alternative_names'].strip() != '':
            for a in self.alt_names.all():
                a.delete()
            for a in data['alternative_names'].split(","):
                alt_name = AlternativeName()
                alt_name.name = a
                alt_name.typ = 'common'
                alt_name.content_object = self
                alt_name.save()
                self.alt_names.add(alt_name)    
            
        #FIXME: add alt names logic
        self.save()
        return self.get_geojson(srid=srid)


    def __unicode__(self):
        return self.name   

    ''' 
    check if point exists for stop
    '''
    def has_point(self):        
        if self.stoplocation_set.all():
            return True
        else:
            return False
        
    has_point.boolean = True

    def get_absolute_url(self):
        return "/admin/mumbai/stop/%d/" % self.id


class Route(models.Model):
    code = models.TextField(max_length=255, unique=True)
    slug = models.SlugField(null=True)
    alias = models.TextField(max_length=255)
    from_stop_txt = models.TextField(max_length=500)
    to_stop_txt = models.TextField(max_length=500)
    from_stop = models.ForeignKey(Stop, related_name='routes_from', default=None, null=True, blank=True)
    to_stop = models.ForeignKey(Stop, related_name='routes_to', default=None, null=True, blank=True)
    distance = models.DecimalField(max_digits=3, decimal_places=1)
    stages =  models.IntegerField()

    def get_absolute_url(self):
        return "/route/%s/" % self.alias

    def __unicode__(self):
        return self.alias

    def get_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'alias': self.alias,
            'slug': self.slug,
            'distance': str(self.distance)
        }

class RouteDetail(models.Model):
    route_code = models.TextField()
    route = models.ForeignKey(Route, to_field="code", null=True, blank=True)
    serial = models.PositiveIntegerField()
    stop = models.ForeignKey(Stop, null=True, blank=True)
    stage =  models.NullBooleanField()
    km  = models.DecimalField(null=True, blank=True, max_digits=3, decimal_places=1)

    class Meta:
        verbose_name = 'Route Detail'
        ordering = ['serial'] 

    def __unicode__(self):
        return str(self.route) + " : " + str(self.serial)


class UniqueRoute(models.Model):
    route = models.ForeignKey(Route)
    from_stop_txt = models.CharField(max_length=255)
    to_stop_txt = models.CharField(max_length=255)
    from_stop = models.ForeignKey(Stop, related_name="unique_routes_from")
    to_stop = models.ForeignKey(Stop, related_name="unique_routes_to")
    distance = models.FloatField(blank=True, null=True)
    is_full = models.BooleanField()

    class Meta:
        verbose_name = 'Atlas'
        verbose_name_plural = 'Atlas'
        
    def __unicode__(self):
        return "%s: %s to %s" % (self.route.alias, self.from_stop_txt, self.to_stop_txt)


class RouteSchedule(models.Model):
    unique_route = models.ForeignKey(UniqueRoute)
    schedule_type = models.CharField(max_length=16)
    busesAM = models.IntegerField(blank=True, null=True)
    busesN = models.IntegerField(blank=True, null=True)
    busesPM = models.IntegerField(blank=True, null=True)
    bus_type = models.CharField(max_length=3, default="SD")
    depot_txt = models.CharField(max_length=16, blank=True)
    depot = models.ForeignKey("Depot", null=True)
    first_from = models.TimeField(blank=True, null=True)
    last_from = models.TimeField(blank=True, null=True)
    first_to = models.TimeField(blank=True, null=True)
    last_to = models.TimeField(blank=True, null=True)
    runtime1 = models.IntegerField(blank=True, null=True)
    runtime2 = models.IntegerField(blank=True, null=True)
    runtime3 = models.IntegerField(blank=True, null=True)
    runtime4 = models.IntegerField(blank=True, null=True)
    headway1 = models.IntegerField(blank=True, null=True)
    headway2 = models.IntegerField(blank=True, null=True)
    headway3 = models.IntegerField(blank=True, null=True)
    headway4 = models.IntegerField(blank=True, null=True)
    headway5 = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
        return "%s: %s" % (unicode(self.unique_route), self.schedule_type,)


class RouteType(models.Model):
    code = models.TextField(max_length=50)
    rtype = models.TextField(max_length=50)
    faretype = models.TextField(max_length=10)

    def __unicode__(self):
        return self.rtype   

    class Meta:
        verbose_name = 'Route Type'


class HardCodedRoute(models.Model):
    code = models.TextField(max_length=50)    
    alias = models.TextField(max_length=50)
    faretype = models.TextField(max_length=10)

    class Meta:
        verbose_name = 'Hardcoded Route'

    def __unicode__(self):
        return self.code + " " +self.alias   


class Landmark(models.Model):
    slug = models.SlugField(null=True)
    name = models.TextField(max_length=500, blank=True, null=True)
    stops = models.ManyToManyField(Stop, related_name='is_near_to', blank=True)
    name_mr = models.TextField(max_length=512, blank=True, null=True)
    display_name = models.TextField(blank=True, max_length=255)
    point = models.PointField(blank=True, null=True)
    alt_names = generic.GenericRelation("AlternativeName")

    def __unicode__(self):
        return self.name 


class StopLocation(models.Model):
    stop = models.ForeignKey(Stop)
    point = models.PointField()
    direction = models.CharField(max_length=5, null=True, blank=True, choices=STOP_CHOICES)

    def __unicode__(self):
        return self.stop.name 


class Depot(models.Model):
    code = models.CharField(max_length=5)
    name = models.TextField(max_length=50)
    stop = models.IntegerField()


    def __unicode__(self):
        return self.name 


class Holiday(models.Model):
    date = models.DateField()
    name = models.TextField(max_length=100)

    def __unicode__(self):
        return self.name 
    

ALT_TYPE_CHOICES = (
    ('alt', 'General Alternative Name'),
    ('old', 'Old Name'),
    ('common', 'Common Name')
)

class AlternativeName(models.Model):
    name = models.CharField(max_length=512)
    name_mr = models.CharField(max_length=512, blank=True)
    typ = models.CharField(max_length=64, choices=ALT_TYPE_CHOICES, default="alt")
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')    

    def __unicode__(self):
        return self.name
