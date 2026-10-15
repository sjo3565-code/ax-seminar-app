import base64,json,time,random,csv,io
from datetime import datetime,timezone
import requests
TEAMS=['중형압연팀','대형제강팀','봉형강압연설계팀','대형압연팀','중형제강팀']
PEOPLE=['홍정원','이광원','최태호','신종열','김용진']
JUDGE_NAMES={'실장': '윤혜성', '중형제강팀': '김진섭', '중형압연팀': '김태형', '대형제강팀': '구자덕', '대형압연팀': '전상규', '봉형강압연설계팀': '배병철'}
CRITERIA=[('실용성',30),('난이도 대비 효과',40),('확산 가능성',20),('발표·전달력',10)]
def validate(role,target,scores):
 if type(target)!=int or target not in range(5) or TEAMS[target]==role:raise ValueError('본인 팀은 채점할 수 없습니다.')
 if len(scores)!=4 or any(type(v)!=int or not 0<=v<=m for v,(_,m) in zip(scores,CRITERIA)):raise ValueError('항목별 배점 범위 내 정수를 입력하세요.')
 return sum(scores)
class Store:
 def __init__(self,cfg):
  self.url='https://api.github.com/repos/'+cfg['data_repo']+'/contents/scores.json'
  self.branch=cfg.get('branch','main')
  self.headers={'Authorization':'Bearer '+cfg['github_token'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
 def read(self):
  res=requests.get(self.url,params={'ref':self.branch},headers=self.headers,timeout=20)
  if res.status_code==404:raise RuntimeError('점수 저장소 또는 scores.json을 찾지 못했습니다. 저장소·토큰 설정을 확인하세요.')
  if res.status_code!=200:raise RuntimeError('저장소 조회 실패 (HTTP '+str(res.status_code)+'). 관리자에게 문의하세요.')
  obj=res.json();data=json.loads(base64.b64decode(obj['content']))
  if not isinstance(data,list):raise RuntimeError('점수 파일 형식 오류')
  for row in data:
   if row.get('role') in JUDGE_NAMES:row['name']=JUDGE_NAMES[row['role']]
  return data,obj['sha']
 def save(self,judge,name,target,scores):
  total=validate(judge['role'],target,scores)
  if not name.strip() or len(name)>30:raise ValueError('성명을 확인하세요.')
  record={'judge':judge['id'],'name':JUDGE_NAMES[judge['role']],'role':judge['role'],'target':target,'scores':scores,'total':total,'updated':datetime.now(timezone.utc).isoformat()}
  for attempt in range(7):
   rows,sha=self.read();rows=[x for x in rows if not(x['judge']==judge['id'] and x['target']==target)]+[record]
   payload={'message':'Update seminar score','branch':self.branch,'sha':sha,'content':base64.b64encode(json.dumps(rows,ensure_ascii=False).encode()).decode()}
   res=requests.put(self.url,json=payload,headers=self.headers,timeout=25)
   if res.status_code in (200,201):return
   if res.status_code in (409,422):time.sleep(.4+random.random()*(attempt+1));continue
   raise RuntimeError('점수 저장 실패 (HTTP '+str(res.status_code)+'). 다시 제출하거나 관리자에게 문의하세요.')
  raise RuntimeError('동시 제출이 많습니다. 잠시 후 다시 제출하세요.')
def export_csv(rows):
 out=io.StringIO(newline='');writer=csv.writer(out)
 writer.writerow(['심사위원','소속','발표자','발표팀',*[x[0] for x in CRITERIA],'총점','제출시각(UTC)'])
 for x in sorted(rows,key=lambda x:(x['target'],x['judge'])):
  values=[x['name'],x['role'],PEOPLE[x['target']],TEAMS[x['target']],*x['scores'],x['total'],x['updated']]
  writer.writerow(["'"+v if isinstance(v,str) and v.startswith(('=','+','-','@','\t','\r','\n')) else v for v in values])
 return out.getvalue().encode('utf-8-sig')
