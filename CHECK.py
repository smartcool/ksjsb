#!/usr/bin/python3
# -*- coding: utf8 -*-
"""
#（必填）填写要监控的GitHub仓库的 “用户名/仓库名/仓库分支/脚本关键词” 监控多个仓库请用 & 隔开
export GitRepoHost="KingRan/KR/main/opencard&feverrun/my_scripts/main/opencard&smiek2121/scripts/master/opencard&okyyds/yyds/master/lzdz1"
#（可选）Github Token变量，将api请求次数提升到5000次/小时，默认60次/小时
export GitToken="GithubToken"
#（可选）http代理，针对国内机使用，访问不了github的可以填上，支持用户名密码
export GitProxy="http://username:password@127.0.0.1:8080"
#（可选）运行开卡脚本前禁用开卡脚本定时任务，不填则不禁用，保留原有定时
export opencardDisable="true"
#（可选）任务参数，格式和青龙的 conc、desi 一样的用法，请自行参考
export opencardParam="desi JD_COOKIE 1 3-10"
#（可选）检测重复任务相似度阈值，值为数字，不使用变量则不检测重复任务（变量不能为空，不使用请注释变量）
#       值过小：两个不同的开卡脚本识别为同一个，值过大：两个相同开卡脚本识别为两个不同脚本
export opencardSimi="50"

cron: */5 0-3 * * *
new Env('开卡更新检测')
"""

from time import sleep
from notify import send
import requests,json,os,re,difflib

print("软件版本：8.5.1")

# 显示日志
def log(content):
    print(content)
    List.append(content)

# 获取青龙登录Token
def GetQLToken():
    path = '/ql/config/auth.json'
    if not os.path.exists(path):
        path = '/ql/data/config/auth.json'
    try:
        with open(path,"r",encoding="utf-8") as file:
            auth = json.load(file)
    except Exception:
        print(f"无法获取青龙登录token！！！")
    return auth.get("token")

# 获取青龙版本
def GetQLVersion():
    url = qlHost+"/system"
    rsp = session.get(url=url,headers=headers)
    jsons=rsp.json()
    if rsp.status_code == 200:
        if jsons.get("data").get("version"):
            print("青龙版本："+jsons["data"]["version"])
            v = jsons["data"]["version"].split(".")
            if int(v[0])<=2 and int(v[1])>=13: # 大于等于2.13.0，小于3.0.0
                version = {"path":"/ql/data","api":"/subscriptions","id":"id"}
            elif int(v[0])<=2 and int(v[1])>=12: # 大于等于2.12.0，小于2.13.0
                version = {"path":"/ql/data","api":"/crons","id":"id"}
            elif int(v[0])<=2 and int(v[1])>=11: # 大于等于2.11.0 小于2.12.0
                version = {"path":"/ql","api":"/crons","id":"id"}
            elif int(v[0])<=2 and int(v[1])>=10 and int(v[2])>=3: # 大于等于2.10.3 小于2.11.0
                version = {"path":"/ql","api":"/crons","id":"_id"}
        else:
            version = {"path":"/ql","api":"/crons","id":"_id"}
        return version
    else:
        print(f'请求青龙失败：{url}')
        print(f'错误信息：{rsp.json().get("message")}')
        return False

def qlCron(name):
    url = qlHost+"/crons?searchValue="+name
    rsp = session.get(url=url, headers=headers)
    jsons = rsp.json()
    if rsp.status_code == 200:
        if jsons.get("data"):
            log("获取任务成功："+jsons["data"][0]["name"])
            return jsons.get("data")
        else:
            log(f"没有找到任务：{name}")
            return False,False
    else:
        log(f'请求青龙失败：{url}')
        log(f'错误信息：{jsons.get("message")}')
        return False,False

def qlSub():
    url = qlHost+version.get("api")
    rsp = session.get(url=url, headers=headers)
    jsons = rsp.json()
    if rsp.status_code == 200:
        if jsons.get("data"):
            for x in jsons["data"]:
                if GitRepo in x.get("url"):
                    log("获取任务成功："+x.get("name"))
                    return x.get("name"),[x.get(version["id"])]
        else:
            log(f"没有找到任务：{GitRepo}")
            return False,False
    else:
        log(f'请求青龙失败：{url}')
        log(f'错误信息：{jsons.get("message")}')
        return False,False

def qlRepo(scriptsName):
    repopath = path+"/scripts/"+Repo[0]+"_"+Repo[1]
    if not os.path.exists(repopath):
        repopath = path+"/scripts/"+Repo[0]+"_"+Repo[1]+"_"+Repo[2]
    if version.get("api")=="/subscriptions":
        RepoName,RepoID = qlSub()
    else:
        rr = qlCron(GitRepo)
        RepoName = rr[0]["name"]
        RepoID = [rr[0][version["id"]]]
    if not RepoName and not RepoID:
        log(f"获取仓库任务信息失败：{GitRepo}")
        return
    url = qlHost+version.get("api")+"/run"
    rsp = session.put(url=url,headers=headers,data=json.dumps(RepoID))
    if rsp.status_code == 200:
        log(f"运行拉库任务：{RepoName}")
        ii=0
        while not os.path.exists(repopath+"/"+scriptsName):
            if ii>60:
                log("找不到文件："+repopath+"/"+scriptsName)
                return
            sleep(5)
            ii+=1
        else:
            sleep(5)
            return True
    else:
        log(f'请求青龙失败：{url}')
        if "message" in rsp.json():
            log(f'错误信息：{rsp.json()["message"]}')
        return

def qlTask(scriptsName):
    TaskName = False
    ii = 0
    while not TaskName:
        if ii>12:
            log(f"获取开卡任务信息失败：{scriptsName}")
            return
        sleep(5)
        ii+=1
        tt = qlCron(scriptsName)
        TaskName = tt[0]["name"]
        TaskID = [tt[0][version["id"]]]
    if 'opencardDisable' in os.environ:
        if os.environ['opencardDisable']=="true":
            url = qlHost+"/crons/disable"
            rsp = session.put(url=url,headers=headers,data=json.dumps(TaskID))
            if rsp.status_code == 200:
                log(f"禁用开卡任务：{TaskName}")
            else:
                log(f'请求青龙失败：{url}')
                log(f'错误信息：{rsp.json().get("message")}')
                return
    if 'opencardParam' in os.environ and "desi" not in tt[0]["command"]:
        url = qlHost+"/crons"
        body = {
            "command": tt[0]["command"]+" "+os.environ["opencardParam"],
            "schedule": tt[0]["schedule"],
            "name": TaskName,
            version["id"]: tt[0][version["id"]]
        }
        rsp = session.put(url=url,headers=headers,data=json.dumps(body))
        if rsp.status_code == 200:
            log("成功更改命令："+rsp.json().get("data").get("command"))
    with open('./nameCron.json',"r",encoding='UTF-8') as f:
        TaskStr = json.load(f)
    if "opencardSimi" in os.environ:
        taskname=qlCronEqual(TaskName,TaskStr)
        if not taskname:
            return
    # 运行开卡任务
    url = qlHost+"/crons/run"
    rsp = session.put(url=url,headers=headers,data=json.dumps(TaskID))
    if rsp.status_code == 200:
        log(f"运行开卡任务：{TaskName}")
        if "opencardSimi" in os.environ:
            if Repo[0] not in TaskStr:
                TaskStr[Repo[0]]=[]
            if taskname not in TaskStr[Repo[0]]:
                TaskStr[Repo[0]].append(taskname)
                with open(f"./nameCron.json","w",encoding='UTF-8') as f:
                    json.dump(TaskStr,f)
                    # log(f"保存任务名到nameCron.json文件")
    else:
        log(f'请求青龙失败：{url}')
        if "message" in rsp.json():
            log(f'错误信息：{rsp.json()["message"]}')

# 检查重复任务
def qlCronEqual(TaskName,TaskStr):
    task = re.split(' |,|，',TaskName)[::-1]
    taskname = task[0]
    if len(taskname)==0:
        taskname = task[1]
    for i in TaskStr:
        for x in TaskStr[i]:
            point = round(difflib.SequenceMatcher(None,taskname,x).quick_ratio()*100)
            if point>=int(os.environ["opencardSimi"]):
                log(f"任务名高度相似：{TaskName}/{x}={point}%")
                log("放弃运行任务："+TaskName)
                if Repo[0] not in TaskStr:
                    TaskStr[Repo[0]]=[]
                if taskname not in TaskStr[Repo[0]]:
                    TaskStr[Repo[0]].append(taskname)
                    with open(f"./nameCron.json","w",encoding='UTF-8') as f:
                        json.dump(TaskStr,f)
                        # log(f"保存任务名到nameCron.json文件")
                return False
    return taskname

# 获取开卡脚本目录树
def GetOpenCardTree():
    log(f"\n监控仓库：https://github.com/{GitRepo}")
    gitapi = f'https://api.github.com/repos/{GitRepo}/git/trees/{GitBranch}'
    rsp = session.get(url=gitapi,headers=githeader,proxies=proxies)
    if rsp.status_code == 200:
        tree = []
        for x in rsp.json()["tree"]:
            if Repo[3] in x["path"]:
                tree.append(x["path"])
        return tree
    else:
        log(f'请求失败：{gitapi}')
        log(f'错误信息：{rsp.json().get("message")}')
        return "false"

def CheckChange():
    state = False

    with open(f"./nameScripts.json", 'rb') as file:
        scriptsJson = json.load(file)
        if Repo[0] not in scriptsJson:
            scriptsJson[Repo[0]]=tree
            with open('./nameScripts.json',"w") as f:
                json.dump(scriptsJson,f)
            # log("nameScripts.json中未找到KEY："+Repo[0])

    sn = True
    for scriptsName in tree:
        if scriptsName not in scriptsJson[Repo[0]]:
            log(f"新增开卡脚本：{scriptsName}")
            if sn:
                repoPull = qlRepo(scriptsName)
            if repoPull:
                qlTask(scriptsName)
                sn==False
            state = True
    else:
        log("没有新增开卡脚本")
    
    if state:
        with open(f"./nameScripts.json","w") as f:
            scriptsJson[Repo[0]]=tree
            json.dump(scriptsJson,f)
            # log(f"保存文件名到nameScripts.json文件")
        
    return state

if 'GitRepoHost' in os.environ:
    RepoHost = os.environ['GitRepoHost'].split("&")
    session = requests.session()
    qlHost = 'http://127.0.0.1:5700/api'
    qlToken = GetQLToken()
    githeader = {"Content-Type":"application/json"}
    headers = {"Content-Type":"application/json","Authorization":"Bearer "+qlToken}
    version = GetQLVersion()
    path = version["path"]
    if 'GitToken' in os.environ:
        githeader["Authorization"]="Bearer "+os.environ['GitToken']
        print("已设置Github Token")
    proxies = {}
    if 'GitProxy' in os.environ:
        proxies['https'] = os.environ['GitProxy']
        print("已设置HTTP代理，将通过代理访问api.github.com")
    if not os.path.exists(f"./nameScripts.json"):
        with open(f"./nameScripts.json","w") as f:
            json.dump({},f)
        print(f"没有找到nameScripts.json文件！将自动生成")
    if not os.path.exists(f"./nameCron.json"):
        with open(f"./nameCron.json","w") as f:
            json.dump({},f)
        print(f"没有找到nameCron.json文件！将自动生成")
    if path:
        for RepoX in RepoHost:
            List=[]
            Repo = RepoX.split("/")
            GitRepo = Repo[0]+"/"+Repo[1]
            GitBranch = Repo[2]
            tree = GetOpenCardTree()
            if tree != "false":
                state = CheckChange()
                tt = '\n'.join(List)
                if state:
                    send('开卡更新检测', tt)
else:
    print("请查看脚本注释后设置相关变量")
