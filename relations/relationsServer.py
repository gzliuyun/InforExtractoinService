#__author__ = 'Administrator'
# -*- coding: utf-8 -*-
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from os import curdir, sep
import cgi, logging, time
from SocketServer import ThreadingMixIn
import json
import gensim
import numpy as np
from keras.models import Sequential, load_model
from keras.layers import Embedding

word2vec = {}
int2relation = {}
cnn_position_dict = {}

timestep = 80    #每条语料设定的最大长度
embedding_length = 100   #embedding的维度
rnn_step = 20     #rnn部分的单词数   4*5, 最多4个人名,每个人名包括前后共5个词
window = 3  # cnn滑动窗口大小
cnn_winWord_length = window * embedding_length
cnn_pos_length = 10   #位置表的embedding长度
cnn_length = cnn_winWord_length + 2 * cnn_pos_length

#位置标签（<e1></e1><e2></e2>）下标对应的embedding
#rnn_position_tag_embedding = []
#rnn_position_tag =['<e1>','</e1>','<e2>','</e2>']

def initData():
    global word2vec, int2relation, final_model
    # 加载词向量
    print '******词向量加载中******'
    word2vec = gensim.models.Word2Vec.load('word2vec/wiki.zh.text.model')
    print '******词向量加载结束****'
    # 加载训练好的深度学习模型
    final_model =  load_model('model/final_model.h5')
    # 关系关系对应的标号
    int2relation = {
    	0 : '夫妻',
    	1 : '父母子女',
    	2 : '师徒',
    	3 : '合作',
    	4 : '朋友',
    	5 : '兄弟',
    	6 : '恋人'
    }
    # 利用keras的embedding功能将位置标签<e1>,</e1>,<e2>,</e2>用embedding_length维的embedding表示
    global rnn_position_tag_embedding   #标签列表中位置下标对应标签的embedding表示
    model = Sequential()
    model.add(Embedding(4,embedding_length,input_length=1))
    model.compile('rmsprop','mse')
    tag_array = np.array([0,1,2,3])
    rnn_position_tag_embedding = model.predict(tag_array)

    print '***** Data init success *****'

# 获取item 单词对应的embedding  
def word2embedding(item):
    if not isinstance(item,unicode):
        item = unicode(item,'utf-8')
    if item in word2vec:
        rlist = np.array(map(float, word2vec[item]))
        return rlist
    # 如果 item 不在训练好的model词汇中,则随机出一个embedding
    else:
        rlist = map(float, list( 4 * np.random.rand(embedding_length) - 2 ))   #-2到2之间
        return np.array(rlist)

def sentence2list(wordsList,name1,name2):
    words = wordsList
    words_list = []
    index = 0
    while (index < len(words)):
        word = words[index]
        if word == name1 or word == name2:
            words_list.append(word)
            index += 1
            continue

        # 连续的分词组合起来是不是等于name1
        copy_index = index
        find = False
        while name1.find(word) == 0:
            if name1 == word:
                words_list.append(name1)
                find = True
                break
            copy_index += 1
            if copy_index >= len(words):
                break
            word += words[copy_index]
        if find:
            index = copy_index +1
            continue
        # 连续的分词组合起来是不是等于name2
        word = words[index]
        copy_index = index
        while name2.find(word) == 0:
            if name2 == word:
                words_list.append(name2)
                find = True
                break
            copy_index += 1
            if copy_index >= len(words):
                break
            word += words[copy_index]
        if find:
            index = copy_index + 1
            continue

        word = words[index]
        words_list.append(word)
        index += 1
    return words_list

def rnnDataEmbedding(wordsList,name1,name2):
    rnnEmbed = np.empty((rnn_step,embedding_length),dtype="float64")
    length = len(wordsList)

    def addRnnEmbed(label,index):
        if index - 2 >= 0:
            rnnEmbed[label] = word2embedding(wordsList[index-2])
            label += 1
        else:
            rnnEmbed[label] = np.array([0] * embedding_length)
            label += 1

        ##########################
        if index - 1 >= 0:
            rnnEmbed[label] = word2embedding(wordsList[index-1])
            label += 1
        else:
            rnnEmbed[label] = np.array([0] * embedding_length)
            label += 1

        ##########################
        rnnEmbed[label] = word2embedding(wordsList[index])
        label += 1

        ##########################
        if index + 1 < length:
            rnnEmbed[label] = word2embedding(wordsList[index+1])
            label += 1
        else:
            rnnEmbed[label] = np.array([0] * embedding_length)
            label += 1

        ##########################
        if index + 2 < length:
            rnnEmbed[label] = word2embedding(wordsList[index+2])
            label += 1
        else:
            rnnEmbed[label] = np.array([0] * embedding_length)
            label += 1
        return label

    label = 0
    for index in range(length):
        word = wordsList[index]
        if word == name1 or word == name2:
            label = addRnnEmbed(label,index)
            if label >= rnn_step: break
    while(label < rnn_step):
        rnnEmbed[label] = np.array([0] * embedding_length)
        label += 1

    return rnnEmbed

def cnnDataEmbedding(wordsList,name1,name2):
    length = len(wordsList)
    posName1 = []
    posName2 = []
    for i in range(length):
        if wordsList[i] == name1:
            posName1.append(i)
        elif wordsList[i] == name2:
            posName2.append(i)

    def lmrEmd(i):
        ebd = []
        if (i - 1)>= 0:
            wordEbd = word2embedding(wordsList[i-1])
            ebd.extend(list(wordEbd))
        else:
            ebd.extend(list(np.array([0] * embedding_length)))

        wordEbd = word2embedding(wordsList[i])
        ebd.extend(list(wordEbd))

        if (i + 1) < length:
            wordEbd = word2embedding(wordsList[i+1])
            ebd.extend(list(wordEbd))
        else:
            ebd.extend(list(np.array([0] * embedding_length)))

        return ebd

    # 最近距离计算
    def minDistence(index):
        # 计算与name1最近距离
        i = 0
        while i < len(posName1):
            if posName1[i] > index:
                break
            i += 1
        if i == len(posName1):
            if i == 0:  pos1 = timestep  #句子中没发现name1的异常情况
            else:   pos1 = index - posName1[i-1]
        elif (i - 1 >= 0):
            if abs(index - posName1[i-1]) <= abs(posName1[i] - index):
                pos1 = index - posName1[i-1]
            else:
                pos1 = index - posName1[i]
        else:
            pos1 = index - posName1[i]

        # 计算与name2最近距离
        i = 0
        while i < len(posName2):
            if posName2[i] > index:
                break
            i += 1
        if i == len(posName2):
            if i == 0:  pos2 = timestep  #句子中没发现name2的异常情况
            else:   pos2 = index - posName2[i-1]
        elif (i - 1 >= 0):
            if abs(index - posName2[i-1]) <= abs(posName2[i] - index):
                pos2 = index - posName2[i-1]
            else:
                pos2 = index - posName2[i]
        else:
            pos2 = index - posName2[i]

        return pos1, pos2

    cnnEbd = np.empty((timestep,cnn_length),dtype="float64")

    idx = 0
    for idx in range(length):
        if idx >= timestep:
            break
        ebd = []
        ebd.extend(lmrEmd(idx))

        #找离index最近的name1，计算差值
        global cnn_position_dict
        pos1, pos2 = minDistence(idx)
        if not cnn_position_dict.has_key(pos1):
            cnn_position_dict[pos1] = list( 4 * np.random.rand(cnn_pos_length) - 2 )
        if not cnn_position_dict.has_key(pos2):
            cnn_position_dict[pos2] = list( 4 * np.random.rand(cnn_pos_length) - 2)
        ebd.extend(cnn_position_dict[pos1])
        ebd.extend(cnn_position_dict[pos2])

        cnnEbd[idx] = np.array(ebd)
    while idx < timestep:
        ebd = [0] * cnn_length
        cnnEbd[idx] = np.array(ebd)
        idx += 1

    return cnnEbd

class Handler(BaseHTTPRequestHandler):

    def _writeheaders(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()


    def do_POST(self):

        self._writeheaders()

        length = self.headers.getheader('content-length');
        nbytes = int(length)
        # print nbytes
        data = self.rfile.read(nbytes)
        # self.send_response(200)

        jdata = json.loads(data,encoding="utf8")    #jdata即为json 数据，可以类似操纵字典进行操作，如dateList = jdata.keys()
    
        wordsList =  jdata["wordsList"]
        name1 = jdata["name1"]
        name2 = jdata["name2"]
        wordsList = sentence2list(wordsList,name1,name2)

        rnn_data = np.empty((1,rnn_step,embedding_length),dtype="float64")
        cnn_data = np.empty((1,timestep,cnn_length),dtype="float64")

        rnn_data[0] = rnnDataEmbedding(wordsList,name1,name2)
        cnn_data[0] = cnnDataEmbedding(wordsList,name1,name2)
        
	test_classes = final_model.predict_classes([rnn_data,cnn_data])
	cls = test_classes[0]
        print cls 

	response = {}
        response["relation"] = int2relation[cls]
        message = json.dumps(response,ensure_ascii=False)

        self.wfile.write(message)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    pass

if __name__ == '__main__':
    initData();
    server = ThreadedHTTPServer(('192.168.1.6', 10002), Handler)
    server.serve_forever()
