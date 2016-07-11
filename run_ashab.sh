#!/bin/bash
sleep 30
cd /home/pi/ashab
{
    python /home/pi/ashab/nsx.py
} >> /home/pi/startup.log 2>&1

