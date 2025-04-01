# !/usr/bin/env python3
import argparse
import json
import sys
import logging
import os
from send2jsm import JSMClient

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


def send_alert(alert_data):
    """
    Sends an alert using JSMClient

    Args:
        alert_data (dict): Dictionary containing alert data
    """
    try:
        # Create JSM client
        client = JSMClient()

        # Update parameters with alert data
        client.parameters.update(alert_data)

        # Send data
        client.send_data()

        print("\nAlert sent successfully!")

    except Exception as e:
        print(f"Error sending alert: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Send alert to JSM')

    # Add arguments for alert data
    parser.add_argument('--triggerName', required=True, help='Trigger Name')
    parser.add_argument('--triggerId', required=True, help='Trigger ID')
    parser.add_argument('--triggerStatus', required=True, help='Trigger Status')
    parser.add_argument('--triggerSeverity', required=True, help='Trigger Severity')
    parser.add_argument('--triggerDescription', required=True, help='Trigger Description')
    parser.add_argument('--triggerUrl', required=True, help='Trigger Url')
    parser.add_argument('--triggerValue', required=True, help='Trigger Value')
    parser.add_argument('--triggerHostGroupName', required=True, help='Trigger HostGroupName')
    parser.add_argument('--hostName', required=True, help='Host name')
    parser.add_argument('--ipAddress', required=True, help='ipAddress')
    parser.add_argument('--eventId', required=True, help='eventId')
    parser.add_argument('--date', required=True, help='date')
    parser.add_argument('--time', required=True, help='time')
    parser.add_argument('--itemKey', required=True, help='itemKey')
    parser.add_argument('--itemValue', required=True, help='itemValue')
    parser.add_argument('--recoveryEventStatus', required=True, help='recoveryEventStatus')

    args = parser.parse_args()

    # Create dictionary with alert data
    alert_data = {
        'triggerName': args.triggerName,
        'triggerId': args.triggerId,
        'triggerStatus': args.triggerStatus,
        'triggerSeverity': args.triggerSeverity,
        'triggerDescription': args.triggerDescription,
        'triggerUrl': args.triggerUrl,
        'triggerValue': args.triggerValue,
        'triggerHostGroupName': args.triggerHostGroupName,
        'hostName': args.hostName,
        'ipAddress': args.ipAddress,
        'eventId': args.eventId,
        'date': args.date,
        'time': args.time,
        'itemKey': args.itemKey,
        'itemValue': args.itemValue,
        'recoveryEventStatus': args.recoveryEventStatus
    }

    # Send the alert
    send_alert(alert_data)

if __name__ == "__main__":
    main()
