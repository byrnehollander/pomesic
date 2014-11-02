#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tweepy, time, sys

CONSUMER_KEY = 'fnZy6tdJxlArfWPwVHcGSCdP2'
CONSUMER_SECRET = REDACTED
ACCESS_TOKEN = '2826481127-MxZGiWMGBoWhkC9acHFKPBbbm4aFMczaeWM6ctU'
ACCESS_SECRET = REDACTED
auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)
api = tweepy.API(auth)

# argfile = str(sys.argv[1])
# filename = open(argfile,'r')
# f = filename.readlines()
# filename.close()

# for line in f:
# 	api.update_status(line)
# 	time.sleep(900) #tweet every 15 minutes