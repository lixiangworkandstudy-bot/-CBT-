"""Local, deterministic activity prototype. Screen feedback; no robot motion."""
import copy
import time
import uuid


def option(label, next_node=None, feedback='谢谢你告诉我。', symbol='✦'):
    return {'label': label, 'next': next_node, 'feedback': feedback, 'symbol': symbol}


def node(prompt, choices, illustration='listen', turn='一起选择', practice=None):
    return dict(prompt=prompt, choices=choices, illustration=illustration, turn=turn, practice=practice)


COMFORT = [option('安静待一会', 'quiet', '好，我们先安静待一会。', '☁'),
           option('请大人陪我', 'adult', '请身边的大人陪你，等你准备好。', '♡'),
           option('试试慢慢呼吸', 'breathe', '可以自然呼吸，不需要屏气，也不用跟上动画。', '〰')]
CHECK = node('现在感觉怎样？每一种都可以。', [option('舒服一些', feedback='谢谢你告诉我现在的感受。', symbol='☀'), option('差不多', feedback='没有变化也可以。', symbol='☁'), option('换一种方法', 'choose', '好，我们换一种方法。', '↺'), option('我想休息', 'REST', '好，我们停下来。', 'Ⅱ')])
SUPPORT = {
 'choose': node('想试哪一种方法？', COMFORT + [option('我想休息', 'REST', '好，我们停下来。', 'Ⅱ')]),
 'quiet': node('可以安静待着，没有倒计时。准备好后再选择。', [option('我准备好了', 'check', '谢谢你告诉我。'), option('换一种方法', 'choose', '好，我们重新选。', '↺'), option('我想休息', 'REST', '好，我们停下来。', 'Ⅱ')], practice='quiet'),
 'adult': node('请陪伴成人回应孩子的需要。孩子可以继续等，也可以结束。', [option('我们准备好了', 'check', '好，按你们的节奏来。', '♡'), option('换一种方法', 'choose', '可以换一个方法。', '↺'), option('我想休息', 'REST', '好，我们停下来。', 'Ⅱ')], turn='等待成人陪伴'),
 'breathe': node('如果愿意，可以自然地慢慢呼吸。不要屏气；不用跟上图形。', [option('我准备好了', 'check', '好，我们看看现在的感受。'), option('换一种方法', 'choose', '可以不做呼吸练习。', '↺'), option('有些不舒服', 'REST', '先停下来，请大人陪伴。', 'Ⅱ')], 'breathe', practice='breathing'),
 'check': CHECK,
}
ACTIVITIES = {
 'feelings': {'title':'心情气象站','tag':'表达感受','start':'mood','nodes': {
   **copy.deepcopy(SUPPORT),
   'mood': node('此刻心情像什么？可以选，也可以不说。', [option(x,'choose',f'你选了“{x}”。每一种感受都可以。',s) for x,s in [('晴天 · 舒服','☀'),('多云 · 不确定','☁'),('下雨 · 难过','☂'),('雷雨 · 生气','ϟ')]] + [option('我不想说','choose','可以不说，我们看看你现在需要什么。','…')]),
 }},
 'breathing': {'title':'云朵充电站','tag':'寻找舒服的方法','start':'choose','nodes':copy.deepcopy(SUPPORT)},
 'turns': {'title':'轮流小星球','tag':'轮流与等待','start':'order','nodes':{
   'order': node('这一次，想让谁先送星星？',[option('慢慢先来','partner_first','好，先看慢慢送星星。','✦'),option('我先来','child_first','好，先轮到你。','☆'),option('先看示范','demo','可以先看看。','◉')]),
   'demo': node('示范：慢慢送一颗星星，然后停下来等你。你可以点“送出星星”。',[option('我想试试','order','好，你来选谁先。'),option('我想休息','REST','好，我们停下来。','Ⅱ')], 'welcome','示范 · 网页演示', 'star'),
   'partner_first': node('慢慢送出了一颗星星。准备好后，可以轮到你。',[option('轮到我了','child_last','慢慢会等你。','☆'),option('再看一次','partner_first','再看一次慢慢送星星。','↺')], 'welcome','慢慢的回合 · 网页演示','star'),
   'child_first': node('轮到你送星星。可以点按钮，也可以由成人协助。',[option('送出星星','partner_last','收到你的星星了！现在轮到慢慢。','☆'),option('请帮帮我','assist_first','请大人协助表达，准备好再送出。','♡')],turn='你的回合'),
   'child_last': node('轮到你送星星。慢慢在等你，不用着急。',[option('送出星星','end','收到你的星星了！我们各送了一颗。','☆'),option('请帮帮我','assist_last','请大人协助，准备好再送出。','♡')],turn='你的回合'),
   'assist_first': node('请成人帮助孩子选择或表达。',[option('一起送出星星','partner_last','收到星星了！现在轮到慢慢。','☆')],turn='等待成人协助'),
   'assist_last': node('请成人帮助孩子选择或表达。',[option('一起送出星星','end','收到星星了！我们各送了一颗。','☆')],turn='等待成人协助'),
   'partner_last': node('现在轮到慢慢。慢慢送出一颗星星，再停下来。',[option('我看到了','end','我们各送了一颗星星。','✦'),option('再看一次','partner_last','好，再演示一次。','↺')],'welcome','慢慢的回合 · 网页演示','star'),
   'end': node('还想再轮流一次吗？',[option('再玩一次','order','好，重新选择顺序。','↺'),option('这次结束',feedback='谢谢你和慢慢一起玩。')]),
 }},
 'help': {'title':'勇气小桥','tag':'表达需要','start':'story','nodes':{
   'story': node('故事里，小伙伴在搭积木，还没有回应你。你可能有什么感受？',[option(x,'reason', '谢谢你告诉我。') for x in ['有点难过','有点生气','还不确定','不想回答']]),
   'reason': node('我们还不知道原因。你愿意选一种可能吗？',[option(x,'request','这是一种可能，我们还不能确定。') for x in ['也许他没听见','也许他想先搭完']] + [option('我还不知道','request','不知道也可以。'),option('请大人帮我理解','story_help','先请身边的大人一起看这个故事。','♡')]),
   'story_help': node('请成人一起理解情境，不需要替孩子选一个正确答案。',[option('我们准备好了','request','好，再看看你想表达什么。')],turn='等待成人协助'),
   'request': node('现在，你想怎样表达自己的需要？',[option('我可以一起玩吗？','practice','你可以用说话、图卡或手势表达。'),option('你玩好后可以叫我吗？','practice','可以把这句话告诉身边的大人试试。'),option('我需要帮助','help_adult','请身边的大人回应你的求助。','♡'),option('我想先休息','REST','好，我们先停下来。','Ⅱ')]),
   'help_adult': node('请成人回应孩子需要的帮助。准备好再选择。',[option('我们一起试试','practice','好，可以用你舒服的方式表达。'),option('这次结束',feedback='谢谢你表达需要。')],turn='等待成人协助'),
   'practice': node('可以和成人试着表达刚才的需要。不想练习也可以。',[option('我试过了',feedback='谢谢你尝试表达。'),option('这次先不试',feedback='可以按自己的节奏决定。'),option('我需要帮助','help_adult','我们请成人一起帮忙。','♡')]),
 }},
}

class InputError(ValueError):
    pass

class Engine:
    def __init__(self, clock=time.monotonic):
        self.clock=clock; self.sessions={}; self.robot={'mode':'disconnected','seen':-1e9}
    def create(self,data):
        if data.get('adult_present') is not True or data.get('consent') is not True:
            raise InputError('请由陪伴成人完成两项确认。')
        sid=uuid.uuid4().hex
        self.sessions[sid]={'id':sid,'activity':None,'node':None,'state':'ready','step':0,'stars':0,'revision':0,'events':[],'created':self.clock(),'settings':{'quiet':bool(data.get('quiet',True)),'reduced_motion':bool(data.get('reduced_motion',True))},'feedback':None,'next':None,'command':None,'skipped':False,'robot':{'mode':'disconnected','seen':-1e9}}
        if len(self.sessions)>100: del self.sessions[next(iter(self.sessions))]
        return self.view(self.sessions[sid])
    def get(self,sid):
        if sid not in self.sessions: raise InputError('本次活动不存在或已清除，请重新开始。')
        return self.sessions[sid]
    def view(self,s):
        a=ACTIVITIES.get(s['activity']); current=None
        if a and s['state']=='playing':
            current=copy.deepcopy(a['nodes'][s['node']])
            current['choices']=[{'label':o['label'],'symbol':o['symbol']} for o in current['choices']]
        return {k:copy.deepcopy(s[k]) for k in ['id','activity','state','step','stars','revision','settings','feedback','skipped']} | {'title':a['title'] if a else '陪伴小屋','current':current,'robot':{'mode':s['robot']['mode'],'online':self.clock()-s['robot']['seen']<1.5},'event_count':len(s['events'])}
    def event(self,sid,data):
        s=self.get(sid); kind=data.get('type')
        if kind=='stop': s.update(state='stopped',command=None,feedback=None,next=None)
        elif kind=='resume':
            if data.get('adult_confirm') is not True: raise InputError('请由陪伴成人确认恢复。')
            s.update(state='ready',activity=None,node=None,feedback=None,next=None,command=None)
        elif kind=='settings':
            s['settings']={'quiet':bool(data.get('quiet',True)),'reduced_motion':bool(data.get('reduced_motion',True))}
        elif kind=='start':
            if s['state'] not in ('ready','completed'): raise InputError('请先结束当前活动。')
            a=data.get('activity')
            if a not in ACTIVITIES: raise InputError('未知活动。')
            s.update(activity=a,node=ACTIVITIES[a]['start'],state='playing',step=0,feedback=None,next=None,command=None,skipped=False)
        elif kind in ('answer','skip','continue','repeat'):
            if data.get('revision')!=s['revision']: raise InputError('页面已更新，请重新查看当前步骤。')
            if kind=='continue':
                if s['state']!='feedback': raise InputError('当前没有待继续的回应。')
                dest=s['next']; s.update(feedback=None,next=None)
                if dest is None: s.update(state='completed',stars=s['stars']+(0 if s['skipped'] else 1))
                else: s.update(state='playing',node=dest,step=s['step']+1)
            else:
                if s['state']!='playing': raise InputError('当前不在选择步骤中。')
                n=ACTIVITIES[s['activity']]['nodes'][s['node']]
                if kind=='repeat':
                    # Repeat is screen-only, never a robot command.
                    s['events'].append({'activity':s['activity'],'step':s['step'],'node':s['node'],'kind':'repeat','answer':'再看一次','input_method':'页面操作','elapsed_s':round(self.clock()-s['created'],1)})
                else:
                    if kind=='skip':
                        s['skipped']=True
                        o=option('跳过并结束本次活动',feedback='可以跳过，随时再来。')
                    else:
                        o=next((x for x in n['choices'] if x['label']==data.get('answer')),None)
                        if o is None: raise InputError('请从当前图卡中选择。')
                    method=data.get('input_method','自己点击')
                    if method not in ('自己点击','图卡 · 成人代选','手势 · 成人代选','成人协助'): raise InputError('未知参与方式。')
                    s['events'].append({'activity':s['activity'],'step':s['step'],'node':s['node'],'kind':kind,'answer':o['label'],'input_method':method,'feedback':o['feedback'],'feedback_mode':'网页演示','elapsed_s':round(self.clock()-s['created'],1)})
                    if o['next']=='REST': s.update(state='stopped',feedback=None,next=None,command=None)
                    else: s.update(state='feedback',feedback=o['feedback'],next=o['next'])
        else: raise InputError('未知操作。')
        if kind=='stop': s['events'].append({'activity':s['activity'],'step':s['step'],'kind':'stop','answer':'我想休息','input_method':'页面操作','elapsed_s':round(self.clock()-s['created'],1)})
        s['revision']+=1
        return self.view(s)
    def report(self,sid):
        s=self.get(sid)
        return {'product':'慢慢星 · 陪伴活动记录','notice':'仅记录本次过程，不是诊断、疗效或能力评分。','completed_activities':s['stars'],'choices':copy.deepcopy(s['events']),'reflection':['孩子表达了哪些需要？','哪些支持让孩子更舒服？','孩子是否想再试一次？']}
    def robot_poll(self,sid,mode):
        if mode not in ('turtlesim','dry-run','vbot'): raise InputError('未知适配器。')
        s=self.get(sid); s['robot']={'mode':mode,'seen':self.clock()}
        return {'session':sid,'state':s['state'],'command_id':None,'cue':'idle','lease_ms':0,'linear_x':0.0,'angular_z':0.0}
