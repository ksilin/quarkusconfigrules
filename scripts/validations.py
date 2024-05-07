# Contains generic validation functions

import re

def validate_property_not_set(properties, key_suffix):
    """
    Validate that no property with a specified key suffix is set in the properties dictionary.

    Parameters:
        properties (dict): The dictionary containing property keys and values.
        key_suffix (str): The suffix to check against property keys.

    Returns:
        tuple: (bool, str) where bool indicates if the validation passed (no key with suffix is set),
               and str provides an error message if a key with the suffix is set.
    """
    for key in properties.keys():
        if str(key).endswith(key_suffix):
            return False, f"Expected {key} to not be set. It is set to {properties[key]}."
    return True, None

def validate_value_expected(properties, key_suffix, expected_values, treat_key_not_found_as_success=False, ignore_profiles=None):
    """
    Validate that a property with a certain key suffix has a value from the expected values list.

    Parameters:
        properties (dict): The dictionary containing property keys and values.
        key_suffix (str): The suffix for identifying the property.
        expected_values (list or str): A list of values or a single value that the property is expected to have.
        treat_key_not_found_as_success (bool, optional): Whether to treat not finding the key as a validation success.
        ignore_profiles (list, optional): A list of profile prefixes to ignore in the keys.

    Returns:
        tuple: (bool, str) where bool indicates if the properties are valid,
               and str provides the result or error message.
    """
    if not isinstance(expected_values, list):
        expected_values = [expected_values]

    key, value = get_key_value_by_suffix(properties, key_suffix, ignore_profiles)

    if key:
        if value in expected_values:
            return True, f"{key} set to '{value}', which is included in the expected values: {expected_values}"
        else:
            return False, f"{key} found but set to '{value}', expected one of {expected_values}"
    else:
        if treat_key_not_found_as_success:
            return True, f"No key ending with '{key_suffix}' found"
        else:
            return False, f"No key ending with '{key_suffix}' found"

def validate_value_regex(properties, key_suffix, regex_pattern, treat_key_not_found_as_success=False, ignore_profiles=None):
    """
    Validate that the value of a property matching a certain key suffix meets a specified regex pattern.

    Parameters:
        properties (dict): The dictionary containing property keys and values.
        key_suffix (str): The suffix for identifying the property.
        regex_pattern (str): The regex pattern that the property's value should match.
        treat_key_not_found_as_success (bool, optional): Whether to treat not finding the key as a validation success.
        ignore_profiles (list, optional): A list of profile prefixes to ignore in the keys.

    Returns:
        tuple: (bool, str) where bool indicates if the properties are valid and str provides the message.
    """
    if ignore_profiles is None:
        ignore_profiles = []

    key, value = get_key_value_by_suffix(properties, key_suffix, ignore_profiles)

    if key:
        if re.match(regex_pattern, value):
            return True, f"Value '{value}' for key '{key}' matches the required pattern: {regex_pattern}"
        else:
            return False, f"Value '{value}' for key '{key}' does not match the required pattern: {regex_pattern}"
    else:
        if treat_key_not_found_as_success:
            return True, None
        else:
            return False, f"No key ending with '{key_suffix}' found"

def is_numeric(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def validate_value_numeric_range(properties, key_suffix, min_val=0, max_val=None, treat_key_not_found_as_success=False, ignore_profiles=None):
    """
    Validate that the numeric value of a property with a specified key suffix is within a defined range.

    Parameters:
        properties (dict): The dictionary containing property keys and values.
        key_suffix (str): The suffix for identifying the property.
        min_val (float): The minimum allowable value for the property.
        max_val (float, optional): The maximum allowable value for the property; defaults to infinity if not specified.
        treat_key_not_found_as_success (bool, optional): Whether to consider not finding the key as a validation success.
        ignore_profiles (list, optional): A list of profile prefixes to ignore in the keys.

    Returns:
        tuple: (bool, str) where bool indicates if the property value is within the range,
               and str provides a message if it is not within the range or the key is not found.
    """
    if max_val is None:
        max_val = float('inf')

    key, value = get_key_value_by_suffix(properties, key_suffix, ignore_profiles)

    if key is None:
        if treat_key_not_found_as_success:
            return True, f"No key ending with '{key_suffix}' found"
        else:
            return False, f"No key ending with '{key_suffix}' found"

    if not is_numeric(value):
        return False, f"Value '{value}' for key '{key}' is not numeric"

    value = float(value)
    in_range = min_val <= value <= max_val
    if in_range:
        return True, f"Value '{value}' for key `{key}` is within the expected range [{min_val},{max_val}]"
    else:
        return False, f"Value '{value}' for key `{key}` is outside of the expected range [{min_val},{max_val}]"

def get_key_value_by_suffix(properties, key_suffix, ignore_profiles=None):
    """
    Fetch a key-value pair from the properties dictionary where the key ends with a given suffix,
    optionally ignoring keys that start with specific profile identifiers.

    Parameters:
        properties (dict): The dictionary from which to fetch the key-value pair.
        key_suffix (str): The suffix to match at the end of the keys.
        ignore_profiles (list, optional): A list of prefixes to ignore in the keys.

    Returns:
        tuple: (key, value) if a matching key is found, otherwise (None, None)
    """
    if ignore_profiles is None:
        ignore_profiles = []

    filtered_keys = {
        k: v for k, v in properties.items()
        if not any(k.startswith(f"%{profile}") for profile in ignore_profiles)
        and k.endswith(key_suffix)
    }

    key = next(iter(filtered_keys), None)
    return (key, filtered_keys.get(key)) if key else (None, None)

def validate_numeric_property_relation(properties, key_suffix_1, key_suffix_2, min_multiple, max_multiple, ignore_profiles=None):
    """
    Validate that if property 1 is set, then property 2 is within the range [value_1 * min_multiple, value_1 * max_multiple].

    Parameters:
        properties (dict): The dictionary containing property keys and values.
        key_suffix_1 (str): The suffix for identifying property 1.
        key_suffix_2 (str): The suffix for identifying property 2.
        min_multiple (int): The minimum multiple of value_1 to determine the lower bound of 2's range.
        max_multiple (int): The maximum multiple of value_1 to determine the upper bound of 2's range.
        ignore_profiles (list, optional): A list of profile prefixes to ignore in the keys.

    Returns:
        tuple: (bool, str) where bool indicates if the properties are valid and str provides the success or error message.
    """
    key_1, value_1 = get_key_value_by_suffix(properties, key_suffix_1, ignore_profiles)
    key_2, value_2 = get_key_value_by_suffix(properties, key_suffix_2, ignore_profiles)

    if value_1 is None:
        return True, f"Property '{key_suffix_1}' is not configured; default is considered valid."

    try:
        numeric_1 = float(value_1)
        numeric_2 = float(value_2)
    except ValueError:
        return False, f"One of the properties '{key_1}'='{value_1}' or '{key_2}'='{value_2}' is not a valid number."

    min_val = numeric_1 * min_multiple
    max_val = numeric_1 * max_multiple

    if min_val <= numeric_2 <= max_val:
        return True, f"Property '{key_2}' is correctly set within the range [{min_val}, {max_val}] based on '{key_1}' value of {numeric_1}."
    else:
        return False, f"Property '{key_2}'='{numeric_2}' is not within the expected range [{min_val}, {max_val}] based on '{key_1}' value of {numeric_1}."

def validate_exclusive_property_setting(properties, key_suffix_1, key_suffix_2, ignore_profiles=None):
    """
    Validate that exactly one of two properties is set, but not both.

    Parameters:
        properties (dict): The dictionary containing property keys and values.
        key_suffix_1 (str): The suffix for identifying the first property.
        key_suffix_2 (str): The suffix for identifying the second property.
        ignore_profiles (list, optional): A list of profile prefixes to ignore in the keys.

    Returns:
        tuple: (bool, str) where bool indicates if the properties are valid and str provides the success or error message.
    """
    if ignore_profiles is None:
        ignore_profiles = []

    key_1, _ = get_key_value_by_suffix(properties, key_suffix_1, ignore_profiles)
    key_2, _ = get_key_value_by_suffix(properties, key_suffix_2, ignore_profiles)

    if (key_1 is not None) ^ (key_2 is not None):
        return True, f"Exactly one property is set as expected: '{key_1 if key_1 else key_2}' is set."
    elif key_1 is not None and key_2 is not None:
        return False, f"Both '{key_1}' and '{key_2}' are set, but only one should be set."
    else:
        return False, f"Neither of '{key_suffix_1}' and '{key_suffix_2}' is set. One of the properties must be set."

def validate_conditional_numeric_range(properties, key_suffix_1, expected_value_1, key_suffix_2, min_val, max_val, ignore_profiles=None):
    """
    Validate that if one property is set to a specific value, then second property must be within a defined numeric range.

    Parameters:
        properties (dict): Dictionary containing property keys and values.
        key_suffix_1 (str): Key suffix for the first property.
        expected_value_1 (str): The specific value of property first property that triggers validation for second property.
        key_suffix_2 (str): Key suffix for second property - the one being evaluated against the range.
        min_val (float): Minimum valid value for second property.
        max_val (float): Maximum valid value for second property.
        ignore_profiles (list, optional): Profiles to ignore in key searching.

    Returns:
        tuple: (bool, str) where bool indicates if the properties are valid and str provides the success or error message.
    """
    key_1, value_1 = get_key_value_by_suffix(properties, key_suffix_1, ignore_profiles)
    if value_1 != expected_value_1:
        return True, f"Property '{key_1}' is not set to '{expected_value_1}'; no validation for '{key_suffix_2}' is required."

    key_2, value_2 = get_key_value_by_suffix(properties, key_suffix_2, ignore_profiles)
    if key_2 is None:
        return False, f"Property with suffix '{key_suffix_2}' must be set when '{key_1}' is '{value_1}'."

    if not is_numeric(value_2):
        return False, f"Property '{key_2}'='{value_2}' is not numeric and cannot be validated."

    b_numeric = float(value_2)
    if min_val <= b_numeric <= max_val:
        return True, f"Property '{key_2}'='{value_2}' is correctly set within the range [{min_val}, {max_val}]."
    else:
        return False, f"Property '{key_2}'='{value_2}' is not within the expected range [{min_val}, {max_val}], which applies when '{key_1}' is '{value_1}'."