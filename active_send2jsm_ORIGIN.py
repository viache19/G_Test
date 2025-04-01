#!/usr/bin/env python3
import subprocess
import sys
import os
import re
import logging
from typing import Dict, Any

def setup_logging():
    """Configure logging"""
    try:
        os.makedirs('/var/log/jec', exist_ok=True)
        logging.basicConfig(
            filename='/var/log/jec/send2jsm.log',
            level=logging.INFO,
            format='[PYTHON WRAPPER] - %(asctime)s - %(levelname)s - %(message)s',
        )
    except Exception as e:
        print(f"Warning: Could not set up logging: {e}", file=sys.stderr)
        logging.basicConfig(
            filename='/tmp/send2jsm.log',
            level=logging.INFO,
            format='[PYTHON WRAPPER] - %(asctime)s - %(levelname)s - %(message)s',
        )

def parse_alert_message(text: str) -> Dict[str, str]:
    """Parse the alert message in the specified format"""
    parsed_data = {}
    key = None
    value_lines = []

    for line in text.splitlines():
        match = re.match(r"^(\w+):\s*(.*)", line)
        if match:
            if key is not None:
                parsed_data[key] = "\n".join(value_lines).strip()
            key, value = match.groups()
            value_lines = [value]
        else:
            value_lines.append(line)

    if key is not None:
        parsed_data[key] = "\n".join(value_lines).strip()

    return parsed_data

def convert_to_send2jsm_format(data: Dict[str, str]) -> Dict[str, str]:
    """Convert the parsed data to the format expected by send2jsm.py"""
    # Mapping of field names from Zabbix format to send2jsm format
    field_mapping = {
        'triggerName': 'eventName',
        'triggerId': 'triggerId',
        'triggerStatus': 'status',
        'triggerSeverity': 'severity',
        'triggerDescription': 'description',
        'triggerUrl': 'url',
        'triggerValue': 'value',
        'triggerHostGroupName': 'hostGroup',
        'hostName': 'hostName',
        'ipAddress': 'ipAddress',
        'eventId': 'eventId',
        'date': 'date',
        'time': 'time',
        'itemKey': 'itemKey',
        'itemValue': 'itemValue',
        'recoveryEventStatus': 'recoveryStatus'
    }
    
    converted_data = {}
    for zabbix_key, send2jsm_key in field_mapping.items():
        if zabbix_key in data:
            converted_data[send2jsm_key] = data[zabbix_key]
    
    return converted_data

def run_send2jsm(data: Dict[str, str], config_path: str = "integration.conf", 
                 jec_config_path: str = "jec-config.json") -> int:
    """Run the send2jsm.py script with the converted data"""
    cmd = ["python3", "send2jsm.py"]
    
    # Add data parameters
    for key, value in data.items():
        cmd.extend([f"--{key}", value])
    
    try:
        logging.info(f"Executing command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logging.info("Script executed successfully")
            return 0
        else:
            logging.error(f"Script failed with return code: {result.returncode}")
            if result.stderr:
                logging.error(f"Error output: {result.stderr}")
            return result.returncode
            
    except Exception as e:
        logging.error(f"Error executing script: {e}")
        return 1

def main():
    setup_logging()
    
    if len(sys.argv) < 2:
        logging.error("You need to include at least one parameter")
        sys.exit(1)

    # Get the alert message from command line arguments
    alert_message = sys.argv[1]
    logging.info(f"Received alert message: {alert_message}")
    
    try:
        # Parse the alert message
        parsed_data = parse_alert_message(alert_message)
        logging.info(f"Parsed data: {parsed_data}")
        
        # Convert to send2jsm format
        converted_data = convert_to_send2jsm_format(parsed_data)
        logging.info(f"Converted data: {converted_data}")
        
        # Run send2jsm
        exit_code = run_send2jsm(converted_data)
        sys.exit(exit_code)
        
    except Exception as e:
        logging.error(f"Error processing alert: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
