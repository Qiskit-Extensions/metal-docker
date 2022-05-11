def dict_to_float(dictionary):
    new_dictionary = {}
    for key, value in dictionary.items():
        new_dictionary[key] = float(value)

    return new_dictionary