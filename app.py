import streamlit as st
import hmac,html
from core import Store,TEAMS,PEOPLE,CRITERIA,export_csv,JUDGE_NAMES
st.set_page_config(page_title='형강생산실 AX 세미나',page_icon='📋',layout='centered')
st.markdown("""<style>.stApp{background:#f2f5fa}.block-container{max-width:740px;padding-top:2rem} .hero{background:linear-gradient(120deg,#082b54,#655f9c 65%,#278a88);padding:26px;border-radius:20px;color:white;margin-bottom:20px}.hero h1{color:white;font-size:30px}.hero p{color:#d7eee9}.stButton button[kind=primary]{background:#167d76;border:0}div[data-testid=stMetric]{background:linear-gradient(135deg,#eef3fc,#e8f5ef);padding:16px;border-radius:12px}</style><div class="hero"><p>형강생산실 · AX SEMINAR</p><h1>모바일 심사실</h1><p>2026년 10월 16일 08:30 · 4.01 회의실</p></div>""",unsafe_allow_html=True)
try:
 cfg=dict(st.secrets);judges=[dict(j) for j in cfg['judges']];store=Store(cfg)
 if len(judges)!=6 or len({j['id'] for j in judges})!=6 or len({j['code'] for j in judges})!=6 or sorted(j['role'] for j in judges)!=sorted(['실장']+TEAMS):raise ValueError('심사위원 설정 오류')
except Exception:
 st.error('배포 설정이 필요합니다. 관리자: Secrets에 PRIVATE_secrets.toml 내용을 입력하세요.');st.stop()
if 'auth' not in st.session_state:st.session_state.auth=None
if 'admin' not in st.session_state:st.session_state.admin=False
mode=st.radio('화면 선택',['심사위원','관리자'],horizontal=True)
if mode=='관리자':
 if not st.session_state.admin:
  with st.form('admin_login'):
   password=st.text_input('관리자 비밀번호',type='password');ok=st.form_submit_button('관리자 입장',type='primary')
  if ok:
   if hmac.compare_digest(password,str(cfg['admin_password'])):st.session_state.admin=True;st.rerun()
   else:st.error('비밀번호를 확인하세요.')
  st.stop()
 st.subheader('관리자 현황')
 if st.button('관리자 로그아웃'):st.session_state.admin=False;st.rerun()
 st.button('현황 새로고침')
 try:rows,_=store.read()
 except Exception as e:st.error(str(e));st.stop()
 st.metric('전체 제출',str(len(rows))+' / 25건')
 st.caption('관리자 화면에는 제출 현황만 표시합니다.')
 for i,p in enumerate(PEOPLE):
  subset=[x for x in rows if x['target']==i]
  with st.container(border=True):
   st.markdown('**'+p+' · '+TEAMS[i]+'**')
   st.write('제출 '+str(len(subset))+' / 5명')
   if len(subset)==5:st.caption('제출 완료')
   elif subset:st.caption('제출 진행 중')
   else:st.caption('제출 대기')
 st.download_button('CSV 내려받기',export_csv(rows),file_name='AX세미나_채점.csv',mime='text/csv',type='primary')
else:
 if st.session_state.auth is None:
  st.subheader('심사위원 입장')
  with st.form('login'):
   name=st.selectbox('성명',list(JUDGE_NAMES.values()),index=None,placeholder='실장님·팀장님 성명을 선택하세요');code=st.text_input('개별 접속코드',type='password');ok=st.form_submit_button('채점 시작',type='primary')
  st.caption('성명·소속·평가 점수는 행사 심사 및 집계를 위해 비공개 저장소에 보관됩니다.')
  if ok:
   judge=next((j for j in judges if hmac.compare_digest(code.strip(),j['code'])),None)
   if not name or judge is None or JUDGE_NAMES[judge['role']]!=name:st.error('선택한 성명과 개별 접속코드가 일치하는지 확인하세요.')
   else:st.session_state.auth={'judge':judge,'name':name.strip()};st.rerun()
  st.stop()
 auth=st.session_state.auth;judge=auth['judge'];st.write('**'+auth['name']+' · '+judge['role']+'**')
 if st.button('나가기'):st.session_state.auth=None;st.rerun()
 st.caption('본인 소속 팀은 자동 제외됩니다. 재제출하면 기존 점수가 수정됩니다.')
 try:allrows,_=store.read()
 except Exception as e:st.error(str(e));st.stop()
 mine=[x for x in allrows if x['judge']==judge['id']];eligible=[i for i in range(5) if TEAMS[i]!=judge['role']]
 st.progress(len(mine)/len(eligible),text='제출 완료 '+str(len(mine))+' / '+str(len(eligible))+'건')
 target=st.selectbox('채점 대상',eligible,format_func=lambda i:PEOPLE[i]+' ('+TEAMS[i]+')')
 existing=next((x for x in mine if x['target']==target),None)
 scores=[]
 for i,(label,maxscore) in enumerate(CRITERIA):
  scores.append(st.number_input(label+' · '+str(maxscore)+'점',min_value=0,max_value=maxscore,value=existing['scores'][i] if existing else None,step=1,key='score_'+judge['id']+'_'+str(target)+'_'+str(i),placeholder='점수를 입력하세요'))
 st.metric('총점',str(sum(v or 0 for v in scores))+' / 100점')
 if st.button('점수 제출 · 기존 점수 수정',type='primary',use_container_width=True):
  if any(v is None for v in scores):st.error('네 항목의 점수를 모두 입력하세요.')
  else:
   try:
    with st.spinner('공동 저장소에 저장 중입니다…'):store.save(judge,auth['name'],target,scores)
    st.session_state.saved=True;st.rerun()
   except Exception as e:st.error(str(e))
 if st.session_state.pop('saved',False):st.success('서버 저장 완료. 관리자 화면에 반영됩니다.')
