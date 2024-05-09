#!/usr/bin/python3

import copy
import os
import sys
import datetime
import re
from datetime import datetime

tagfilelocation = "/home/ubuntu/imageupdater"
tagfile = "tagfile"
knowntagfile = "knowntags.txt"
scanlogslocation = "/home/ubuntu/imageupdater/scanlogs"
# Define the format of the datetime strings
datetime_format = "%Y-%m-%d %H:%M:%S"
#microserv = ['adservice', 'checkoutservice', 'productcatalogservice', 'emailservice', 'cartservice', 'frontend', 'currencyservice', 'shippingservice', 'recommendationservice', 'paymentservice', 'loadgenerator']
microserv = ['shippingservice']

#Make a list of current tags of the microservices running
print('\n###############################################################')
print('Reading current tagfile and making a list of tags in production')
print('###############################################################')
production_tags = []
with open(os.path.join(tagfilelocation,tagfile)) as f:
    for line in f:
        line = line.split(',')
        production_tags.append(line)
        
print('\n###############################################################')
print('Making list of knowntags to compare with images in docker hub')
print('###############################################################')
known_tags = []
with open(os.path.join(tagfilelocation,knowntagfile)) as f:
    for line in f:
        line = line.split(',')
        known_tags.append(line)

upgradelist = []
updatedtaglist = []
nowknown_tags = copy.deepcopy(known_tags)

for service in range(len(microserv)):
    tag_list = []
    servtags = []
    deltatags = []
    foundtag = []
    prodservtag = ''
    prodservts = ''
    foundflag = 0
    tagcount = 1
    print('\n##########################################################')
    print('Checking %s' % microserv[service])
    print('##########################################################')
    #Find the current tag and timestamp for the microservice
    for tags in range(len(production_tags)):
        if production_tags[tags][0] == microserv[service]:
            prodservtag = production_tags[tags][1]
            prodservts = production_tags[tags][2]
            prodservts = datetime.strptime(prodservts, datetime_format)

    #Load the known tags for this service
    for ktags in range(len(nowknown_tags)):
        if nowknown_tags[ktags][0] == microserv[service]:
            nowknown_tags[ktags].pop(0)
            nowknown_tags[ktags].pop()
            servtags = nowknown_tags[ktags]

    #Capture all the tags for each microservice
    command = 'skopeo list-tags --creds cmupro7:grp5pro7cmu@1234 docker://cmupro7/' + microserv[service]
    stream = os.popen(command)
    output = stream.read() 
    output = output.split('\n')
    #Create a list of the tags
    for line in range(len(output)):
        if re.match(r'^\s+\"\d+\"(\,)?', output[line], re.M | re.I):
            tag = re.search(r'^\s+\"(\d+)\"(\,)?', output[line], re.M | re.I)
            foundtag.append(tag.group(1))
    #compare foundtags and new tags to find delta
    deltatags = [x for x in foundtag if x not in servtags]
    
    if(len(deltatags)>0):
        print('Found %d new tags\n' % len(deltatags))
        print('Looking for the latest tag\n')
        newtimestamp = prodservts
        newtag = prodservtag
        #From delta tags find the latest tag, first find timestamp of current production tag
        for dtags in range(len(deltatags)):
            command2 = 'skopeo inspect --creds cmupro7:grp5pro7cmu@1234 docker://cmupro7/' + microserv[service] + ':' + deltatags[dtags] + ' |grep Created'
            #print(command2)
            stream1 = os.popen(command2)
            output1 = stream1.read()
            output1 = output1.split('\n')
            if re.match(r'^\s+\"Created\"\: \"\d+\-\d+\-\d+T\d+\:\d+\:\d+\.\d+Z', output1[0], re.M | re.I):
                temptimestamp = re.search(r'^\s+\"Created\"\: \"(\d+\-\d+\-\d+)T(\d+\:\d+\:\d+)\.\d+Z', output1[0], re.M | re.I)
                temptimestamp = temptimestamp[1] + " " + temptimestamp[2]
                foundtimestamp = datetime.strptime(temptimestamp, datetime_format)
                #print("##%s" % foundtimestamp)
                if foundtimestamp > newtimestamp:
                    newtimestamp = foundtimestamp
                    newtag = deltatags[dtags]
        print("Latest tag is %s with timestamp %s\n" % (newtag, newtimestamp))
        print("Exeucting Docker bench security scan on tag %s\n"% newtag)
        command3 = "docker pull cmupro7/" + microserv[service] + ':' + deltatags[dtags]
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
        command5 ="sudo /home/ubuntu/docker-bench-security/docker-bench-security.sh -l /home/ubuntu/imageupdater/scanlogs/scanlog_" + microserv[service] + logtimestamp + ".log"
        stream5 = os.popen(command5)
        output5 = stream5.read()
        output5 = output5.split('\n')
        command6 = "docker rmi " + imageid[1]
        stream6 = os.popen(command6)
        print("Docker bench security scans complete, Please review logs at /home/ubuntu/scanlogs/scanlog_%s%s\n" % (microserv[service], logtimestamp))
        print("Performing Canary Upgrade for %s\n" % microserv[service])
        command7 = "kubectl argo rollouts set image rollouts-demo rollouts-demo=argoproj/" + microserv[service] + ":" + deltatags[dtags]
        stream7 = os.popen(command7)
        output7 = stream7.read()
        output7 = output7.split('\n')
        if re.match(r'^.*image update', output7[0], re.M | re.I):
            print('%s was upgraded successfully'% microserv[service])
            upgradelist.append([microserv[service], newtag, newtimestamp])
            #print(foundtag)
            foundtag.insert(0,microserv[service])
            updatedtaglist.append(foundtag)
        else:
            print('%s upgrade failed'% microserv[service])
            upgradelist.append([microserv[service], newtag, newtimestamp])
            #print(foundtag)
            #foundtag.insert(0,microserv[service])
            #updatedtaglist.append(foundtag)
            #print(updatedtaglist)
            #foundflag = 1
    else:
        print("No new tags found for %s" % microserv[service])

#Update tagfile
if len(upgradelist) > 0:
    #Before upgrading archive the currrent tagfile
    print('\n##########################################################')
    print('Archiving current tagfile')
    print('##########################################################')
    archivecommand = 'sudo mv tagfile /home/ubuntu/imageupdater/archive/tagfile_' + datetime.now().strftime("%Y%m%d_%H%M%S")
    archivestream = os.popen(archivecommand)
    archiveoutput = archivestream.read()
    #print(archiveoutput)
    #Update the services which have been modified
    for newtags in range(len(upgradelist)):
        for oldtags in range(len(production_tags)):
            if upgradelist[newtags][0] == production_tags[oldtags][0]:
                if upgradelist[newtags][1] != production_tags[oldtags][1]:
                    production_tags[oldtags][1] = upgradelist[newtags][1]
                    production_tags[oldtags][2] = upgradelist[newtags][2]
    print('\n##########################################################')
    print('Creating new tagfile')
    print('##########################################################')
    tagfilehandle = open("tagfile", "w")
    for i in range(len(production_tags)):
        tagfilehandle.write("%s,%s,%s,%s"%(production_tags[i][0],production_tags[i][1],production_tags[i][2],production_tags[i][3]))
    tagfilehandle.close()
else:
    print('\n##########################################################')
    print('Tagfile doesnt need to change as no services were upgraded')
    print('##########################################################')

#Update knowntagfile
if len(updatedtaglist) > 0:
    #Before updating archive the current knowntagfile
    print('\n##########################################################')
    print('Archiving the current knowntagfile')
    print('##########################################################')
    archivecommand = 'sudo mv knowntags.txt /home/ubuntu/imageupdater/archive/knwontag_' + datetime.now().strftime("%Y%m%d_%H%M%S")
    archivestream = os.popen(archivecommand)
    archiveoutput = archivestream.read()

    #Update the services which have been successfully upgraded
    for olddata in range(len(known_tags)):
        #print(known_tags[olddata][0])
        for newdata in range(len(updatedtaglist)):
            #print(updatedtaglist[newdata][0])
            if known_tags[olddata][0] == updatedtaglist[newdata][0]:
                known_tags[olddata] = updatedtaglist[newdata]
                known_tags[olddata].append('\n')
    print('\n##########################################################')
    print('Creating new knowntagfile')
    print('##########################################################')
    tagfilehandle = open("knowntags.txt", "w")
    for i in range(len(known_tags)):
        for j in range(len(known_tags[i])):
            if j == len(known_tags[i]) - 1 :
                tagfilehandle.write("%s"% known_tags[i][j])
            else:
                tagfilehandle.write("%s,"% known_tags[i][j])
    tagfilehandle.close()
else:
    print('\n###############################################################')
    print('KnownTagfile doesnt need to change as no services were upgraded')
    print('############################################################')


print('\n##########################################################')
print('Image Updater done')
print('\n##########################################################')

