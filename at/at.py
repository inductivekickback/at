"""
Basic AT command parsing/encoding library compatible with Nordic's nRF91 series.

NOTE:   Commands are NOT expected to end in <CR><LF> (0xOD, 0xOA) or a NULL.
        Concatenated commands are separated by a ';' (and only first command has 'AT' prefix).
        Custom command prefixes (i.e. "AT#<CMD>") are not used.

See https://infocenter.nordicsemi.com/pdf/nrf91_at_commands_v0.7.pdf for more information.

Most AT commands are represented by a single Python dictionary with 'cmd', 'type', and 'params'
keys. The 'cmd' value is arbitrary but always starts with '+' or '%' with the nRF91. The 'type'
value can be 'SET', 'READ', or 'TEST'. The 'params' value is a list of Python values of type
None, int, str, or (single-nested) lists.

A few command strings use a primary command (e.g. %XSUDO to provide authenticatication) followed
by one or more "concatenated" commands that are sent as part of a single string. These commands are
separated by the ';' character.

Command string: 'AT+CEMODE=0'
Dictionary:     {'cmd':'+CEMODE', 'type':'SET', 'params':[0]}

Command string: 'AT%FOO=7,"c2lnbmF0dXJl";+BAR=(1,2,3)'
Dictionary:     [{'cmd':'%FOO',
                  'type':'SET',
                  'params':[7, "c2lnbmF0dXJl"]},
                 {'cmd':'+BAR',
                  'type':'SET',
                  'params':[[1, 2, 3]]}]

Responses strings are similar to commands and use the same 'params' key and format. However,
responses have a 'response' key instead of a 'cmd' key, the 'type' key is set to 'RESPONSE',
and an 'error' key is set to True or False.

Response string: 'OK'
Dictionary:      {'response':'OK', 'type':'RESPONSE', 'error':False, 'params':[]})

Response string: '+CMS ERROR: 128'
Dictionary:      {'response':'+CMS ERROR',
                  'type':'RESPONSE',
                  'error':True,
                  'params':[128]}

The 'test/tests.py' script contains several example strings and their dictionary equivalents.
"""
AT_CMD_KEY = 'cmd'
AT_TYPE_KEY = 'type'
AT_PARAMS_KEY = 'params'
AT_RESPONSE_KEY = 'response'
AT_ERROR_KEY = 'error'

AT_TYPE_VALUE_SET = 'SET'
AT_TYPE_VALUE_READ = 'READ'
AT_TYPE_VALUE_TEST = 'TEST'
AT_TYPE_VALUE_RESPONSE = 'RESPONSE'

AT_PARAM_SEP = ','
AT_RSP_SEP = ':'
AT_PARAM_CONCAT_SEP = ';'

AT_CMD_PREFIX = 'AT'
AT_CMD_SET_IDENT = '='
AT_CMD_READ_IDENT = '?'
AT_CMD_TEST_IDENT = '=?'
AT_CMD_STRING_IDENT = '"'
AT_CMD_ARRAY_START = '('
AT_CMD_ARRAY_END = ')'

AT_RSP_OK = 'OK'
AT_RSP_ERROR = 'ERROR'

AT_STD_PREFX = '+'
AT_PROP_PREFX = '%'

RESPONSE_STR_DANGLING_QUOTE = '"\r\n'


class ATError(Exception):
    """AT exception class, inherits from the built-in Exception class."""

    def __init__(self, error_str=None):
        """Constructs a new object and sets the error."""
        if error_str:
            self.err_str = 'AT error: {}'.format(error_str)
        else:
            self.err_str = 'AT error'
        Exception.__init__(self, self.err_str)


def _parse_param(param_str):
    """Convert the param_str into its corresponding Python type."""
    if not param_str:
        return None
    elif param_str[0] == AT_CMD_STRING_IDENT:
        return param_str.strip(AT_CMD_STRING_IDENT)
    else:
        # It might be a string but not enclosed in quotes
        try:
            res = int(param_str)
        except ValueError:
            res = param_str
        return res

def _encode_param(param):
    """Convert the param to its corresponding AT string representation."""
    if param is None:
        return ' '
    elif isinstance(param, str):
        return "".join((AT_CMD_STRING_IDENT, param, AT_CMD_STRING_IDENT))
    else:
        return str(param)


def _parse_params(params_str):
    """Parse an entire string of params, including single-nested arrays."""
    result = []
    array = None
    end_of_array = False
    params = params_str.split(AT_PARAM_SEP)
    for param in params:
        param_str = param.strip()
        if param_str.startswith(AT_CMD_ARRAY_START):
            if array is not None:
                raise ATError("Nested array encountered")
            else:
                array = []
                param_str = param_str[1:]
        if param_str.endswith(AT_CMD_ARRAY_END):
            end_of_array = True
            param_str = param_str[:-1]
        if array is not None:
            array.append(_parse_param(param_str))
        else:
            result.append(_parse_param(param_str))
        if end_of_array:
            result.append(array)
            array = None
            end_of_array = False
    return result


def _encode_params(params_seq):
    """Return a string representation of the params sequence."""
    result_strs = []
    for param in params_seq:
        if not isinstance(param, (list, tuple)):
            result_strs.append(_encode_param(param))
        else:
            seq_str = _encode_params(param)
            result_strs.append(AT_CMD_ARRAY_START + seq_str + AT_CMD_ARRAY_END)
    return AT_PARAM_SEP.join(result_strs)


def parse_string(cmd_str):
    """Return a list of dicts specifying the command."""
    if not cmd_str:
        raise ATError('No str to parse.')
    temp_cmd_str = cmd_str.strip().upper()
    if temp_cmd_str.startswith(AT_RSP_OK):
        if len(temp_cmd_str) != len(AT_RSP_OK):
            raise ATError('Unexpected trailing data after OK')
        return {AT_RESPONSE_KEY:AT_RSP_OK,
                AT_TYPE_KEY:AT_TYPE_VALUE_RESPONSE,
                AT_ERROR_KEY:False,
                AT_PARAMS_KEY:[]}
    elif temp_cmd_str.startswith(AT_RSP_ERROR):
        if len(temp_cmd_str) != len(AT_RSP_ERROR):
            raise ATError('Unexpected trailing data after ERROR')
        return {AT_RESPONSE_KEY:AT_RSP_ERROR,
                AT_TYPE_KEY:AT_TYPE_VALUE_RESPONSE,
                AT_ERROR_KEY:True,
                AT_PARAMS_KEY:[]}
    elif temp_cmd_str.startswith(AT_STD_PREFX) or temp_cmd_str.startswith(AT_PROP_PREFX):
        # Response starting with '+<CMD>: <params>' or '%<CMD>: <params>'
        response, params = cmd_str.split(AT_RSP_SEP)
        params = _parse_params(params)
        if AT_RSP_ERROR in response:
            return {AT_RESPONSE_KEY:response,
                    AT_TYPE_KEY:AT_TYPE_VALUE_RESPONSE,
                    AT_ERROR_KEY:True,
                    AT_PARAMS_KEY:params}
        else:
            return {AT_RESPONSE_KEY:response,
                    AT_TYPE_KEY:AT_TYPE_VALUE_RESPONSE,
                    AT_ERROR_KEY:False,
                    AT_PARAMS_KEY:params}
    elif cmd_str.endswith(AT_CMD_TEST_IDENT):
        return {AT_CMD_KEY:cmd_str.upper().lstrip(AT_CMD_PREFIX).rstrip(AT_CMD_TEST_IDENT),
                AT_TYPE_KEY:AT_TYPE_VALUE_TEST, AT_PARAMS_KEY:[]}
    elif cmd_str.endswith(AT_CMD_READ_IDENT):
        return {AT_CMD_KEY:cmd_str.upper().lstrip(AT_CMD_PREFIX).rstrip(AT_CMD_TEST_IDENT),
                AT_TYPE_KEY:AT_TYPE_VALUE_READ, AT_PARAMS_KEY:[]}
    elif temp_cmd_str.startswith(AT_CMD_PREFIX):
        # Could be a regular or compound command.
        result = []
        stmts = cmd_str.split(AT_PARAM_CONCAT_SEP)
        for stmt in stmts:
            if AT_CMD_SET_IDENT in stmt:
                cmd, params = stmt.split(AT_CMD_SET_IDENT)
                result.append({AT_CMD_KEY:cmd.lstrip(AT_CMD_PREFIX),
                               AT_TYPE_KEY:AT_TYPE_VALUE_SET, AT_PARAMS_KEY:_parse_params(params)})
            else:
                # Some SET requests actually return data, e.g. AT%XMODEMUUID
                result.append({AT_CMD_KEY:stmt.lstrip(AT_CMD_PREFIX),
                               AT_TYPE_KEY:AT_TYPE_VALUE_SET, AT_PARAMS_KEY:[]})
        if len(result) == 1:
            return result[0]
        else:
            return result
    else:
        if cmd_str.strip() == AT_CMD_STRING_IDENT:
            # Cert responses end with a line containing a single ".
            cmd_str = ''
        elif cmd_str.endswith(RESPONSE_STR_DANGLING_QUOTE):
            # It's also possible for multi-line response strings to end with an orphan ".
            cmd_str = cmd_str.strip(RESPONSE_STR_DANGLING_QUOTE)
        return{AT_RESPONSE_KEY:None,
               AT_TYPE_KEY:AT_TYPE_VALUE_RESPONSE,
               AT_ERROR_KEY:False,
               AT_PARAMS_KEY:[cmd_str]}


def encode_command(cmd_dicts, result_strs=None):
    """Take a list of dicts that describe an AT command string and encode it as string."""
    if not result_strs:
        result_strs = [AT_CMD_PREFIX]
    if not isinstance(cmd_dicts, (tuple, list)):
        cmd_dicts = (cmd_dicts,)

    result_strs.append(cmd_dicts[0][AT_CMD_KEY])
    cmd_type = cmd_dicts[0][AT_TYPE_KEY]
    if cmd_type == AT_TYPE_VALUE_SET:
        if cmd_dicts[0].get(AT_PARAMS_KEY):
            result_strs.append(AT_CMD_SET_IDENT)
            result_strs.append(_encode_params(cmd_dicts[0][AT_PARAMS_KEY]))
    elif cmd_type == AT_TYPE_VALUE_READ:
        result_strs.append(AT_CMD_READ_IDENT)
    elif cmd_type == AT_TYPE_VALUE_TEST:
        result_strs.append(AT_CMD_TEST_IDENT)
    else:
        raise ATError('Unknown command type: {}'.format(cmd_type))
    if len(cmd_dicts) == 1:
        return "".join(result_strs)
    else:
        result_strs.append(AT_PARAM_CONCAT_SEP)
        return "".join(encode_command(cmd_dicts[1:], result_strs))
