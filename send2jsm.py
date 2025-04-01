#!/usr/bin/env python3
import argparse
import json
import logging
import os
import re
import sys
import time
from typing import Dict, Optional, Any
from urllib.parse import urlparse, urlunparse
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3.exceptions import InsecureRequestWarning
from requests.exceptions import RequestException, Timeout, ConnectionError

# Suppress only the single warning from urllib3 needed.
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Default configuration
DEFAULT_CONFIG = {
    "apiKey": "",
    "jsm.api.url": "https://api.atlassian.com",
    "zabbix2jsm.logger": "warning",
    "zabbix2jsm.http.proxy.enabled": "false",
    "zabbix2jsm.http.proxy.port": "1111",
    "zabbix2jsm.http.proxy.host": "localhost",
    "zabbix2jsm.http.proxy.protocol": "https",
    "zabbix2jsm.http.proxy.username": "",
    "zabbix2jsm.http.proxy.password": "",
    "timeout": "60"
}

# Logging levels mapping
LOG_LEVELS = {
    "info": logging.INFO,
    "debug": logging.DEBUG,
    "warning": logging.WARNING,
    "error": logging.ERROR
}

class ConfigurationError(Exception):
    """Custom exception for configuration errors"""
    pass

class Configuration:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = self._validate_url(base_url)

    @staticmethod
    def _validate_url(url_str: str) -> str:
        """Validate and normalize URL"""
        try:
            parsed = urlparse(url_str)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
            return url_str.rstrip('/')
        except Exception as e:
            raise ConfigurationError(f"Invalid URL format: {url_str}") from e

    @classmethod
    def from_json(cls, filepath: str) -> 'Configuration':
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                return cls(
                    api_key=data.get('apiKey', ''),
                    base_url=data.get('baseUrl', '')
                )
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error reading config file: {e}")

class JSMClient:
    def __init__(self, config_path: str = "/home/jsm/jec/conf/integration.conf",
                 jec_config_path: str = "/home/jsm/jec/conf/jec-config.json"):
        self.config = DEFAULT_CONFIG.copy()
        self.parameters: Dict[str, str] = {}
        self.total_time = 60
        self.logger = None
        
        self._load_config(config_path)
        self._load_jec_config(jec_config_path)
        self._setup_logging()

    def _load_config(self, config_path: str) -> None:
        try:
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            self.config[key] = value
                            if key == "timeout":
                                self.total_time = max(1, int(value))
                        except ValueError:
                            self.logger.warning(f"Invalid line in config file: {line}")
        except Exception as e:
            raise ConfigurationError(f"Error reading config file: {e}")

    def _load_jec_config(self, jec_config_path: str) -> None:
        try:
            jec_config = Configuration.from_json(jec_config_path)
            if not self.config["apiKey"]:
                self.config["apiKey"] = jec_config.api_key
            if self.config["jsm.api.url"] != jec_config.base_url:
                self.config["jsm.api.url"] = jec_config.base_url
        except Exception as e:
            raise ConfigurationError(f"Error reading JEC config file: {e}")

    def _setup_logging(self) -> None:
        log_level = LOG_LEVELS.get(self.config["zabbix2jsm.logger"].lower(), logging.WARNING)
        log_path = self.parameters.get("logPath", "/var/log/jec/send2jsm.log")
        log_dir = os.path.dirname(log_path)

        try:
            # Check if directory exists and is writable
            if not os.path.exists(log_dir):
                Path(log_dir).mkdir(parents=True, exist_ok=True)
            
            if not os.access(log_dir, os.W_OK):
                raise PermissionError(f"No write permission for log directory: {log_dir}")

            logging.basicConfig(
                filename=log_path,
                level=log_level,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
        except Exception as e:
            print(f"Could not create log file '{log_path}', will log to '/tmp/send2jsm.log'. Error: {e}")
            try:
                logging.basicConfig(
                    filename="/tmp/send2jsm.log",
                    level=log_level,
                    format='%(asctime)s - %(levelname)s - %(message)s'
                )
            except Exception as e:
                print(f"Logging disabled. Reason: {e}")

        self.logger = logging.getLogger(__name__)

    def _get_http_client(self, timeout: int) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        if self.config["zabbix2jsm.http.proxy.enabled"].lower() == "true":
            proxy_host = self.config["zabbix2jsm.http.proxy.host"]
            proxy_port = self.config["zabbix2jsm.http.proxy.port"]
            proxy_protocol = self.config["zabbix2jsm.http.proxy.protocol"]
            proxy_username = self.config["zabbix2jsm.http.proxy.username"]
            proxy_password = self.config["zabbix2jsm.http.proxy.password"]

            proxy_url = f"{proxy_protocol}://{proxy_host}:{proxy_port}"
            if proxy_username and proxy_password:
                proxy_url = f"{proxy_protocol}://{proxy_username}:{proxy_password}@{proxy_host}:{proxy_port}"

            session.proxies = {
                "http": proxy_url,
                "https": proxy_url
            }

        return session

    def _validate_response(self, response: requests.Response) -> bool:
        """Validate the response from the server"""
        try:
            response.raise_for_status()
            response.json()  # Validate JSON response
            return True
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error occurred: {e}")
            return False
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON response: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error validating response: {e}")
            return False

    def send_data(self) -> None:
        if not self.config["apiKey"]:
            raise ConfigurationError("API key is not configured")

        self.parameters["apiKey"] = self.config["apiKey"]
        log_prefix = f"[TriggerId: {self.parameters.get('triggerId', '')}, HostName: {self.parameters.get('hostName', '')}]"
        
        api_url = f"{self.config['jsm.api.url']}/jsm/ops/integration/v1/json/zabbix"
        target = "JSM"

        self.logger.debug(f"URL: {api_url}")
        # Mask sensitive data in logs
        safe_params = {k: '*******' if 'password' in k or 'key' in k else v 
                      for k, v in self.parameters.items()}
        self.logger.debug(f"Data to be posted: {safe_params}")

        for attempt in range(1, 4):
            timeout = max(1, (self.total_time / 12) * 2 * attempt)
            self.logger.debug(f"{log_prefix} Trying to send data to {target} with timeout: {timeout}")

            try:
                session = self._get_http_client(attempt)
                response = session.post(
                    api_url,
                    json=self.parameters,
                    verify=False,
                    timeout=timeout
                )

                if self._validate_response(response):
                    self.logger.debug(f"{log_prefix} Response code: {response.status_code}")
                    self.logger.debug(f"{log_prefix} Response: {response.text}")
                    self.logger.info(f"{log_prefix} Data from Zabbix posted to {target} successfully")
                    return
                else:
                    self.logger.error(f"{log_prefix} Failed to post data. Status code: {response.status_code}")
                    self.logger.error(f"{log_prefix} Response: {response.text}")

            except Timeout:
                self.logger.error(f"{log_prefix} Request timed out")
                if attempt == 3:
                    self.logger.error(f"{log_prefix} All attempts failed to send data to {target}")
                    sys.exit(1)
            except ConnectionError:
                self.logger.error(f"{log_prefix} Connection error occurred")
                if attempt == 3:
                    self.logger.error(f"{log_prefix} All attempts failed to send data to {target}")
                    sys.exit(1)
            except Exception as e:
                self.logger.error(f"{log_prefix} Error occurred while sending data: {str(e)}")
                if attempt == 3:
                    self.logger.error(f"{log_prefix} All attempts failed to send data to {target}")
                    sys.exit(1)
            time.sleep(1)

def parse_args() -> Dict[str, str]:
    parser = argparse.ArgumentParser(description='Send data to JSM')
    parser.add_argument('-v', '--version', action='store_true', help='Show version')
    
    # Add all other parameters as arguments
    for key in DEFAULT_CONFIG.keys():
        parser.add_argument(f'--{key}', help=f'Set {key}')
    
    args = parser.parse_args()
    
    if args.version:
        print("Version: 1.1")
        sys.exit(0)
    
    return {k: v for k, v in vars(args).items() if v is not None}

def remove_special_characters(param: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', param)

def main():
    try:
        client = JSMClient()
        parameters = parse_args()
        
        # Update parameters with command line arguments
        client.parameters.update(parameters)
        
        # Print configuration to log
        if client.logger and client.logger.isEnabledFor(logging.DEBUG):
            client.logger.debug("Config:")
            for k, v in client.config.items():
                if "password" in k or "key" in k:
                    client.logger.debug(f"{k}=*******")
                else:
                    client.logger.debug(f"{k}={v}")
        
        client.send_data()
    except ConfigurationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 