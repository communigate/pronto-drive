#!/bin/bash

PACKSRC=`pwd`
source ${PACKSRC}/config.ini


# Install WebSkins
mkdir -p /var/CommuniGate/WebSkins
cp -r ${PACKSRC}/WebSkins/* /var/CommuniGate/WebSkins/
mkdir -p /var/CommuniGate/cgi/
chmod +x ${PACKSRC}/cgi/*
cp ${PACKSRC}/cgi/* /var/CommuniGate/cgi/

service CommuniGate stop
service CommuniGate start
