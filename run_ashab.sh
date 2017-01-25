#!/bin/bash
sleep 20
cd /home/pi/ASHAB/ns1
{
    python3 /home/pi/ASHAB/ns1/nsx.py
} >> /home/pi/startup.log 2>&1

