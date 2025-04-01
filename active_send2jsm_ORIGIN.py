#!/usr/bin/env python3
import re
import sys
import logging
import subprocess
"""
Originaly the JSM script is awaiting for this data.

/home/jsm/jec/scripts/send2jsm  -triggerName='{TRIGGER.NAME}'
                                -triggerId='{TRIGGER.ID}'
                                -triggerStatus='{TRIGGER.STATUS}'
                                -triggerSeverity='{TRIGGER.SEVERITY}'
                                -triggerDescription='{TRIGGER.DESCRIPTION}'
                                -triggerUrl='{TRIGGER.URL}'
                                -triggerValue='{TRIGGER.VALUE}'
                                -triggerHostGroupName='{TRIGGER.HOSTGROUP.NAME}'
                                -hostName='{HOST.NAME}'
                                -ipAddress='{IPADDRESS}'
                                -eventId='{EVENT.ID}'
                                -date='{DATE}'
                                -time='{TIME}'
                                -itemKey='{ITEM.KEY}'
                                -itemValue='{ITEM.VALUE}'
                                -recoveryEventStatus='{EVENT.RECOVERY.STATUS}'

##### Zabbix Media Type - Message configuration #####
triggerName:{TRIGGER.NAME}
triggerId:{TRIGGER.ID}
triggerStatus:{TRIGGER.STATUS}
triggerSeverity:{TRIGGER.SEVERITY}
triggerDescription:{TRIGGER.DESCRIPTION}
triggerUrl:{TRIGGER.URL}
triggerValue:{TRIGGER.VALUE}
triggerHostGroupName:{TRIGGER.HOSTGROUP.NAME}
hostName:{HOST.NAME}
ipAddress:{IPADDRESS}
eventId:{EVENT.ID}
date:{DATE}
time:{TIME}
itemKey:{ITEM.KEY}
itemValue:{ITEM.VALUE}
recoveryEventStatus:{EVENT.RECOVERY.STATUS}
"""


def parse_alert_message(text):
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

logging.basicConfig(
    filename='/var/log/jec/send2jsm.log',
    level=logging.INFO,
    format='[PYTHON WRAPPER] - %(asctime)s - %(levelname)s - %(message)s',
)

if len(sys.argv) < 2:
    logging.error("You need to include at least one parameter")
    sys.exit(1)

alert_message = sys.argv[1]

logging.info(f"Alert message: {alert_message}")
parsed_data = parse_alert_message(alert_message)

logging.info(f"Parsed data: {parsed_data}")
logging.info("Trying to send data to send2jsm")

command = ["/home/jsm/jec/scripts/send2jsm.py"]

for key, value in parsed_data.items():
    command.append(f"-{key}={value}")

logging.info(f"This is the command: {command}")
result = subprocess.run(command, capture_output=True, text=True)

logging.info(f"Result: {result}")

if result.returncode == 0:
    logging.info(f"The script was executed correctly.")
    # logging.info(f"Output: {result.stdout}") <- doesn't make sence, the stdout is empty
    sys.exit(0)
else:
    logging.error(f"There was an error while executing the script")
    # logging.error(f"Error Output:{result.stderr}") <- doesn't make sence, the stdout is empty
    sys.exit(0)