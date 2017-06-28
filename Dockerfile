#
#Dockerfile to build the backup utility image
#
FROM centos:7
MAINTAINER Traiano Welcome "traiano@gmail.com"
RUN yum -y update
RUN yum -y install yum-utils
RUN yum -y groupinstall development 
RUN yum -y install https://centos7.iuscommunity.org/ius-release.rpm
RUN yum -y install python36u
RUN yum -y install python36u-pip
RUN yum -y install cronie
RUN pip3.6 install boto3
ADD backup.py /backup.py
ADD cronjob.txt /cronjob.txt
CMD /bin/crontab /cronjob.txt
WORKDIR /
