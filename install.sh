#!/bin/bash

sudo apt update && apt install mysql-server libmysqlclient-dev libxml2-dev curl apt-transport-https ca-certificates curl software-properties-common snapd pkg-config python3-pip python3 python-dev python3-dev build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev -y

go get github.com/jbowtie/gokogiri
