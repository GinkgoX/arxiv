# -*- coding: utf-8 -*-
import requests
import re
import time
import pandas as pd
from bs4 import BeautifulSoup
import pymysql
from collections import Counter
import os
import random

import smtplib
from smtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header


def get_one_page(url):
    response = requests.get(url)
    print(response.status_code) 
    while response.status_code == 403:
        time.sleep(500 + random.uniform(0, 500))
        response = requests.get(url)
        print(response.status_code)
    print(response.status_code)
    if response.status_code == 200:
        return response.text

    return None


def send_email(title, content):
    #sender's email
    sender = 'username@163.com'
    #sender's email and password(SMTP key)
    user = 'usernameA@163.com'
    # password = 'KSTEAIBLHBIAMAPD'#dailyarxiv123
    password = 'userA_password_for_163_email'
    #sender's SMTP address
    smtpserver = 'smtp.163.com'
    #receiver email
    receiver = 'email_you_want_to_send' 
    msg = MIMEMultipart('alternative')  
    part1 = MIMEText(content, 'plain', 'utf-8')  

    msg.attach(part1)  

    #sender
    msg['From'] = sender
    #receiver
    msg['To'] = receiver
    #title
    msg['Subject'] = title
    
    #start smtp sever
    smtp = smtplib.SMTP()
    smtp.connect(smtpserver) 
    smtp.login(user, password)
    smtp.sendmail(sender, receiver, msg.as_string())
    smtp.quit()
    smtp.close()

#get all result
def get_all(url='https://arxiv.org/list/cs/pastweek?show=1000', save_path='arxiv/daily/'):
    html = get_one_page(url)
    soup = BeautifulSoup(html, features='html.parser')
    content = soup.dl
    date = soup.find('h3')
    list_ids = content.find_all('a', title = 'Abstract')
    list_title = content.find_all('div', class_ = 'list-title mathjax')
    list_authors = content.find_all('div', class_ = 'list-authors')
    list_subjects = content.find_all('div', class_ = 'list-subjects')
    list_subject_split = []
    for subjects in list_subjects:
        subjects = subjects.text.split(': ', maxsplit=1)[1]
        subjects = subjects.replace('\n\n', '')
        subjects = subjects.replace('\n', '')
        subject_split = subjects.split('; ')
        list_subject_split.append(subject_split)
    items = []
    for i, paper in enumerate(zip(list_ids, list_title, list_authors, list_subjects, list_subject_split)):
        items.append([paper[0].text, paper[1].text, paper[2].text, paper[3].text, paper[4]])
    name = ['id', 'title', 'authors', 'subjects', 'subject_split']
    paper = pd.DataFrame(columns=name,data=items)
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    paper.to_csv(save_path+time.strftime("%Y-%m-%d")+'_'+str(len(items))+'.csv')
    subject_all = []
    for subject_split in list_subject_split:
        for subject in subject_split:
            subject_all.append(subject)
    subject_cnt = Counter(subject_all)
    return list_title, subject_cnt, items, paper 

#split with keywords(multi-keywords)
def split_keywords(paper, key_words=['Detection'], save_path='arxiv/selected/'):
    # key_words2 = ['quantization', 'compress', 'prun']
    selected_papers = paper[paper['title'].str.contains(key_words[0], case=False)]
    for key_word in key_words[1:]:
        selected_paper1 = paper[paper['title'].str.contains(key_word, case=True)]
        selected_papers = pd.concat([selected_papers, selected_paper1], axis=0)
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    selected_papers.to_csv(save_path+time.strftime("%Y-%m-%d")+'_'+str(len(selected_papers))+'.csv')
    return selected_papers

#download parper
def download_parper(save_path, selected_papers):
    '''dowdload key_word selected papers'''
    list_subject_split = []
    if not os.path.exists(save_path+time.strftime("%Y-%m-%d")):
        os.makedirs(save_path+time.strftime("%Y-%m-%d"))
    for selected_paper_id, selected_paper_title in zip(selected_papers['id'], selected_papers['title']):
        selected_paper_id = selected_paper_id.split(':', maxsplit=1)[1]
        selected_paper_title = selected_paper_title.split(':', maxsplit=1)[1]
        r = requests.get('https://arxiv.org/pdf/' + selected_paper_id) 
        while r.status_code == 403:
            time.sleep(500 + random.uniform(0, 500))
            r = requests.get('https://arxiv.org/pdf/' + selected_paper_id)
        selected_paper_id = selected_paper_id.replace(".", "_")
        pdfname = selected_paper_title.replace("/", "_")
        pdfname = pdfname.replace("?", "_")
        pdfname = pdfname.replace("\"", "_")
        pdfname = pdfname.replace("*","_")
        pdfname = pdfname.replace(":","_")
        pdfname = pdfname.replace("\n","")
        pdfname = pdfname.replace("\r","")
        print(save_path+time.strftime("%Y-%m-%d")+'/%s %s.pdf'%(selected_paper_id, selected_paper_title))
        with open(save_path+time.strftime("%Y-%m-%d")+'/%s %s.pdf'%(selected_paper_id,pdfname), "wb") as code:    
           code.write(r.content)

#send email
def send_parper(list_title, subject_cnt, items, selected_papers):
    '''send email'''
    #selected_papers.to_html('email.html')
    content = 'Today arxiv has {} new papers in CS area, and {} of them is about CV, {} of them contain your keywords.\n\n'.format(len(list_title), subject_cnt['Computer Vision and Pattern Recognition (cs.CV)'], len(selected_papers))
    # content += 'Ensure your keywords is ' + str(key_words) + ' and ' + str(Key_words) + '(case=True). \n\n'
    content += 'This is your paperlist.Enjoy! \n\n'
    for i, selected_paper in enumerate(zip(selected_papers['id'], selected_papers['title'], selected_papers['authors'], selected_papers['subject_split'])):
        #print(content1)
        content1, content2, content3, content4 = selected_paper
        content += '------------' + str(i+1) + '------------\n' + content1 + content2 + str(content4) + '\n'
        content1 = content1.split(':', maxsplit=1)[1]
        content += 'https://arxiv.org/abs/' + content1 + '\n\n'

    content += 'Here is the Research Direction Distribution Report. \n\n'
    subject_items = []
    for subject_name, times in subject_cnt.items():
        subject_items.append([subject_name, times])
    subject_items = sorted(subject_items, key=lambda subject_items: subject_items[1], reverse=True)
    name = ['name', 'times']
    subject_file = pd.DataFrame(columns=name,data=subject_items)
    sub_path = 'arxiv/sub_cnt/'
    if not os.path.exists(sub_path):
        os.makedirs(sub_path)
    subject_file.to_csv(sub_path+time.strftime("%Y-%m-%d")+'_'+str(len(items))+'.csv')
    for subject_name, times in subject_items:
        content += subject_name + '   ' + str(times) +'\n'
    title = time.strftime("%Y-%m-%d") + ' you have {} papers'.format(len(selected_papers))
    return title, content

#write log
def write_report(save_path='arxiv/report/', content):
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    freport = open(save_path +'.txt', 'w')
    freport.write(content)
    freport.close()


def main():

    url = 'https://arxiv.org/list/cs/pastweek?show=1000'
    save_all_path = 'arxiv/daily/'

    list_title, subject_cnt, items, paper = get_all(url,save_all_path)
    print(paper.head())
    print("*" * 20)

    key_words = ['Object Detection', 'Detector']
    save_split_path = 'arxiv/selected/'
    selected_papers = split_keywords(paper, key_words, save_split_path)
    print(selected_papers.head())

    #download_parper(save_split_path, selected_papers)

    title, content = send_parper(list_title, subject_cnt, items, selected_papers)

    send_email(title , content)
    
    save_log_path = 'arxiv/report/'
    write_report(save_log_path, content)

    time.sleep(5)

if __name__ == '__main__':
    main()
    
