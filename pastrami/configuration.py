"""
Configuration directives for the package.
"""
from __future__ import absolute_import
from __future__ import print_function

import os

from collections import OrderedDict
import yamlordereddictloader

from jsonschema import Draft4Validator, validators
from jsonschema.exceptions import ValidationError, best_match

import yaml
yaml.add_representer(OrderedDict, yaml.representer.SafeRepresenter.represent_dict)


def extend_with_default(validator_class):
    """
    Wrapper around jsonschema validator_class to add support for default values.

    Returns:
        Extended validator_class
    """
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        """
        Function to set default values
        """
        for _property, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(_property, subschema["default"])

        for error in validate_properties(validator, properties, instance, schema):
            yield error

    return validators.extend(
        validator_class, {"properties" : set_defaults},
    )

DefaultValidatingDraft4Validator = extend_with_default(Draft4Validator)


def get_defaults(schema):
    """
    Gets default values from the schema

    Args:
        schema: jsonschema

    Returns:
        dict: dict with default values
    """
    result = ""
    try:
        _type = schema['type']
    except KeyError:
        return result
    except TypeError:
        raise SyntaxError('Error while parsing configuration file: "type" keyword missing at %s')

    if _type == 'object':
        result = dict(
            (k, get_defaults(v)) for k, v in schema['properties'].items()
        )
    elif _type == 'array':
        result = [get_defaults(schema['items'])]
    else:
        try:
            result = schema['default']
        except KeyError:
            result = result

    return result


def updatedict(original, updates):
    """
    Updates the original dictionary with items in updates.
    If key already exists it overwrites the values else it creates it

    Args:
        original: original dictionary
        updates: items to be inserted in the dictionary

    Returns:
        dict: updated dictionary
    """
    for key, value in updates.items():
        if key not in original or type(value) != type(original[key]):
            original[key] = value
        elif isinstance(value, dict):
            original[key] = updatedict(original[key], value)
        else:
            original[key] = value

    return original


def keys_to_lower(item):
    """
    Normalize dict keys to lowercase.

    Args:
        dict: dict to be normalized

    Returns:
        Normalized dict
    """
    result = False
    if isinstance(item, list):
        result = [keys_to_lower(v) for v in item]
    elif isinstance(item, dict):
        result = dict((k.lower(), keys_to_lower(v)) for k, v in item.items())
    else:
        result = item

    return result


def get_config(configuration_filename, schema_filename='configuration.yml', lower_keys=True):
    """
    Gets default config and overwrite it with the content of configuration_filename.
    If the file does not exist, it creates it.

    Default config is generated by applying get_defaults() to local file named configuration.yaml .
    Content of configuration_filename by assuming the content is formatted in YAML.

    Args:
        configuration_filename: name of the YAML configuration file
        schema_filename: name of the JSONSchema file
        lower_keys: transform keys to lowercase

    Returns:
        dict: configuration statements
    """

    base_dir = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(base_dir, schema_filename)) as stream:
        try:
            configschema = yaml.load(stream, Loader=yamlordereddictloader.Loader)
        except (yaml.scanner.ScannerError) as error:
            raise SyntaxError('Error while parsing configuration file: %s' % error)

    if os.path.exists(configuration_filename):
        with open(configuration_filename, 'r') as stream:
            defaults = get_defaults(configschema)
            config = yaml.load(stream)
            config = updatedict(defaults, config)
            if lower_keys:
                config = keys_to_lower(config)
    else:
        config = get_defaults(configschema)
        try:
            with open(configuration_filename, 'w') as stream:
                yaml.dump(config, stream, default_flow_style=False)
                print('Created configuration file: %s' % configuration_filename)
        except IOError:
            raise IOError('Unable to create configuration file: %s' % configuration_filename)

    error = best_match(DefaultValidatingDraft4Validator(configschema).iter_errors(config))
    if error:
        if error.path:
            path = '/'.join(error.relative_path)
            raise SyntaxError(
                'Error while parsing configuration file, not a valid value for: %s' % path
            )
        raise SyntaxError('Error while parsing configuration file: %s' % error.message)


    return config
