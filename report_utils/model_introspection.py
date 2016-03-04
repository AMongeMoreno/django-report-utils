""" Functioned to introspect a model """
from django.contrib.contenttypes.models import ContentType
from django.db.models.fields import FieldDoesNotExist
from django.conf import settings
import inspect

def isprop(v):
    return isinstance(v, property)

def is_direct(field):
    return not field.auto_created or field.concrete

def is_m2m(field):
    return getattr(field, 'many_to_many', False)

def get_properties_from_model(model_class):
    """ Show properties from a model """
    properties = []
    attr_names = [name for (name, value) in inspect.getmembers(model_class, isprop)]
    for attr_name in attr_names:
        if attr_name.endswith('pk'):
            attr_names.remove(attr_name)
        else:
            properties.append(dict(label=attr_name, name=attr_name.strip('_').replace('_',' ')))
    return sorted(properties, key=lambda k: k['label'])


def get_relation_fields_from_model(model_class):
    """ Get related fields (m2m, FK, and reverse FK) """
    relation_fields = []
    all_fields = model_class._meta.get_fields()
    for field in all_fields:
        field_name = field.name
        if is_m2m(field) or not is_direct(field) or hasattr(field, 'related'):
            field.field_name = field_name
            relation_fields += [field]
    return relation_fields


def get_direct_fields_from_model(model_class):
    """ Direct, not m2m, not FK """
    direct_fields = []
    all_fields = model_class._meta.get_fields()
    for field in all_fields:
        if is_direct(field) and not is_m2m(field) and not hasattr(field, 'related'):
            direct_fields += [field]
    return direct_fields


def get_custom_fields_from_model(model_class):
    """ django-custom-fields support """
    if 'custom_field' in settings.INSTALLED_APPS:
        from custom_field.models import CustomField
        try:
            content_type = ContentType.objects.get(
                model=model_class._meta.model_name,
                app_label=model_class._meta.app_label)
        except ContentType.DoesNotExist:
            content_type = None
        custom_fields = CustomField.objects.filter(content_type=content_type)
        return custom_fields


def get_model_from_path_string(root_model, path):
    """ Return a model class for a related model
    root_model is the class of the initial model
    path is like foo__bar where bar is related to foo
    """
    for path_section in path.split('__'):
        if path_section:
            try:
                field = root_model._meta.get_field(path_section)
            except FieldDoesNotExist:
                return root_model
            if is_direct(field):
                if hasattr(field, 'related'):
                    try:
                        root_model = field.related.parent_model()
                    except AttributeError:
                        root_model = field.related_model
            else:
                if hasattr(field, 'related_model'):
                    root_model = field.related_model
                else:
                    root_model = field.model
    return root_model
