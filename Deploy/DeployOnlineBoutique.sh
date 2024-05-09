#!/bin/bash
yourfilenames=`ls manifests/*.yaml`
for eachfile in $yourfilenames
do
   kubectl apply -n onlineboutique -f $eachfile
   sleep 2
done
