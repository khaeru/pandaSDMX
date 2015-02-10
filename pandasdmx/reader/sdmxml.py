# encoding: utf-8


from pandasdmx.utils import DictLike, namedtuple_factory
from pandasdmx import model
from .common import Reader
from lxml import objectify
from lxml.etree import XPath
from itertools import repeat


 
class SDMXMLReader(Reader):

    
    """
    Read SDMX-ML 2.1 and expose it as instances from pandasdmx.model
    """
    
    _nsmap = {
            'com' : 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common',
            'str' : 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure',
            'mes' : 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message',
    'gen' : 'http://www.sdmx.org/resources/sdmxml/schemas/v2_1/data/generic'
    }

    def initialize(self, source):
        root = objectify.parse(source).getroot()
        self.root = root
        if root.tag.endswith('Structure'):
            cls = model.StructureMessage
        elif (root.tag.endswith('GenericData') 
              or root.tag.endswith('GenericTimeSeriesData')):
            cls = model.GenericDataMessage
        elif (root.tag.endswith('StructureSpecificData') 
              or root.tag.endswith('StructureSpecificTimeSeriesData')):
            cls = model.StructureSpecificDataMessage
        else: raise ValueError('Unsupported root tag: %s' % root.tag)
        self.message = cls(self, root)  
        return self.message 
    
    
    def get_dataset(self, elem):
        if 'Generic' in self.root.tag: 
            cls = model.GenericDataSet
        elif 'StructureSpecific' in self.root.tag: 
            cls = model.StructureSpecificDataSet
        else: raise ValueError('Message for datasets has tag %s' % elem.tag)
        return cls(self, elem)  
        
      
    # Map names to pairs of compiled xpath expressions and callables
    # to be called by read methods. Callable must accept the same args as
    # model.SDMXObject. In most cases it will be a model class so that 
    # read methods return a model class instance. But it may also be a staticmethod if the
    # class selection is more involved (see the method get_dataset above). If 
    # callable is None, the result of the xpath expressions is returned
    # unchanged. This is useful for strings as attribute values. 
    _model_map = {
        'header' : (XPath('mes:Header', namespaces = _nsmap), model.Header),
        'footer' : (XPath('mes:Footer', namespaces = _nsmap), model.Footer), 
        'annotations' : (XPath('com:Annotations/com:Annotation', 
                             namespaces = _nsmap), model.Annotation),
        'annotationtype' : (XPath('com:AnnotationType/text()', namespaces = _nsmap), None),
        'codelists' : (XPath('mes:Structures/str:Codelists/str:Codelist', 
                             namespaces = _nsmap), model.Codelist),
                  'codes': (XPath('str:Code', 
                             namespaces = _nsmap), model.Code),  
                  'conceptschemes' : (XPath('mes:Structures/str:Concepts/str:ConceptScheme', 
                             namespaces = _nsmap), model.ConceptScheme),
        'concepts' : (XPath('str:Concept', 
                             namespaces = _nsmap), model.Concept),
        'categoryschemes' : (XPath('mes:Structures/str:CategorySchemes/str:CategoryScheme', 
                             namespaces = _nsmap), model.CategoryScheme),
        'categories': (XPath('str:Category', 
                             namespaces = _nsmap), model.Category),  
        'dataflows' : (XPath('mes:Structures/str:Dataflows/str:Dataflow', 
                             namespaces = _nsmap), model.DataflowDefinition),
        'datastructures' : (XPath('mes:Structures/str:DataStructures/str:DataStructure', 
                             namespaces = _nsmap), model.DataStructureDefinition),
        'dimdescriptor' : (XPath('str:DataStructureComponents/str:DimensionList', 
                             namespaces = _nsmap), model.DimensionDescriptor),
        'dimensions': (XPath('str:Dimension', 
                             namespaces = _nsmap), model.Dimension),
        'time_dimension': (XPath('str:TimeDimension', 
                             namespaces = _nsmap), model.TimeDimension),
        'measure_dimension': (XPath('str:MeasureDimension', 
                             namespaces = _nsmap), model.MeasureDimension),
        'measures' : (XPath('str:DataStructureComponents/str:MeasureList', 
                             namespaces = _nsmap), model.MeasureDescriptor),
        'measure_items' : (XPath('str:PrimaryMeasure', 
                             namespaces = _nsmap), model.PrimaryMeasure), 
        'attributes' : (XPath('str:DataStructureComponents/str:AttributeList', 
                             namespaces = _nsmap), model.AttributeDescriptor),
                  'attribute_items' : (XPath('str:Attribute', 
                             namespaces = _nsmap), model.DataAttribute),
                  'data' : (XPath('mes:DataSet', 
                             namespaces = _nsmap), get_dataset),
            'structured_by'
             : (XPath('mes:Structure/@structureID', 
                                            namespaces = _nsmap), None),
            'dim_at_obs' : (XPath('mes:Structure/@dimensionAtObservation', 
                                            namespaces = _nsmap), None),
            'generic_series' : (XPath('gen:Series', 
                             namespaces = _nsmap), model.Series),
    } 
        
        
    def read_one(self, name, sdmxobj):
        '''
        return model class instance of the first element in the
        result set of the xpath expression as defined in _model_map. If no elements are found,
        return None. If no model class is given in _model_map, 
        return result unchanged.
        '''
        path, cls = self._model_map[name]
        try:
            result = path(sdmxobj._elem)[0]
            if cls: return cls(self, result)
            else: return result 
        except IndexError:
            return None
     
    def read_iter(self, name, sdmxobj):
        '''
        return iterator of model class instances of elements in the
        result set of the xpath expression as defined in _model_map. 
        '''
        path, cls = self._model_map[name]
        return map(cls, repeat(self), path(sdmxobj._elem))
     

    def read_identifiables(self, name, sdmxobj):
        '''
        If sdmxobj inherits from dict: update it  with modelized elements. 
        These must be instances of model.IdentifiableArtefact,
        i.e. have an 'id' attribute. This will be used as dict keys.
        If sdmxobj does not inherit from dict: return a new DictLike. 
        '''
        path, cls = self._model_map[name]
        result = {e.get('id') : cls(self, e) for e in path(sdmxobj._elem)}
        if isinstance(sdmxobj, dict): sdmxobj.update(result)
        else: return DictLike(result)
        

    def header_id(self, sdmxobj):
        return sdmxobj._elem.ID[0].text 

    def identity(self, sdmxobj):
        return sdmxobj._elem.get('id')
    
    def urn(self, sdmxobj):
        return sdmxobj._elem.get('urn')

    def uri(self, sdmxobj):
        return sdmxobj._elem.get('uri')
        
        
    def agencyID(self, sdmxobj):
        return sdmxobj._elem.get('agencyID')
    
    
    def international_str(self, name, sdmxobj):
        '''
        return DictLike of xml:lang attributes. If node has no attributes,
        assume that language is 'en'.
        '''
        # Get language tokens like 'en', 'fr'...
        # Can we simplify the xpath expressions by not using .format?
        elem_attrib = sdmxobj._elem.xpath('com:{0}/@xml:lang'.format(name), 
                               namespaces = self._nsmap)
        values = sdmxobj._elem.xpath('com:{0}/text()'.format(name), 
                             namespaces = self._nsmap)
        # Unilingual strings have no attributes. Assume 'en' instead.
        if not elem_attrib:
            elem_attrib = ['en']
        return DictLike(zip(elem_attrib, values))

    def header_prepared(self, sdmxobj):
        return sdmxobj._elem.Prepared[0].text # convert this to datetime obj?
        
    def header_sender(self, sdmxobj):
        return DictLike(sdmxobj._elem.Sender.attrib)

    def header_error(self, sdmxobj):
        try:
            return DictLike(sdmxobj._elem.Error.attrib)
        except AttributeError: return None
                     
        
    def isfinal(self, sdmxobj):
        return bool(sdmxobj._elem.get('isFinal')) 
        
    def concept_id(self, sdmxobj):
        # called by model.Component.concept
        c_id = sdmxobj._elem.xpath('str:ConceptIdentity/Ref/@id', 
                          namespaces = self._nsmap)[0]
        parent_id = sdmxobj._elem.xpath('str:ConceptIdentity/Ref/@maintainableParentID',
                               namespaces = self._nsmap)[0]
        return self.message.conceptschemes[parent_id][c_id]
        
    def position(self, sdmxobj):
        # called by model.Dimension
        return int(sdmxobj._elem.get('position')) 
    
    def localrepr(self, sdmxobj):
        node = sdmxobj._elem.xpath('str:LocalRepresentation',
                          namespaces = self._nsmap)[0]
        enum = node.xpath('str:Enumeration/Ref/@id',
                          namespaces = self._nsmap)
        if enum: enum = self.message.codelists[enum[0]]
        else: enum = None
        return model.Representation(self, node, enum = enum)
    
    def assignment_status(self, sdmxobj):
        return sdmxobj._elem.get('assignmentStatus')
        
    def attr_relationship(self, sdmxobj):
        return sdmxobj._elem.xpath('*/Ref/@id')
    
    # Types and xpath expressions for generic observations
    _ObsTuple = namedtuple_factory('GenericObservation', ('key', 'value', 'attrib'))
    _SeriesObsTuple = namedtuple_factory('SeriesObservation', ('dim', 'value', 'attrib'))
    _generic_obs_path = XPath('gen:Obs', namespaces = _nsmap)
    _obs_key_id_path = XPath('gen:ObsKey/gen:Value/@id', namespaces = _nsmap)
    _obs_key_values_path = XPath('gen:ObsKey/gen:Value/@value', namespaces = _nsmap)
    _series_key_values_path = XPath('gen:SeriesKey/gen:Value/@value', namespaces = _nsmap)
    _series_key_id_path = XPath('gen:SeriesKey/gen:Value/@id', namespaces = _nsmap)
    _generic_series_dim_path = XPath('gen:ObsDimension/@value', namespaces = _nsmap)
    _obs_value_path = XPath('gen:ObsValue/@value', namespaces = _nsmap)
    _attr_id_path = XPath('gen:Attributes/gen:Value/@id', namespaces = _nsmap)
    _attr_values_path = XPath('gen:Attributes/gen:Value/@value', namespaces = _nsmap)
    
    def iter_generic_obs(self, sdmxobj, with_value, with_attributes):
        for obs in self._generic_obs_path(sdmxobj._elem):
            # Construct the namedtuple for the ObsKey. 
            # The namedtuple class is created on first iteration.
            obs_key_values = self._obs_key_values_path(obs)
            try:
                obs_key = ObsKeyTuple._make(obs_key_values)
            except NameError:
                obs_key_id = self._obs_key_id_path(obs)
                ObsKeyTuple = namedtuple_factory('ObsKey', obs_key_id)
                obs_key = ObsKeyTuple._make(obs_key_values)
            if with_value:
                obs_value = self._obs_value_path(obs)[0]
            else: obs_value = None
            if with_attributes:
                obs_attr_values = self._attr_values_path(obs)
                try:
                    obs_attr = ObsAttrTuple._make(obs_attr_values)
                except NameError:
                    obs_attr_id = self._attr_id_path(obs)
                    ObsAttrTuple = namedtuple_factory('ObsAttr', obs_attr_id)
                    obs_attr = ObsAttrTuple._make(obs_attr_values)
            else: obs_attr = None
            yield self._ObsTuple(obs_key, obs_value, obs_attr)  
    
                
    def generic_series(self, sdmxobj):
        path, cls = self._model_map['generic_series']
        for series in path(sdmxobj._elem):
            yield cls(self, series)
                        
    def series_key(self, sdmxobj):
        series_key_id = self._series_key_id_path(sdmxobj._elem)
        series_key_values = self._series_key_values_path(sdmxobj._elem)
        SeriesKeyTuple = namedtuple_factory('SeriesKey', series_key_id)
        return SeriesKeyTuple._make(series_key_values)

    def series_attrib(self, sdmxobj):
        series_attr_id = self._attr_id_path(sdmxobj._elem)
        series_attr_values = self._attr_values_path(sdmxobj._elem)
        SeriesAttrTuple = namedtuple_factory('Attributes', series_attr_id)
        return SeriesAttrTuple._make(series_attr_values)

    def iter_generic_series_obs(self, sdmxobj, with_value, with_attributes):
        for obs in self._generic_obs_path(sdmxobj._elem):
            obs_dim = self._generic_series_dim_path(obs)[0]
            if with_value:
                obs_value = self._obs_value_path(obs)[0]
            else: obs_value = None
            if with_attributes:
                obs_attr_values = self._attr_values_path(obs)
                try:
                    obs_attr = ObsAttrTuple._make(obs_attr_values)
                except NameError:
                    obs_attr_id = self._attr_id_path(obs)
                    ObsAttrTuple = namedtuple_factory('ObsAttr', obs_attr_id)
                    obs_attr = ObsAttrTuple._make(obs_attr_values)
            else: obs_attr = None
            yield self._SeriesObsTuple(obs_dim, obs_value, obs_attr)  
    