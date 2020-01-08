"""
The purpose of this module is to handle sending commands and receiving responses from
a serial port in a separate thread.
"""
import at


CFUN_MODE_POWER_OFF = 0
CFUN_MODE_NORMAL = 1
CFUN_MODE_OFFLINE = 4 # AKA Flight mode
CFUN_MODE_OFFLINE_WO_SHUTTING_DOWN_UICC = 44

OPCODE_WRITE = 0
OPCODE_LIST = 1
OPCODE_READ = 2
OPCODE_DELETE = 3

CRED_TYPE_ROOT_CA = 0
CRED_TYPE_CLIENT_CERT = 1
CRED_TYPE_CLIENT_PRIVATE_KEY = 2
CRED_TYPE_PSK = 3 # ASCII string in hex format
CRED_TYPE_PSK_IDENTITY = 4
CRED_TYPE_PUBLIC_KEY = 5

CME_ERROR_NOT_FOUND = 513
CME_ERROR_NO_ACCESS = 514
CME_ERROR_MEMORY_FULL = 515
CME_ERROR_NOT_ALLOWED_IN_ACTIVE_STATE = 518


class SoCError(Exception):
    """ChatThrad exception class, inherits from the built-in Exception class."""

    def __init__(self, error_str=None):
        """Constructs a new object and sets the error."""
        if error_str:
            self.err_str = 'SoC error: {}'.format(error_str)
        else:
            self.err_str = 'SoC error'
        Exception.__init__(self, self.err_str)


class SoC():
    """Library for interacting with an nRF9160 via its AT command interface."""

    def __init__(self, port):
        """Create a new object and assign it the specfied serial port."""
        self._chat = at.Chat(port)

    def close(self):
        """Close the serial port."""
        if not self._chat.is_closed():
            self._chat.close()

    def functional_mode_get(self):
        """Uses the +CFUN command to get the functional mode and returns it as an int."""
        cmd = {at.AT_CMD_KEY:'+CFUN', at.AT_TYPE_KEY:at.AT_TYPE_VALUE_READ}
        result, response = self._chat.send_cmd(cmd)
        if len(response) != 1:
            raise SoCError('Unexpected response to +CFUN.')
        if result[at.AT_ERROR_KEY]:
            raise SoCError('Failed to read +CFUN.')
        return response[0][at.AT_PARAMS_KEY][0]

    def functional_mode_set(self, mode):
        """
        Uses the +CFUN command to set the functional mode and returns 'OK' or an error string.

        NOTE:   An ERROR response will be returned when changing to NORMAL mode
                if the SIM card has failed.

        NOTE:   A power cycle is required after changing to POWER_OFF mode (and no
                further commands should be sent before that happens).
        """
        cmd = {at.AT_CMD_KEY:'+CFUN',
               at.AT_TYPE_KEY:at.AT_TYPE_VALUE_SET,
               at.AT_PARAMS_KEY:[mode]}
        result, _ = self._chat.send_cmd(cmd)
        return result[at.AT_RESPONSE_KEY]

    def credentials_list(self, sec_tag=None, cred_type=None):
        """Use %CMNG to return a list of credentials. Each credential is in the form [sec_tag,
        cred_type, content]. Either of the sec_tag and cred_type parameters can be None.
        Returns [] if there were no matching credentials.
        """
        command = '%CMNG'
        if cred_type == CRED_TYPE_PUBLIC_KEY:
            raise SoCError('Public keys can only be deleted.')
        cmd = {at.AT_CMD_KEY:command,
               at.AT_TYPE_KEY:at.AT_TYPE_VALUE_SET,
               at.AT_PARAMS_KEY:[OPCODE_LIST, sec_tag, cred_type, None, None]}
        result, response = self._chat.send_cmd(cmd)
        if result[at.AT_ERROR_KEY]:
            raise SoCError('{} list failed: {}.'.format(command, result[at.AT_RESPONSE_KEY]))
        return [x[at.AT_PARAMS_KEY] for x in response if x[at.AT_RESPONSE_KEY] == command]
