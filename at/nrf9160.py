"""
The purpose of this module is to handle sending commands and receiving responses from
a serial port in a separate thread.

NOTE: The at_client firmware needs a few seconds to start up before the AT interface is useful.
"""
import at


CFUN_MODE_POWER_OFF = 0
CFUN_MODE_NORMAL = 1
CFUN_MODE_OFFLINE = 4 # AKA Flight mode
CFUN_MODE_OFFLINE_WO_SHUTTING_DOWN_UICC = 44

CGSN_TYPE_SN = 0
CGSN_TYPE_IMEI = 1
CGSN_TYPE_IMEISV = 2
CGSN_TYPE_SVN = 3

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

    def query_modem(self, command):
        """Request modem the specified command"""
        cmd = {at.AT_CMD_KEY:command, at.AT_TYPE_KEY:at.AT_TYPE_VALUE_SET}
        result, response = self._chat.send_cmd(cmd)
        if len(response) != 1:
            raise SoCError('Unexpected response to {}.'.format(command))
        if result[at.AT_ERROR_KEY]:
            raise SoCError('{} failed: {}.'.format(command, result[at.AT_RESPONSE_KEY]))
        return response[0][at.AT_PARAMS_KEY][0]

    def get_manufacturer_id(self):
        """Use the +CGMI command to read the manufacturer identification as a string."""
        command = '+CGMI'
        cmd = {at.AT_CMD_KEY:command, at.AT_TYPE_KEY:at.AT_TYPE_VALUE_SET}
        result, response = self._chat.send_cmd(cmd)
        if len(response) != 1:
            raise SoCError('Unexpected response to {}.'.format(command))
        if result[at.AT_ERROR_KEY]:
            raise SoCError('{} failed: {}.'.format(command, result[at.AT_RESPONSE_KEY]))
        return response[0][at.AT_PARAMS_KEY][0].rstrip()

    def _cgsn(self, param):
        """Use the +CGSN command to read several types of serial numbers."""
        command = '+CGSN'
        cmd = {at.AT_CMD_KEY:command,
               at.AT_TYPE_KEY:at.AT_TYPE_VALUE_SET,
               at.AT_PARAMS_KEY:[param]}
        result, response = self._chat.send_cmd(cmd)
        if len(response) != 1:
            raise SoCError('Unexpected response to {}.'.format(command))
        if result[at.AT_ERROR_KEY]:
            raise SoCError('{} failed: {}.'.format(command, result[at.AT_RESPONSE_KEY]))
        return response[0][at.AT_PARAMS_KEY][0].rstrip()

    def get_serial_number(self):
        """Use the +CGSN command to read the serial number."""
        return self._cgsn(CGSN_TYPE_SN)

    def get_imei(self):
        """Use the +CGSN command to read the IMEI."""
        return self._cgsn(CGSN_TYPE_IMEI)

    def get_imeisv(self):
        """Use the +CGSN command to read the IMEISV."""
        return self._cgsn(CGSN_TYPE_IMEISV)

    def get_svn(self):
        """Use the +CGSN command to read the SVN."""
        return self._cgsn(CGSN_TYPE_SVN)

    def get_functional_mode(self):
        """Use the +CFUN command to get the functional mode and returns it as an int."""
        command = '+CFUN'
        cmd = {at.AT_CMD_KEY:command, at.AT_TYPE_KEY:at.AT_TYPE_VALUE_READ}
        result, response = self._chat.send_cmd(cmd)
        if len(response) != 1:
            raise SoCError('Unexpected response to {}.'.format(command))
        if result[at.AT_ERROR_KEY]:
            raise SoCError('{} list failed: {}.'.format(command, result[at.AT_RESPONSE_KEY]))
        return response[0][at.AT_PARAMS_KEY][0]

    def set_functional_mode(self, mode):
        """
        Use the +CFUN command to set the functional mode.

        NOTE:   An ERROR response will be returned when changing to NORMAL mode
                if the SIM card has failed.

        NOTE:   A power cycle is required after changing to POWER_OFF mode (and no
                further commands should be sent before that happens).
        """
        command = '+CFUN'
        cmd = {at.AT_CMD_KEY:command,
               at.AT_TYPE_KEY:at.AT_TYPE_VALUE_SET,
               at.AT_PARAMS_KEY:[mode]}
        result, _ = self._chat.send_cmd(cmd)
        if result[at.AT_ERROR_KEY]:
            raise SoCError('{} list failed: {}.'.format(command, result[at.AT_RESPONSE_KEY]))

    def list_credentials(self, sec_tag=None, cred_type=None):
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

    def read_credential(self, sec_tag, cred_type):
        """Use %CMNG to read a credential. The sec_tag and cred_type parameters must
        be specified. Returns [] if there were no matching credentials.
        """
        command = '%CMNG'
        if cred_type == CRED_TYPE_PUBLIC_KEY:
            raise SoCError('Public keys can only be deleted.')
        if (cred_type == CRED_TYPE_CLIENT_CERT or
                cred_type == CRED_TYPE_CLIENT_PRIVATE_KEY or
                cred_type == CRED_TYPE_PSK):
            raise SoCError('Reading of cred_types 1, 2, and 3 is not supported.')
        cmd = {at.AT_CMD_KEY:command,
               at.AT_TYPE_KEY:at.AT_TYPE_VALUE_SET,
               at.AT_PARAMS_KEY:[OPCODE_READ, sec_tag, cred_type]}
        result, response = self._chat.send_cmd(cmd)
        if result[at.AT_ERROR_KEY]:
            raise SoCError('{} list failed: {}.'.format(command, result[at.AT_RESPONSE_KEY]))
        credential = []
        cmd_echo = response.pop(0)
        if cmd_echo[at.AT_RESPONSE_KEY] != command:
            raise SoCError('Failed to parse output of {} read.'.format(command))
        verify_sec_tag, verify_cred_type, _, content = cmd_echo[at.AT_PARAMS_KEY]
        if verify_sec_tag != sec_tag or verify_cred_type != cred_type:
            raise SoCError('Failed to verify credential in output of {} read.'.format(command))
        credential.append(content)
        credential.append('\n')
        for line in response:
            if line[at.AT_RESPONSE_KEY] is None:
                credential.append(line[at.AT_PARAMS_KEY][0])
        return "".join(credential).strip()

    def write_credential(self, sec_tag, cred_type, content, passwd=None):
        """Use %CMNG to write a credential. The sec_tag, cred_type, and content parameters must
        be specified.

        NOTE: Certificate length seems to be limited to 4077 bytes.
        """
        command = '%CMNG'
        if cred_type == CRED_TYPE_PUBLIC_KEY:
            raise SoCError('Public keys can only be deleted.')
        if not passwd is None and cred_type != CRED_TYPE_CLIENT_PRIVATE_KEY:
            raise SoCError('passwd is not used unless writing encrypted private key.')
        if self.get_functional_mode() == CFUN_MODE_NORMAL:
            raise SoCError('Writing credentials is not possible while modem is active.')
        cmd = {at.AT_CMD_KEY:command,
               at.AT_TYPE_KEY:at.AT_TYPE_VALUE_SET,
               at.AT_PARAMS_KEY:[OPCODE_WRITE, sec_tag, cred_type, content, passwd]}
        result, _ = self._chat.send_cmd(cmd)
        if result[at.AT_ERROR_KEY]:
            raise SoCError('{} write failed: {}.'.format(command, result[at.AT_RESPONSE_KEY]))

    def delete_credential(self, sec_tag, cred_type):
        """Use %CMNG to delete a credential. The sec_tag and cred_type parameters must
        be specified.
        """
        command = '%CMNG'
        if self.get_functional_mode() == CFUN_MODE_NORMAL:
            raise SoCError('Deleting credentials is not possible while modem is active.')
        cmd = {at.AT_CMD_KEY:command,
               at.AT_TYPE_KEY:at.AT_TYPE_VALUE_SET,
               at.AT_PARAMS_KEY:[OPCODE_DELETE, sec_tag, cred_type]}
        result, _ = self._chat.send_cmd(cmd)
        if result[at.AT_ERROR_KEY]:
            raise SoCError('{} delete failed: {}.'.format(command, result[at.AT_RESPONSE_KEY]))
