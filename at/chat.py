"""
The purpose of this module is to handle sending commands and receiving responses from
a serial port in a separate thread.
"""
import threading
import queue
import serial

import at


class ChatError(Exception):
    """ChatThrad exception class, inherits from the built-in Exception class."""

    def __init__(self, error_str=None):
        """Constructs a new object and sets the error."""
        if error_str:
            self.err_str = f'Chat error: {error_str}'
        else:
            self.err_str = 'Chat error'
        Exception.__init__(self, self.err_str)


class Chat():
    """Simplifies the process of sending AT commands to a modem and waiting for a response."""

    def __init__(self, port):
        """Create a new object and open the specified serial port."""
        self._rx_q = queue.Queue()
        self._tx_q = queue.Queue()
        self._closed = False
        self._thread = ChatThread(self._rx_q, self._tx_q, port)
        self._thread.start()

    def _raise_thread_errors(self):
        """Iterate through the information that was sent back from the thread
        and raise any Exceptions that were encountered.
        """
        while not self._rx_q.empty():
            item = self._rx_q.get()
            if isinstance(item, Exception):
                raise item
        self.close()

    def _read(self, block=True, timeout_s=None):
        """Read a response line as a string. Return None if block is False
        and there is no data to read.
        """
        if self._closed:
            raise ChatError("Port is closed.")
        if self._thread.is_closed():
            if self._rx_q.empty():
                self.close()
                raise ChatError('Thread closed unexpectedly.')
            self._raise_thread_errors()
        if not block and self._rx_q.empty():
            return None
        item = self._rx_q.get(block, timeout_s)
        if isinstance(item, str):
            return item
        raise ChatError(str(item))

    def _write(self, seq):
        """Write the string or bytes seq to the serial port."""
        if self._closed:
            raise ChatError("Port is closed.")
        if self._thread.is_closed():
            if self._rx_q.empty():
                self.close()
                raise ChatError('Thread closed unexpectedly.')
            self._raise_thread_errors()
        self._tx_q.put(seq)

    def send_cmd(self, cmd, timeout_s=5):
        """Send a command to the serial port and wait for a response that is either
        an OK or an ERROR. The cmd parameter can be a string or a dict from the at
        module. Any responses that arrive before the OK or ERROR will be returned
        along with the final response as part of a tuple: (result, [responses]).
        """
        responses = []
        if self._closed:
            raise ChatError("Port is closed.")
        if isinstance(cmd, str):
            self._write(cmd)
        elif isinstance(cmd, dict):
            cmd_str = at.encode_command(cmd)
            self._write(cmd_str)
        while True:
            try:
                line = self._read(True, timeout_s)
            except queue.Empty as exc:
                raise ChatError(f'Command timed out ({timeout_s} seconds).') from exc
            if line:
                res = at.parse_string(line)
                if res[at.AT_TYPE_KEY] == at.AT_TYPE_VALUE_RESPONSE:
                    if res[at.AT_RESPONSE_KEY] == at.AT_RSP_OK or res[at.AT_ERROR_KEY]:
                        return (res, responses)
                    responses.append(res)

    def close(self):
        """Close the serial port."""
        if self._closed:
            raise ChatError("Port is already closed.")
        self._closed = True
        self._thread.close()

    def is_closed(self):
        """Return True if the thread was manually closed or closed due to an error."""
        return self._closed


class ChatThread(threading.Thread):
    """Creates a simple thread for interacting with a serial port."""
    DEFAULT_BAUDRATE = 115200
    DEFAULT_TIMEOUT_S = 0.5
    CR_LF_BYTES = b'\r\n'
    CR_LF_STR = '\r\n'
    NULL_BYTE = b'\x00'

    def __init__(self, rx_queue, tx_queue, port, baudrate=DEFAULT_BAUDRATE):
        """Create a new object but do not start the thread."""
        super().__init__()
        self.daemon = True
        self._rx_q = rx_queue
        self._tx_q = tx_queue
        self._port = port
        self._baudrate = baudrate
        self._closed = False
        self._stop = threading.Event()

    def _term_and_encode(self, seq):
        """Ensure that seq terminates with <CR><LF> and convert to bytes if necessary."""
        if isinstance(seq, str):
            if seq.endswith(self.CR_LF_STR):
                return seq.encode()
            return "".join((seq, self.CR_LF_STR)).encode()
        if seq.endswith(self.CR_LF_BYTES):
            return seq
        return b''.join((seq, self.CR_LF_BYTES))

    def run(self):
        """Interact with the serial port until the semaphore is set.
        NOTE: Automatically decodes received bytes into strings.
        """
        ser = None
        try:
            ser = serial.Serial(self._port, self._baudrate, timeout=self.DEFAULT_TIMEOUT_S)
            while not self._stop.is_set():
                while not self._tx_q.empty():
                    tx_item = self._tx_q.get()
                    ser.write(self._term_and_encode(tx_item))
                line = ser.readline()
                if line and line != self.NULL_BYTE:
                    self._rx_q.put(line.decode())
        except serial.SerialException as err:
            self._rx_q.put(err)
        finally:
            if ser:
                ser.close()
            self.close()

    def close(self):
        """Set the semaphore to instruct the thread to close."""
        self._stop.set()
        self._closed = True

    def is_closed(self):
        """Return True if the thread was manually closed or closed due to an error."""
        return self._closed
