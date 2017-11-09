#__author__ = 'Administrator'
# -*- coding: utf-8 -*-
import urllib
import urllib2
import json


sendData = {}
sendData['method'] = "cutWords"
sendData['sentence'] = "2017年3月，国务院总理李克强调研上海外高桥时提出，支持上海积极探索新机制。"
#sendData['sentence'] = "2002——2004年，章子怡连续出演了张艺谋导演的武侠电影《英雄》和《十面埋伏》，与李连杰，梁朝伟，张曼玉，刘德华，金城武等华人演员同台演绎。"

# words = cut_words('国务院总理李克强调研上海外高桥时提出，支持上海积极探索新机制。')

message = json.dumps(sendData).decode().encode('utf8')
response = urllib2.urlopen('http://192.168.1.6:10001/',message)
data = response.read()
# print type(response
jdata = json.loads(data,encoding="utf8")   #jdata即为获取的json数据
wordsList = jdata['wordsList']
for w in wordsList:
    print w

print '------------'

send = {}
send['method'] = "postTag"
send['wordsList'] = wordsList

message = json.dumps(send).decode().encode('utf8')
response = urllib2.urlopen('http://192.168.1.6:10001/',message)
data = response.read()
# print type(response
jdata = json.loads(data,encoding="utf8")   #jdata即为获取的json数据
posTags = jdata['postags']
for w in posTags:
    print w

print '------------'

send = {}
send['method'] = "ner"
send['postags'] = posTags
send['wordsList'] = wordsList

message = json.dumps(send).decode().encode('utf8')
response = urllib2.urlopen('http://192.168.1.6:10001/',message)
data = response.read()
# print type(response
jdata = json.loads(data,encoding="utf8")   #jdata即为获取的json数据
netags = jdata['netags']
for w in netags:
    print w
