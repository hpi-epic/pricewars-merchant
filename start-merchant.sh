#!/bin/bash

for folder in /merchant/*; do
    if [ -d "${folder}" ];then
        for file in $folder/*; do
            if [ "${file}" != "${file%.py}" ];then
                echo "Setting merchant token $MERCHANT_TOKEN in $file ...";
                sed -i "s/\{\{API_TOKEN\}\}/$MERCHANT_TOKEN/" $file;
            fi
        done
    fi
done

BASE_FOLDER=`dirname $MERCHANT_FILE`
PYTHON_FILE=`basename $MERCHANT_FILE`

cd BASE_FOLDER && python PYTHON_FILE --port $MERCHANT_PORT
