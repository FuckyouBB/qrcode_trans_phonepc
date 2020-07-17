from tkinter import *
import tkinter.filedialog
import time
import socket
import os
import shutil
import threading
import zipfile,re
from urllib.parse import quote

import windnd
import qrcode
from biplist import *
from flask import Flask,make_response,send_from_directory,request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)
tk = Tk()
label_img = None

plist_tpl = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>items</key>
    <array>
        <dict>
            <key>assets</key>
            <array>
                <dict>
                    <key>kind</key>
                    <string>software-package</string>
                    <key>url</key>
                    <string>https://$ip:5051/$file_path</string>
                </dict>
                <dict>
                    <key>kind</key>
                    <string>display-image</string>
                    <key>url</key>
                    <string>https://example.com/image.57x57.png</string>
                </dict>
                <dict>
                    <key>kind</key>
                    <string>full-size-image</string>
                    <key>url</key>
                    <string>https://example.com/image.512x512.png</string>
                </dict>
            </array>
            <key>metadata</key>
            <dict>
                <key>bundle-identifier</key>
                <string>$bundleid</string>
                <key>bundle-version</key>
                <string>$version</string>
                <key>kind</key>
                <string>software</string>
                <key>title</key>
                <string>$name</string>
            </dict>
        </dict>
    </array>
</dict>
</plist>'''


def get_host_ip(): 
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

def dragged_files(files):
    msg = '\n'.join((item.decode('gbk') for item in files))
    #showinfo('file::',msg)
    gen_qrcode(msg)

def show_upload():
    global label_img
    if not os.path.exists('img'):
        os.mkdir('img')
    if not os.path.exists('img/upload.gif'):
        img = qrcode.make("http://{}:5050/upload_pic".format(get_host_ip()))
        img.save('img/upload.gif')
    pl = PhotoImage(file='img/upload.gif')
    tk_show_img(pl)
    
def file_open():
    r = tkinter.filedialog.askopenfilename(title='上传文件',
                                           filetypes=[ ('All files', '*')])
    gen_qrcode(r)

def show_img_dir():
    if not os.path.exists('img'):
        os.mkdir('img')
    os.system('start img')

def tk_show_img(img):
    global label_img
    if not label_img:
        label_img = Label(tk,image = img,width=450,height=450)
        label_img.image = img
        label_img.place(x=25,y=40)
        tk.update_idletasks()
    else:
        label_img.configure(image = img)
        label_img.image = img
        tk.update_idletasks()

def gen_qrcode(path):
    global label_img
    if not os.path.exists('img'):
        os.mkdir('img')
    if not os.path.exists('download'):
        os.mkdir('download')
    if path[-3:] == 'ipa':
        img = gen_ios_img(path)
    else:
        img = gen_anr_img(path)
    tk_show_img(img)
    

def gen_anr_img(path):
    ts = str(int(time.time()*1000))
    filepath = 'download/'+ts+'.'+path.split('.')[-1]
    shutil.copy(path,filepath)
    img = qrcode.make("http://{}:5050/".format(get_host_ip())+filepath)
    img_path = 'img/'+ts+'.gif'
    img.save(img_path)
    return PhotoImage(file=img_path)

def gen_ios_img(path):
    ts = str(int(time.time()*1000))
    filepath = 'download/'+ts+'.'+path.split('.')[-1]
    shutil.copy(path,filepath)
    ip = get_host_ip()
    gen_plist(filepath,ts,ip)
    url = 'itms-services://?action=download-manifest&url=https://{}:5051/download/{}.plist'.format(ip,ts)
    img = qrcode.make(url)
    img_path = 'img/'+ts+'.gif'
    img.save(img_path)
    return PhotoImage(file=img_path)

def gen_plist(ios_file,ts,ip):
    content = plist_tpl
    info = get_ios_data(ios_file)
    content = content.replace('$ip',ip).replace('$file_path',ios_file).replace('$name',info[0]).replace('$bundleid',info[1]).replace('$version',info[2])
    with open('download/{}.plist'.format(ts),'w') as wf:
        wf.write(content)


def get_ios_info_path(ipaobj):
    infopath_re = re.compile(r'.*.app/Info.plist')
    for i in ipaobj.namelist():
        m = infopath_re.match(i)
        if m is not None:
            return m.group()

def get_ios_data(ios_file):
    if zipfile.is_zipfile(ios_file):
        ipaobj = zipfile.ZipFile(ios_file)
        info_path = get_ios_info_path(ipaobj)
        if info_path:
            plist_data = ipaobj.read(info_path)
            plist_root = readPlistFromString(plist_data)
            if 'CFBundleDisplayName' in plist_root.keys():
                labelname = plist_root['CFBundleDisplayName']
            else:
                labelname = plist_root['CFBundleName']
            versioncode = plist_root['CFBundleVersion']
            bundle_id = plist_root['CFBundleIdentifier']
            return labelname, bundle_id, versioncode

def main():
    tk.title('文件二维码生成器')
    tk.geometry('500x500')
    b = Button(tk, text='打开文件',  command=file_open)
    b.place(x=110,y=0)
    b1 = Button(tk, text='手机上传图片',  command=show_upload)
    b1.place(x=180,y=0)
    b2 = Button(tk, text='打开图片目录',  command=show_img_dir)
    b2.place(x=275,y=0)
    windnd.hook_dropfiles(tk,func=dragged_files)
    tk.mainloop()

@app.route("/", methods=['GET'])
def hello_world():
    return 'hello world'

@app.route("/upload_pic", methods=['GET'])
def upload_pic():
    html = '''<!DOCTYPE html>
                <html>
                    <head>
                    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
                    <title>移动端上传图片</title>
                    <style type="text/css">
                    .file {
                        position: relative;
                        display: inline-block;
                        background: #D0EEFF;
                        border: 1px solid #99D3F5;
                        border-radius: 4px;
                        padding: 4px 12px;
                        overflow: hidden;
                        color: #1E88C7;
                        text-decoration: none;
                        text-indent: 0;
                        text-indent: 0;
                        line-height: 125px;
                        width:420px;
                        height:120px;
                        font-size:90px
                    }
                    .file input {
                        position: absolute;
                        font-size: 100px;
                        right: 0;
                        top: 0;
                        opacity: 0;
                    }
                    .file:hover {
                        background: #AADFFD;
                        border-color: #78C3F3;
                        color: #004974;
                        text-decoration: none;
                    }
                    </style>
                    </head>
                    <body style="text-align:center;margin-top:100px">
                        <a href="javascript:;" class="file" >上传图片
                            <input accept="image/*,video/*" type="file" onchange="handleFileSelect(event)" />   
                        </a>
                    </body>
                    <script type="text/javascript">
                        function handleFileSelect(event) {
                            var fileObj = event.target.files[0];
                            var formData = new FormData();
                            formData.append('file', fileObj);
                            var ajax = new XMLHttpRequest();
                            ajax.open("POST", "http://$ip:5050/upload", true);
                            ajax.send(formData);
                        }
                    </script>
                </html>'''
    html = html.replace('$ip',get_host_ip())
    return html

@app.route("/upload", methods=['POST'])
def upload_file():
    if not os.path.exists('img'):
        os.mkdir('img')
    f = request.files['file']
    path = 'img/手机截图'+str(int(time.time()))+'.'+ f.filename.split('.')[-1]
    f.save(path)
    return 'success'

@app.route("/download/<filename>", methods=['GET'])
def download_file(filename):
    response = make_response(send_from_directory('./download', filename, as_attachment=True))
    response.headers["Content-Disposition"] = "attachment; filename={}".format(quote(filename))
    return response

def flaskk():
    app.run(host='0.0.0.0',port= 5051,ssl_context='adhoc')

def flask():
    app.run(host='0.0.0.0',port= 5050)

if __name__ == '__main__':
    t = threading.Thread(target=flaskk,args=())
    t1 = threading.Thread(target=flask,args=())
    t.setDaemon(True)
    t.start()
    t1.setDaemon(True)
    t1.start()
    main()