#!/usr/bin/python3

import copy
import os
import sys
import datetime
import re
from datetime import datetime
from pathlib import Path

# Define the format of the datetime strings
datetime_format = "%Y-%m-%d %H:%M:%S"
scanloglocation = "/home/ubuntu//scanlogs"
scanscorethreshold = 0
servsummary = []
manifestlocation = "/home/ubuntu/cmu-artifacts/Deploy/manifests/"
microserv = []

print('##########################################################')
print('Image Update beginning')
print('##########################################################\n')

print('##########################################################')
print('Check for new tags in git')
print('##########################################################\n')
changeserv = []
command = "git -C " + manifestlocation + " pull"
stream = os.popen(command)
output = stream.read()
output = output.split('\n')
for line in range(len(output)):
    if re.match(r' Deploy\/manifests\/\w+_rollout.yaml.*', output[line], re.M | re.I):
        servcha = re.search(r' Deploy\/manifests\/(\w+)_rollout.yaml.*', output[line], re.M | re.I)
        if servcha.group(1) != 'shoppingassistantservice':
            microserv.append(servcha.group(1))

if len(microserv) != 0:
    print('Following services have new tags and will be updated:')
    for serv1 in range(len(microserv)):
        print('%s', microserv[serv1])
    print('\n')
    for serv in range(len(microserv)):
        summary = []
        print('##########################################################')
        print('Updating %s' % microserv[serv])
        print('##########################################################\n')
        print('Checking the rollout health and image tag for %s\n' % microserv[serv])
        command = "kubectl argo rollouts get rollout " + microserv[serv] + " -n onlineboutique"
        stream = os.popen(command)
        output = stream.read()
        output = output.split('\n')
        for line in range(len(output)):
            if re.match(r'^Status\:.*', output[line], re.M | re.I):
                if re.match(r'^Status\:.*(Healthy)', output[line], re.M | re.I):
                    servstat = 1
                    print("Status of %s is Healthy, Will Check for newer tags in git repo\n"% microserv[serv])
                    summary = [microserv[serv],'healthy']
                else:
                    servstat = 0
                    print("Status of %s Not Healthy, Moving onto next service\n" % microserv[serv])
                    summary = [microserv[serv],'unhealthy']
                    break
            if re.match(r'^Images\:\s+cmupro7/\w+:(\d+)',output[line], re.M | re.I):
                tagprod = re.search(r'^Images\:\s+cmupro7/\w+:(\d+)',output[line], re.M | re.I)
                print("Tag in production is %s\n"% tagprod.group(1))
        if(servstat == 1):
            print("Finding the new tag number for %s\n" % microserv[serv])
            command1 = 'grep image ' + manifestlocation + microserv[serv] + '_rollout.yaml'
            stream1 = os.popen(command1)
            output1 = stream1.read()
            output1 = output1.split('\n')
            taggitlist = []
            #Create a list of the tags
            for line in range(len(output1)):
                if re.match(r'^\s+image\: cmupro7/\w+:\d+', output1[line], re.M | re.I):
                    tagsko = re.search(r'^\s+image\: cmupro7/\w+:(\d+)', output1[line], re.M | re.I)
                    taggitlist.append(int(tagsko.group(1)))
            taggit = max(taggitlist)
            print("The latest tag in git for %s is %d\n" %(microserv[serv], taggit))
        scanphase = 1
        if(scanphase == 1):
            print("Exeucting Docker bench security scan on tag %s\n" % taggit)
            command3 = "docker pull cmupro7/" + microserv[serv] + ':' + str(taggit)
            stream3 = os.popen(command3)
            output3 = stream3.read()
            output3 = output3.split('\n')
            command4 = "docker images"
            stream4 = os.popen(command4)
            output4 = stream4.read()
            output4 = output4.split('\n')
            if re.match(r'^cmupro7/\w+\s+\d+\s+(\w+)\s+', output4[1], re.M | re.I):
                imageid = re.search(r'cmupro7/\w+\s+\d+\s+(\w+)\s+', output4[1], re.M | re.I)
            logtimestamp =  datetime.now().strftime("%Y%m%d_%H%M%S")
            logfilename = scanloglocation + "/scanlog_" + microserv[serv] + logtimestamp + ".log"
            jsonlogfilename = logfilename + ".json"
            command5 ="sudo /home/ubuntu/docker-bench-security/docker-bench-security.sh -l " + logfilename 
            stream5 = os.popen(command5)
            output5 = stream5.read()
            output5 = output5.split('\n')
            command6 = "docker rmi " + imageid[1]
            stream6 = os.popen(command6)
            print("Docker bench security scans complete, Please review logs at %s /scanlog_%s%s\n" % (scanloglocation, microserv[serv], logtimestamp))
            if Path(jsonlogfilename).is_file():
                print("Checking Scan scores\n")
                with open(jsonlogfilename) as f:
                    for line in f:
                        #line = line.split(',')
                        if re.match(r'^\s+\"score\"\:\s+(\d+)\,', line, re.M | re.I):
                            score = re.search(r'^\s+\"score\"\:\s+(\d+)\,', line, re.M | re.I)
                            if(int(score.group(1)) > scanscorethreshold):
                                print("Scan score %s meets threshold of %d, Moving to upgrade\n" % (int(score.group(1)), scanscorethreshold))
                                summary = [microserv[serv],'upgradephase']
                                upgradephase =1
                            else:
                                print("Scan score %s doesnt meet threshold of %d, Review the scanlogs, Moving to next service\n" % (int(score.group(1)), scanscorethreshold))
                                upgradephase = 0
                                summary = append[microserv[serv],'scanfail']
            else:
                print("Couldnt check scan score,Skipping upgrade, moving to next service\n")
                upgradephase = 0
                summary = [microserv[serv],'scannotdone']
            if(upgradephase == 1):
                command7 = "kubectl argo rollouts set image " + microserv[serv] + " " + microserv[serv] + "=cmupro7/" + microserv[serv] + ":" + str(taggit) + " -n onlineboutique"
                stream7 = os.popen(command7)
                output7 = stream7.read()
                output7 = output7.split('\n')
                if re.match(r'^.*image update', output7[0], re.M | re.I):
                    print('Canary upgrade for %s was successful\n'% microserv[serv])
                    summary = [microserv[serv],'upgradepass']
                else:
                    print('Canary upgrade for %s failed\n'% microserv[serv])
                    summary = [microserv[serv],'upgradefail']
    servsummary.append(summary)

print('##########################################################')
print('Activity Summary')
print('##########################################################\n')
if len(servsummary) == 0:
    print("No new tags were found and hence no services were updated\n")
else:
    for stat in range(len(servsummary)):
        if(servsummary[stat][1] == 'healthy'):
            print("%s: Found healthy, need to investigate why it wasnt upgrade\n" % servsummary[stat][0])
        if(servsummary[stat][1] == 'unhealthy'):
            print("%s: Found unhealthy, Upgrade was skipped\n" % servsummary[stat][0])    
        if(servsummary[stat][1] == 'needscan'):
            print("%s: Needed scan, need to investigate why it wasnt upgrade\n" % servsummary[stat][0])
        if(servsummary[stat][1] == 'equaltag'):
            print("%s: Running latest tags, no further action was needed\n" % servsummary[stat][0])
        if(servsummary[stat][1] == 'impropertag'):
            print("%s: Production tag higher than GIT tag, need to investigate further, Upgrade was skipped\n" % servsummary[stat][0])
        if(servsummary[stat][1] == 'upgradephase'):
            print("%s: Needed an upgrade but wasnt, need to investigate why it wasnt upgrade\n" % servsummary[stat][0])
        if(servsummary[stat][1] == 'scanfail'):
            print("%s: Docker-bench-security scan score didnt meet threshold, Upgrade was skipped, Review scan logs\n" % servsummary[stat][0])
        if(servsummary[stat][1] == 'scannotdone'):
            print("%s: Docker-bench-security scan logs not available, Upgrade was skipped\n" % servsummary[stat][0])  
        if(servsummary[stat][1] == 'upgradepass'):
            print("%s: Canary update was successful, promote when upgrade checks out\n" % servsummary[stat][0])
        if(servsummary[stat][1] == 'upgradefail'):
            print("%s: Canary update failed, Need to investigate why\n" % servsummary[stat][0])

print('##########################################################')
print('Image update wrapped up')
print('##########################################################\n')
