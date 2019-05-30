"""
Signal Messenger for notify component.
Place this in homeassistant/custom_components/signalmessenger/notify.py
"""
import pathlib
import subprocess
import logging
import requests
import voluptuous as vol
import os
import base64

from os import path
from homeassistant.components.notify import (
     ATTR_DATA, ATTR_TITLE, ATTR_TITLE_DEFAULT, PLATFORM_SCHEMA,
     BaseNotificationService)
from homeassistant.const import CONF_API_KEY
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = []

_LOGGER = logging.getLogger("signalmessenger")

CONF_SENDER_NR = 'sender_nr'
CONF_RECP_NR = 'recp_nr'
CONF_SIGNAL_CLI_REST_API = 'signal_cli_rest_api'

ATTR_FILENAME = 'filename'
ATTR_DELETE_FILE_AFTER_SEND = 'delete_file_after_send'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
vol.Optional(CONF_SENDER_NR): cv.string,
vol.Optional(CONF_SIGNAL_CLI_REST_API): cv.string,
vol.Optional(CONF_RECP_NR): vol.All(cv.ensure_list, [cv.string])
})

def get_service(hass, config, discovery_info=None):
    sender_nr = config.get(CONF_SENDER_NR)
    recp_nrs = config.get(CONF_RECP_NR)
    signal_cli_rest_api = config.get(CONF_SIGNAL_CLI_REST_API)

    if signal_cli_rest_api is None:
        _LOGGER.error("Please specify the URL to the signal-cli REST API")
        return False

    if recp_nrs is None:
        _LOGGER.error("Please specify at least one recp_nr")
        return False

    if sender_nr is None:
        _LOGGER.error("Please provide a sender_nr")
        return False

    return SignalNotificationService(sender_nr, recp_nrs, signal_cli_rest_api)

class SignalNotificationService(BaseNotificationService):

    def __init__(self, sender_nr, recp_nrs, signal_cli_rest_api):
        self._sender_nr = sender_nr
        self._recp_nrs = recp_nrs
        self._signal_cli_rest_api = signal_cli_rest_api

    def send_message(self, message="", **kwargs):
        _LOGGER.info("SENDING SIGNAL MESSAGE")
        
        data = kwargs.get(ATTR_DATA, None)

        filename = None
        if data is not None and ATTR_FILENAME in data:
            filename = data[ATTR_FILENAME]

        delete_file_after_send = None
        if data is not None and ATTR_DELETE_FILE_AFTER_SEND in data:
            delete_file_after_send = data[ATTR_DELETE_FILE_AFTER_SEND]
        try: 
            data = {"message": message, "number": self._sender_nr, "recipients": self._recp_nrs}
            if filename is not None:
                with open(filename, "rb") as f:
                    data["base64_attachment"] = base64.b64encode(f.read())
            resp = requests.post(self._signal_cli_rest_api + "/v1/send", json=data)
            _LOGGER.info(self._signal_cli_rest_api + "/v1/send")
            if resp.status_code != 201:
                json_resp = resp.json()
                if "error" in json_resp:
                    raise Exception(json_resp["error"])
                raise Exception("unknown error while sending signal message")
        except Exception as e:
            _LOGGER.error(str(e))
            raise e

        if delete_file_after_send is not None:
            if delete_file_after_send and filename is not None:
                try:
                    if os.path.isfile(filename):
                        os.remove(filename)
                except Exception as e:
                    _LOGGER.error(str(e))
                    raise e

