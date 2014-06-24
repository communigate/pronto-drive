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

vercomp () {
    if [[ $1 == $2 ]]
    then
        return 0
    fi
    local IFS=.
    local i ver1=($1) ver2=($2)
    # fill empty fields in ver1 with zeros
    for ((i=${#ver1[@]}; i<${#ver2[@]}; i++))
    do
        ver1[i]=0
    done
    for ((i=0; i<${#ver1[@]}; i++))
    do
        if [[ -z ${ver2[i]} ]]
        then
            # fill empty fields in ver2 with zeros
            ver2[i]=0
        fi
        if ((10#${ver1[i]} > 10#${ver2[i]}))
        then
            return 1
        fi
        if ((10#${ver1[i]} < 10#${ver2[i]}))
        then
            return 2
        fi
    done
    return 0
}

if [ `perl -MGD::Barcode::QRcode -e 1 2>&1 | wc -l` -ne "0" ]
then
    echo "!!! Please install perl module GD::Barcode::QRcode !!!";
fi
if [ `perl -MIO::Compress::Zip -e 1 2>&1 | wc -l` -ne "0" ]
then
    echo "!!! Please install perl module IO::Compress::Zip !!!";
else
   VERSION=`perl -MIO::Compress::Base -e 'print $IO::Compress::Base::VERSION'`;
   vercomp "2.040" $VERSION;
   if [ $? == 1 ]
   then
       echo "!!! Please install perl module IO::Compress::Zip with version at least 2.040 !!!";
   fi;
fi

