#__author__ = 'Administrator'
# -*- coding: utf-8 -*-
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from os import curdir, sep
import cgi, logging, time
from SocketServer import ThreadingMixIn
import json
import pyltp
from pyltp import SentenceSplitter,Segmentor,Postagger,NamedEntityRecognizer,Parser,SementicRoleLabeller
import jieba

global segmentor, postagger, recognizer
segmentor = Segmentor()
postagger = Postagger()
recognizer = NamedEntityRecognizer()
# parser = Parser()
# labeller = SementicRoleLabeller()

def loadModel():
    segmentor.load('ltp_data/cws.model')
    postagger.load('ltp_data/pos.model')
    recognizer.load('ltp_data/ner.model')
    # self.parser.load('ltp_data/parser.model')
    # self.labeller.load('ltp_data/srl')
    print '***** Models load Success *****'

def sentence_splitter(text):
    sents = SentenceSplitter.split(text)  # 分句
    return sents
# 分词
def cut_words(sentence):
    # segmentor = Segmentor()  # 初始化实例
    # segmentor.load('../ltp_data/cws.model')  # 加载模型
    if isinstance(sentence,unicode):
        sentence = sentence.encode("utf8")
    wordsList = jieba.cut(sentence,cut_all=False)
    # wordsList = segmentor.segment(sentence)  # 分词 
    # print '\t'.join(words)
    # segmentor.release()  # 释放模型
    words_list = []
    for word in wordsList:
        if isinstance(word,unicode):
    	    word = word.encode("utf8")
            words_list.append(word)
    return words_list

# 词性标注
def post_tagger(wordsList):
    # postagger = Postagger() # 初始化实例
    # postagger.load('../ltp_data/pos.model')  # 加载模型
    for index in range(len(wordsList)):
        if isinstance(wordsList[index],unicode):
            wordsList[index] = wordsList[index].encode("utf8")

    postags = postagger.postag(wordsList)  # 词性标注
    # postagger.release()  # 释放模型
    return [x for x in postags]

# 命名实体识别
def ner(wordsList,postags):
    # recognizer = NamedEntityRecognizer() # 初始化实例
    # recognizer.load('../ltp_data/ner.model')  # 加载模型
    for index in range(len(wordsList)):
        if isinstance(wordsList[index],unicode):
            wordsList[index] = wordsList[index].encode("utf8")
    for index in range(len(postags)):
        if isinstance(postags[index],unicode):
            postags[index] = postags[index].encode("utf8")

    netags = recognizer.recognize(wordsList, postags)  # 命名实体识别
    # recognizer.release()  # 释放模型
    return [x for x in netags]

# 依存句法分析
def parse(wordsList, postags):
    # parser = Parser() # 初始化实例
    # parser.load('../ltp_data/parser.model')  # 加载模型
    for index in range(len(wordsList)):
        if isinstance(wordsList[index],unicode):
            wordsList[index] = wordsList[index].encode("utf8")
    for index in range(len(postags)):
        if isinstance(postags[index],unicode):
            postags[index] = postags[index].encode("utf8")
            
    arcs = parser.parse(wordsList, postags)  # 句法分析
    # parser.release()  # 释放模型
    return [x for x in arcs]

# 语义角色标注
def role_label(wordsList, postags, netags, arcs):
    # labeller = SementicRoleLabeller() # 初始化实例
    # labeller.load('../ltp_data/srl')  # 加载模型
    roles = labeller.label(wordsList, postags, netags, arcs)  # 语义角色标注
    # labeller.release()  # 释放模型
    return [x for x in roles]


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
        response = {}

        method = jdata['method']

        if method == "cutWords":
            sentence = jdata["sentence"]
            wordsList = cut_words(sentence)
            response['wordsList'] = wordsList

        elif method == "postTag":
            wordsList = jdata['wordsList']
            postags = post_tagger(wordsList)
            response['postags'] = postags

        elif method == "ner":
            wordsList = jdata['wordsList']
            postags = jdata['postags']
            netags = ner(wordsList, postags)
            response['netags'] = netags
        else:
            pass

        # 以下是返回json的内容

        message = json.dumps(response,ensure_ascii=False)

        self.wfile.write(message)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""
    pass

if __name__ == '__main__':
    loadModel()
    server = ThreadedHTTPServer(('192.168.1.6', 10001), Handler)
    server.serve_forever()
