def uci_commit(config):
    pass


def uci_get(config, section=None, type=None, option=None):
    """
    - When called without argument or with empty object: return an array of
      config names in the configs field
    - When called with config set: return an object containing all sections
      containing all options in a field named after the config
    - When called with config and type set: return an object containing all
      sections of type type containing all options in a field named after the
      config
    - When called with config and sname set: return an object containing all
      options of the section in a field named after the section
    - When called with config and type and oname set: return an object
      containing the value of each option named oname within a section of type
      type in a field named after the matched section
    - When called with config and sname and oname set: return the result
      string in a field named oname in case of options or an array of result
      strings in a field named oname in case of list options

    Args:
        config (str):
        section (str):
        type (str):
        option (str):

    Returns:
        dict: Requested data
    """


def uci_set(config, section, option=None, value=None):
    """Set a UCI option

    When called with config and section and value set:
      - Add a new section with given name in config and set it to the type
        given in value

    When called with config, section, option and value:
      - If value is of type array:
            -set strings in the value array as list option
      - If value is of type string:
            - set value as normal option oname

    Args:
        config (str):
        section (str):
        option (str):
        value (str):

    Returns:
        bool: Operation successfull
    """
