#!/bin/bash

PACKSRC=`pwd`
source ${PACKSRC}/config.ini


# Install WebSkins
cp -r ${PACKSRC}/WebSkins/* /var/CommuniGate/WebSkins/
chmod +x ${PACKSRC}/cgi/*
cp ${PACKSRC}/cgi/* /var/CommuniGate/cgi/

service CommuniGate stop
service CommuniGate start
