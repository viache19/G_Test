#!/usr/bin/env python3
import argparse
import json
import sys
from send2jsm import JSMClient

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
    parser.add_argument('--triggerId', required=True, help='Trigger ID')
    parser.add_argument('--hostName', required=True, help='Host name')
    parser.add_argument('--eventName', required=True, help='Event name')
    parser.add_argument('--severity', required=True, choices=['High', 'Medium', 'Low'], help='Event severity')
    parser.add_argument('--description', required=True, help='Event description')
    parser.add_argument('--status', required=True, choices=['Problem', 'Resolved'], help='Event status')
    
    # Optional arguments
    parser.add_argument('--additionalData', help='Additional data in JSON format')
    parser.add_argument('--config_path', default='integration.conf', help='Path to integration config file')
    parser.add_argument('--jec_config_path', default='jec-config.json', help='Path to JEC config file')
    
    args = parser.parse_args()
    
    # Create dictionary with alert data
    alert_data = {
        'triggerId': args.triggerId,
        'hostName': args.hostName,
        'eventName': args.eventName,
        'severity': args.severity,
        'description': args.description,
        'status': args.status
    }
    
    # Add additional data if provided
    if args.additionalData:
        try:
            additional_data = json.loads(args.additionalData)
            alert_data.update(additional_data)
        except json.JSONDecodeError:
            print("Error: Additional data must be in valid JSON format")
            sys.exit(1)
    
    # Send the alert
    send_alert(alert_data)

if __name__ == "__main__":
    main() 
