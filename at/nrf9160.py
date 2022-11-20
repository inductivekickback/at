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
CRED_TYPE_ENDORSEMENT_PRIVATE_KEY = 8

CRED_RESPONSE_CONTENT_CSR = 0 # Mandatory when generating CRED_TYPE_CLIENT_PRIVATE_KEY
CRED_RESPONSE_CONTENT_PUBLIC_KEY = 1

CME_ERROR_NOT_FOUND = 513
CME_ERROR_NO_ACCESS = 514
CME_ERROR_MEMORY_FULL = 515
CME_ERROR_NOT_ALLOWED_IN_ACTIVE_STATE = 518
CME_ERROR_ALREADY_EXISTS = 519
CME_ERROR_KEY_GEN_FAILED = 523
CME_ERROR_NOT_ALLOWED = 528 # Not allowed in Power off warning state

JWT_ALG_ES256 = 0

CSR_ATTRIBUTES = [ "commonName", # (CN)
    "locality", # (L)
    "stateOrProvinceName", # (ST)
    "organizationName", # (O)
    "organizationalUnitName", # (OU)
    "countryName", # (C)
    "domainComponent", # (DC)
    "surName", # (SN)
    "givenName", # (GN)
    "emailAddress", # (R)
    "serialNumber",
    "postalAddress",
    "postalCode",
    "dnQualifier",
    "title",
    "initials",
    "pseudonym",
    "generationQualifier" ]

CSR_KEY_USAGE_BIT_DIG_SIG = (1<<0) # digitalSignature (the first digit)
CSR_KEY_USAGE_BIT_NON_REPUD = (1<<1) # nonRepudiation
CSR_KEY_USAGE_BIT_KEY_ENCIPH = (1<<2) # keyEncipherment
CSR_KEY_USAGE_BIT_DATA_ENCIPH = (1<<3) # dataEncipherment
CSR_KEY_USAGE_BIT_KEY_AGREE = (1<<4) # keyAgreement
CSR_KEY_USAGE_BIT_KEY_CERT_SIGN = (1<<5) # keyCertSign
CSR_KEY_USAGE_BIT_CRL_SIGN = (1<<6) # cRLSign
CSR_KEY_USAGE_BIT_ENCIPH_ONLY = (1<<7) # encipherOnly
CSR_KEY_USAGE_BIT_DECIPH_ONLY = (1<<8) # decipherOnly (the last digit)


class SoCError(Exception):
    """ChatThrad exception class, inherits from the built-in Exception class."""

    def __init__(self, error_str=None):
        """Constructs a new object and sets the error."""
        if error_str:
            self.err_str = f'SoC error: {error_str}.'
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
            raise SoCError(f'Unexpected response to {command}.')
        if result[at.AT_ERROR_KEY]:
            raise SoCError(f'{command} failed: {result[at.AT_RESPONSE_KEY]}.')
        return response[0][at.AT_PARAMS_KEY][0]

    def get_manufacturer_id(self):
        """Use the +CGMI command to read the manufacturer identification as a string."""
        command = '+CGMI'
        cmd = {at.AT_CMD_KEY:command, at.AT_TYPE_KEY:at.AT_TYPE_VALUE_SET}
        result, response = self._chat.send_cmd(cmd)
        if len(response) != 1:
            raise SoCError(f'Unexpected response to {command}.')
        if result[at.AT_ERROR_KEY]:
            raise SoCError(f'{command} failed: {result[at.AT_RESPONSE_KEY]}.')
        return response[0][at.AT_PARAMS_KEY][0].rstrip()

    def _cgsn(self, param):
        """Use the +CGSN command to read several types of serial numbers."""
        command = '+CGSN'
        cmd = {at.AT_CMD_KEY:command,
               at.AT_TYPE_KEY:at.AT_TYPE_VALUE_SET,
               at.AT_PARAMS_KEY:[param]}
        result, response = self._chat.send_cmd(cmd)
        if len(response) != 1:
            raise SoCError(f'Unexpected response to {command}.')
        if result[at.AT_ERROR_KEY]:
            raise SoCError(f'{command} failed: {result[at.AT_RESPONSE_KEY]}.')
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
            raise SoCError(f'Unexpected response to {command}.')
        if result[at.AT_ERROR_KEY]:
            raise SoCError(f'{command} list failed: {result[at.AT_RESPONSE_KEY]}.')
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
            raise SoCError(f'{command} list failed: {result[at.AT_RESPONSE_KEY]}.')

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
            raise SoCError(f'{command} list failed: {result[at.AT_RESPONSE_KEY]}.')
        return [x[at.AT_PARAMS_KEY] for x in response if x[at.AT_RESPONSE_KEY] == command]

    def read_credential(self, sec_tag, cred_type):
        """Use %CMNG to read a credential. The sec_tag and cred_type parameters must
        be specified. Returns [] if there were no matching credentials.
        """
        command = '%CMNG'
        if cred_type == CRED_TYPE_PUBLIC_KEY:
            raise SoCError('Public keys can only be deleted.')
        if cred_type in (CRED_TYPE_CLIENT_CERT, CRED_TYPE_CLIENT_PRIVATE_KEY, CRED_TYPE_PSK):
            raise SoCError('Reading of cred_types 1, 2, and 3 is not supported.')
        cmd = {at.AT_CMD_KEY:command,
               at.AT_TYPE_KEY:at.AT_TYPE_VALUE_SET,
               at.AT_PARAMS_KEY:[OPCODE_READ, sec_tag, cred_type]}
        result, response = self._chat.send_cmd(cmd)
        if result[at.AT_ERROR_KEY]:
            raise SoCError(f'{command} list failed: {result[at.AT_RESPONSE_KEY]}.')
        credential = []
        cmd_echo = response.pop(0)
        if cmd_echo[at.AT_RESPONSE_KEY] != command:
            raise SoCError(f'Failed to parse output of {command} read.')
        verify_sec_tag, verify_cred_type, _, content = cmd_echo[at.AT_PARAMS_KEY]
        if verify_sec_tag != sec_tag or verify_cred_type != cred_type:
            raise SoCError(f'Failed to verify credential in output of {command} read.')
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
            raise SoCError(f'{command} write failed: {result[at.AT_RESPONSE_KEY]}.')

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
            raise SoCError(f'{command} delete failed: {result[at.AT_RESPONSE_KEY]}.')

    def get_attestation_token(self):
        """The response contains a device identity attestation message including the device type,
        device UUID, and COSE authentication metadata joined by a dot "." and coded to Base64url
        format.

        NOTE: Can also return None
        """
        command = '%ATTESTTOKEN'
        cmd = {at.AT_CMD_KEY:command, at.AT_TYPE_KEY:at.AT_TYPE_VALUE_SET}
        result, response = self._chat.send_cmd(cmd)
        if result[at.AT_ERROR_KEY]:
            msg = '{} get attestation token failed: ' + '{}.'
            raise SoCError(msg.format(command, result[at.AT_RESPONSE_KEY]))
        if response:
            return response[0][at.AT_PARAMS_KEY][0].rstrip()
        return None

    def generate_credential(self, sec_tag, key_type, response_content=None,
                            attributes=None, key_usage=None):
        """This command creates keys for different purposes:
         - Client private key and certificate signing request (CSR)
         - Client private key and public key
         - Device Endorsement key pair
        """
        command = '%KEYGEN'
        if self.get_functional_mode() == CFUN_MODE_NORMAL:
            raise SoCError('Generating credentials is not possible while modem is active.')
        if response_content == CRED_RESPONSE_CONTENT_CSR:
            if key_type != CRED_TYPE_CLIENT_PRIVATE_KEY:
                raise SoCError('Generating credentials failed because key_type ' +
                    f'{key_type} is not valid with response_content {response_content}.')
        elif response_content == CRED_RESPONSE_CONTENT_PUBLIC_KEY:
            if attributes or key_usage:
                raise SoCError('Generating credentials failed because attributes and ' +
                    'key_usage are only allowed when response_content is set to 0.')
            if not key_type in (CRED_TYPE_CLIENT_PRIVATE_KEY, CRED_TYPE_ENDORSEMENT_PRIVATE_KEY):
                raise SoCError('Generating credentials failed because key_type must be set to ' +
                    '2 or 8 when response_content is set to 1.')
        elif response_content:
            raise SoCError('Generating credentials failed because response_content ' +
                f'is not used for key_type {key_type}.')
        elif not response_content:
            if key_type == CRED_TYPE_CLIENT_PRIVATE_KEY:
                raise SoCError('Generating credentials failed because ' +
                    'response_content must be set to 0 when key_type is set to 2.')
        if key_usage:
            if isinstance(key_usage, int):
                key_usage = str(bin(key_usage))[2:]
            if not isinstance(key_usage, str):
                raise SoCError('Generating credentials failed due to unknown key_usage type.')
            if len(key_usage) != 9:
                raise SoCError('Generating credentials failed due to invalid ' +
                    f'key_usage str len ({len(key_usage)}).')
            try:
                int(key_usage, 2)
            except ValueError as err:
                raise SoCError("Generating credentials failed due to " +
                    "key_usage not being a valid binary str.") from err
            if key_usage[8] != '0':
                raise SoCError("Generating credentials failed " +
                    "because the decipherOnly digit is set.")
        cmd = {at.AT_CMD_KEY:command,
               at.AT_TYPE_KEY:at.AT_TYPE_VALUE_SET,
               at.AT_PARAMS_KEY:[sec_tag, key_type, response_content, attributes, key_usage]}
        result, response = self._chat.send_cmd(cmd)
        if result[at.AT_ERROR_KEY]:
            raise SoCError(f'{command} write failed: {result[at.AT_RESPONSE_KEY]}.')
        return response[0][at.AT_PARAMS_KEY][0]

    def generate_jwt(self, exp_delta=0, subject=None, audience=None,
                     sec_tag=None, key_type=None, alg=JWT_ALG_ES256):
        """This command creates a JSON Web Token (JWT). The following params are accepted:
         - alg - JWT signing algorithm, currently only ES256 (0) is supported

         - exp_delta - The number of seconds before expiry.
                       Requires the modem to have a correct date and time

         - subject - The "sub" (subject) claim for the JWT as defined in RFC 7519 4.1.2

         - audience - The "aud" (audience) claim for the JWT as defined in RFC 7519 4.1.3
                      NOTE: array not supported

         - sec_tag - Identifies the key to be used for signing the JWT

         - key_type - Type of the key to be used for signing the JWT
        """
        # %JWT=[<alg>],[<exp_delta>],[<subject>],[<audience>][,<sec_tag>,<key_type>]
        command = '%JWT'
        if key_type and not sec_tag:
            raise SoCError("Generating JWT failed because a key_type was " +
                "specified without a sec_tag.")
        if sec_tag and not key_type:
            raise SoCError("Generating JWT failed because a sec_tag was " +
                "specified without a key_type.")
        cmd = {at.AT_CMD_KEY:command,
               at.AT_TYPE_KEY:at.AT_TYPE_VALUE_SET,
               at.AT_PARAMS_KEY:[alg, exp_delta, subject, audience, sec_tag, key_type]}
        result, response = self._chat.send_cmd(cmd)
        if result[at.AT_ERROR_KEY]:
            raise SoCError(f'{command} write failed: {result[at.AT_RESPONSE_KEY]}.')
        return response[0][at.AT_PARAMS_KEY][0]
