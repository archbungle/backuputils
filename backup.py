#!/bin/python3
#Simple, reliable backup script for backing up documents to an NFS share
#from S3
#Provides logging, error handling and alerting.
#blame: traiano@gmail.com
#1. Determine the current week and create a pattern matching string
#2. Connect to S3 bucket and list all files matching that pattern (combine with step below if possible) (log this step, alert on fail)
#3. Get all the files matching the pattern and copy to a temporary folder (log this step)
#4. Mount the NFS share on /mnt (log this step and alert on fail - try - catch)
#5. Copy all files from the temp folder to /mount (log this step)
#6. Sync and unmount the NFS share (log, alert on failure)
#7. Log a summary of the backup run to the s3 bucket (log and alert on failure)
#8. A Separate script handles reports: End of day run a report of backup operations - send email report after processing logs

import time
import datetime
import subprocess
import os
import zipfile
import boto3

#Configurable script variables below
nfs_host="172.31.25.0"
local_mount_point="/mnt"
bucket_list=[]
bucket_name="document-submissions"
tstamp = int(round(time.time() * 1000))
log_file="/tmp/"+"backup-"+str(tstamp)+".log"
key="backup-"+str(tstamp)+".log"

def mount_share():
 result=0
 mount_command="/bin/mount "+nfs_host+":/data/ "+local_mount_point
 message="mounting remote NFS share with: "+mount_command
 log_to_file(log_file,message)
 result=os.system(mount_command)
 return result

def unmount_share():
 result=0
 sync_command="/bin/sync"
 umount_command="/bin/umount "+"/mnt"
 message="Unmounting remote NFS share with: "+umount_command
 log_to_file(log_file,message)
 print(umount_command)
 os.system(sync_command)
 result=os.system(umount_command)
 return result

#[] Determine the current week and create a pattern matching string
def get_search_tag():
 search_tag=""
 now = datetime.datetime.now()
 nyear=now.year
 nmonth=now.month

 nday=now.day
 week = datetime.date(nyear, nmonth, nday).isocalendar()[1]
 search_tag = str(nyear)+"_"+str(week)
 message="Searching for documents matching: "+search_tag
 log_to_file(log_file,message)
 return search_tag 

# Connect to S3 bucket and list all files matching that pattern (combine with step below if possible) (log this step, alert on fail)
# Get all the files matching the pattern and copy to a temporary folder (log this step)
def list_s3files(search_tag):
 file_count=0
 s3 = boto3.resource('s3')
 bucket = s3.Bucket('document-submissions')
 for obj in bucket.objects.all():
  if(search_tag in obj.key):
   bucket_list.append(obj.key)
   file_count+=1
 message="Connected to S3 and found "+str(file_count)+" documents matching this week."
 log_to_file(log_file,message)
 if(file_count==0):
  message="Found 0 relevant documents in S3. Quitting ..." 
  log_to_file(log_file,message)
 return file_count

#make temporary directory to store s3 downloads:
def make_temp():
 path="/tmp/"
 ts=str(time.time())
 path="/tmp/"+ts
 os.mkdir(path)
 message="Created temporary local directory: "+path
 log_to_file(log_file,message)
 return path

def get_s3files(path):
 s3_client = boto3.client('s3')
 fcount=0
 for key in bucket_list:
  local_key=path+"/"+key
  s3_client.download_file(bucket_name, key, local_key)
  fcount += 1
 message="Downloaded "+str(fcount)+" files from S3"
 log_to_file(log_file,message)
 #get all the files in the bucket list
 return fcount

#copy all files from the temp folder to /mount (log this step)
#list all the files on the share, validate against the list of files originally copied (log and alert on failure)
def copy_to_mount(src_dir,dst_dir):
 result=1
 copy_command="/bin/cp "+src_dir+"/* "+dst_dir+"/"
 result=os.system(copy_command)
 result=0
 message="Copied all downloaded files to "+dst_dir+" result was: "+str(result)
 log_to_file(log_file,message)

 return result

#log a summary of the backup run to the s3 bucket (log and alert on failure)
def log_to_s3():
 result=0
 message="Pushing backup log to S3: "+log_file
 log_to_file(log_file,message)
 return result

def log_to_file(log_file,message):
 result=1
 fobj=open(log_file,"a")
 time_stamp = time.strftime("%c")
 fobj.write(time_stamp+": "+message+"\n")
 result=fobj.close()
 return result

#move the log to S3
def log_to_s3(log_file,key,destination_bucket):
 source_file=log_file
 s3 = boto3.resource(service_name="s3", region_name="ap-southeast-1")
 data = open(source_file, 'rb')
 s3.Bucket(destination_bucket).put_object(Key=key, Body=data)

#get the search_tag
search_tag=get_search_tag()
#get the files in the bucket
fc_s3=list_s3files(search_tag)
#download to temp directory
path=make_temp()
fclocal=get_s3files(path)

#Just to be sure, unmount the NFS share:
result=unmount_share()
if(result==0): print("Unmount Result OK: "+str(result))
else: print("Unmount NOT OK")

#mount the NFS share
result=mount_share()
print("Mount Result: "+str(result))
if(result==0): print("mount OK ...")
else: print("Mount NOT OK")

#Copy the files to the NFS share
copy_to_mount(path,local_mount_point)

#unmount the NFS share
result=unmount_share()
if(result==0): print("Unmount Result OK: "+str(result))
else: print("Unmount NOT OK")

#push the log to S3 for forensics
log_to_s3(log_file,key,bucket_name)
