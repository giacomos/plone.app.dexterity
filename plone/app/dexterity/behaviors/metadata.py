from DateTime import DateTime
from datetime import datetime
from zope.interface import alsoProvides
from zope.component import adapts
from zope import schema
from plone.directives import form
from plone.dexterity.interfaces import IDexterityContent
from plone.autoform.interfaces import IFormFieldProvider

try:
    from z3c.form.browser.textlines import TextLinesFieldWidget
except ImportError:
    from plone.z3cform.textlines.textlines import TextLinesFieldWidget
# from collective.z3cform.datepicker.widget import DateTimePickerFieldWidget

# Behavior interfaces to display Dublin Core metadata fields on Dexterity
# content edit forms.
#     
# These schemata duplicate the fields of zope.dublincore.IZopeDublinCore,
# in order to annotate them with form hints and more helpful titles
# and descriptions.

class IBasic(form.Schema):
    # default fieldset
    title = schema.TextLine(
        title = u'Title',
        required = True
        )
        
    description = schema.Text(
        title = u'Summary',
        description = u'A short summary of the content.',
        required = False,
        )
    
    form.order_before(description = '*')
    form.order_before(title = '*')

class ICategorization(form.Schema):
    # categorization fieldset
    form.fieldset(
        'categorization',
        label=u'Categorization',
        fields=['subjects', 'language'],
        )

    subjects = schema.Tuple(
        title = u'Categories',
        description = u'Also known as keywords, tags or labels, these help you categorize your content.',
        value_type = schema.TextLine(),
        required = False,
        missing_value = (),
        )
    form.widget(subjects = TextLinesFieldWidget)

    language = schema.Choice(
        title = u'Language',
        vocabulary = 'plone.app.vocabularies.AvailableContentLanguages',
        required = False,
        missing_value = '',
        )

class IPublication(form.Schema):
    # dates fieldset
    form.fieldset(
        'dates',
        label=u'Dates',
        fields=['effective', 'expires'],
        )
    
    effective = schema.Datetime(
        title = u'Publishing Date',
        description = u'If this date is in the future, the content will not show up in listings and searches until this date.',
        required = False
        )
    # form.widget(effective = DateTimePickerFieldWidget)
        
    expires = schema.Datetime(
        title = u'Expiration',
        description = u'When this date is reached, the content will nolonger be visible in listings and searches.',
        required = False
        )
    # form.widget(expires = DateTimePickerFieldWidget)

class IOwnership(form.Schema):
    # ownership fieldset
    form.fieldset(
        'ownership',
        label=u'Ownership',
        fields=['creators', 'contributors', 'rights'],
        )

    creators = schema.Tuple(
        title = u'Creators',
        description = u'Persons responsible for creating the content of this item. Please enter a list of user names, one per line. The principal creator should come first.',
        value_type = schema.TextLine(),
        required = False,
        missing_value = (),
        )
    form.widget(creators = TextLinesFieldWidget)

    contributors = schema.Tuple(
        title = u'Contributors',
        description = u'The names of people that have contributed to this item. Each contributor should be on a separate line.',
        value_type = schema.TextLine(),
        required = False,
        missing_value = (),
        )
    form.widget(contributors = TextLinesFieldWidget)
    
    rights = schema.Text(
        title=u'Rights',
        description=u'Copyright statement or other rights information on this item.',
        required = False,
        )

class IDublinCore(IBasic, ICategorization, IPublication, IOwnership):
    """ Metadata behavior providing all the DC fields
    """
    pass

# Mark these interfaces as form field providers
alsoProvides(IBasic, IFormFieldProvider)
alsoProvides(ICategorization, IFormFieldProvider)
alsoProvides(IPublication, IFormFieldProvider)
alsoProvides(IOwnership, IFormFieldProvider)
alsoProvides(IDublinCore, IFormFieldProvider)

class MetadataBase(object):
    """ This adapter uses DCFieldProperty to store metadata directly on an object
        using the standard CMF DefaultDublinCoreImpl getters and setters.
    """
    adapts(IDexterityContent)
    
    def __init__(self, context):
        self.context = context

_marker = object()
class DCFieldProperty(object):
    """Computed attributes based on schema fields.
    Based on zope.schema.fieldproperty.FieldProperty.
    """

    def __init__(self, field, get_name=None, set_name=None):
        if get_name is None:
            get_name = field.__name__
        self._field = field
        self._get_name = get_name
        self._set_name = set_name

    def __get__(self, inst, klass):
        if inst is None:
            return self

        attribute = getattr(inst.context, self._get_name, _marker)
        if attribute is _marker:
            field = self._field.bind(inst)
            attribute = getattr(field, 'default', _marker)
            if attribute is _marker:
                raise AttributeError(self._field.__name__)
        elif callable(attribute):
            attribute = attribute()

        if isinstance(attribute, DateTime):
             return datetime(*map(int, attribute.parts()[:6]))
        return attribute

    def __set__(self, inst, value):
        field = self._field.bind(inst)
        field.validate(value)
        if field.readonly:
            raise ValueError(self._field.__name__, 'field is readonly')
        if isinstance(value, datetime):
            value = DateTime(value.isoformat())
        if self._set_name:
            getattr(inst.context, self._set_name)(value)
        elif inst.context.hasProperty(self._get_name):
            inst.context._updateProperty(self._get_name, value)
        else:
            setattr(inst.context, self._get_name, value)

    def __getattr__(self, name):
        return getattr(self._field, name)

class Basic(MetadataBase):
    title = DCFieldProperty(IBasic['title'], get_name = 'Title', set_name = 'setTitle')
    description = DCFieldProperty(IBasic['description'], get_name = 'Description', set_name = 'setDescription')
    
class Categorization(MetadataBase):
    subjects = DCFieldProperty(ICategorization['subjects'], get_name = 'Subject', set_name = 'setSubject')
    language = DCFieldProperty(ICategorization['language'], get_name = 'Language', set_name = 'setLanguage')
    
class Publication(MetadataBase):
    effective = DCFieldProperty(IPublication['effective'], get_name = 'effective', set_name = 'setEffectiveDate')
    expires = DCFieldProperty(IPublication['expires'], get_name = 'expires', set_name = 'setExpirationDate')

class Ownership(MetadataBase):
    creators = DCFieldProperty(IOwnership['creators'], get_name = 'listCreators', set_name = 'setCreators')
    contributors = DCFieldProperty(IOwnership['contributors'], get_name = 'Contributors', set_name = 'setContributors')
    rights = DCFieldProperty(IOwnership['rights'], get_name = 'Rights', set_name = 'setRights')

class DublinCore(Basic, Categorization, Publication, Ownership):
    pass
