"""Deterministic, local-first CBT-informed activity engine (not a clinical tool)."""
import time
import uuid

ACTIVITIES = {
    "feelings": {"title": "心情气象站", "tag": "表达感受", "steps": [
        {"prompt": "此刻，你的心情像哪种天气？每一种都可以。", "choices": ["晴天 · 舒服", "多云 · 不确定", "下雨 · 难过", "雷雨 · 生气", "我不想说"]},
        {"prompt": "你希望接下来怎么样？", "choices": ["安静待一会", "请大人陪我", "一起慢慢呼吸", "继续玩一会"]},
        {"prompt": "谢谢你告诉我。你可以用说话、图卡或手势表达需要。", "choices": ["我想试试", "我想休息"]}]},
    "breathing": {"title": "云朵充电站", "tag": "调节情绪", "steps": [
        {"prompt": "想跟着云朵慢慢呼吸吗？自然呼吸就好，不需要屏气。", "choices": ["开始跟随云朵", "只看云朵", "选择安静休息"]},
        {"prompt": "按自己的节奏呼吸。觉得不舒服，随时按休息。", "choices": ["我准备好了", "请大人陪我", "我想休息"]},
        {"prompt": "现在身体感觉怎样？没有标准答案。", "choices": ["舒服一些", "差不多", "有些不舒服", "不想回答"]}]},
    "turns": {"title": "轮流小星球", "tag": "社交沟通", "steps": [
        {"prompt": "我们轮流送一颗星星。想让我先，还是你先？", "choices": ["伙伴先来", "我先来", "一起试试看"]},
        {"prompt": "轮到你啦。可以点一下，也可以请大人帮忙。", "choices": ["送出星星", "请帮帮我", "我想休息"]},
        {"prompt": "我们一起完成了一次轮流。下次也可以说：轮到我了吗？", "choices": ["轮到我了吗？", "请再给我一点时间", "谢谢，一起玩吧"]}]},
    "help": {"title": "勇气小桥", "tag": "情境练习", "steps": [
        {"prompt": "故事里，小伙伴正在玩积木，还没有回应。你可能有什么感受？", "choices": ["有点难过", "有点生气", "还不确定", "不想回答"]},
        {"prompt": "我们还不知道原因。你愿意选一种可能吗？", "choices": ["也许他没听见", "也许他想先搭完", "我还不知道", "请大人帮我理解"]},
        {"prompt": "你可以选一句想试着表达的话，也可以用图卡。", "choices": ["我可以一起玩吗？", "你玩好后可以叫我吗？", "我需要帮助", "我想先休息"]}]}
}

class InputError(ValueError):
    pass

class Engine:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.sessions = {}
        self.robot = {"mode": "disconnected", "seen": -1e9}

    def create(self, data):
        if data.get("adult_present") is not True or data.get("consent") is not True:
            raise InputError("请由陪伴成人确认在场，并确认本次活动说明。")
        sid = uuid.uuid4().hex
        s = {"id": sid, "activity": None, "step": 0, "state": "ready", "stars": 0,
             "events": [], "command": None, "revision": 0, "created": self.clock(),
             "settings": {"quiet": bool(data.get("quiet", True)), "reduced_motion": bool(data.get("reduced_motion", True))}}
        self.sessions[sid] = s
        # Bound memory; no files or child identifiers are stored.
        if len(self.sessions) > 100:
            del self.sessions[next(iter(self.sessions))]
        return self.view(s)

    def get(self, sid):
        if sid not in self.sessions:
            raise InputError("本次活动不存在或已清除，请重新开始。")
        return self.sessions[sid]

    def view(self, s):
        a = ACTIVITIES.get(s["activity"])
        step = a["steps"][s["step"]] if a and s["state"] == "playing" else None
        return {k: s[k] for k in ("id", "activity", "step", "state", "stars", "revision", "settings")} | {
            "title": a["title"] if a else "今天，按你的节奏来", "current": step,
            "robot": {"mode": self.robot["mode"], "online": self.clock() - self.robot["seen"] < 1.5},
            "event_count": len(s["events"])}

    def event(self, sid, data):
        s = self.get(sid)
        kind = data.get("type")
        if kind == "stop":
            s["state"] = "stopped"; s["command"] = None
        elif kind == "resume":
            if data.get("adult_confirm") is not True:
                raise InputError("恢复活动需要陪伴成人确认。")
            s["state"] = "ready"; s["activity"] = None; s["command"] = None
        elif kind == "start":
            if s["state"] not in ("ready", "completed"):
                raise InputError("请先完成当前活动，或由成人确认恢复。")
            activity = data.get("activity")
            if activity not in ACTIVITIES:
                raise InputError("未知活动。")
            s.update(activity=activity, step=0, state="playing", command=None)
        elif kind in ("answer", "skip"):
            if s["state"] != "playing":
                raise InputError("当前不在活动中。")
            if data.get("revision") != s["revision"]:
                raise InputError("页面已更新，请按当前步骤继续。")
            choices = ACTIVITIES[s["activity"]]["steps"][s["step"]]["choices"]
            answer = data.get("answer") if kind == "answer" else "跳过"
            if kind == "answer" and answer not in choices:
                raise InputError("请从当前图卡中选择。")
            s["events"].append({"activity": s["activity"], "step": s["step"], "kind": kind, "answer": answer,
                                "elapsed_s": round(self.clock()-s["created"], 1)})
            if answer in ("我想休息", "我想先休息", "选择安静休息", "有些不舒服"):
                s["state"] = "stopped"; s["command"] = None
            else:
                s["step"] += 1
                if s["step"] >= len(ACTIVITIES[s["activity"]]["steps"]):
                    s["state"] = "completed"; s["step"] = 0; s["stars"] += 1
                    # A small optional demonstration cue; child success never depends on robot motion.
                    s["command"] = {"id": uuid.uuid4().hex, "cue": "celebrate", "until": self.clock()+0.6}
        elif kind == "settings":
            s["settings"] = {"quiet": bool(data.get("quiet", True)), "reduced_motion": bool(data.get("reduced_motion", True))}
        else:
            raise InputError("未知操作。")
        s["revision"] += 1
        return self.view(s)

    def report(self, sid):
        s = self.get(sid)
        return {"product": "慢慢星 · 陪伴活动记录", "notice": "仅记录本次活动选择，不是诊断、疗效或能力评分。由成人结合真实情境共同回顾。",
                "completed_activities": s["stars"], "choices": list(s["events"]),
                "reflection": ["孩子主动表达了哪些需要？", "哪些环境或支持让孩子更舒服？", "孩子是否愿意在生活中再试一次？"]}

    def robot_poll(self, sid, mode):
        if mode not in ("turtlesim", "dry-run", "vbot"):
            raise InputError("未知适配器。")
        s = self.get(sid); self.robot = {"mode": mode, "seen": self.clock()}
        c = s["command"]
        active = s["state"] == "completed" and c and self.clock() < c["until"]
        return {"session": sid, "state": s["state"], "command_id": c["id"] if active else None,
                "cue": "celebrate" if active else "idle", "lease_ms": 150 if active else 0,
                "linear_x": 0.0, "angular_z": 0.12 if active else 0.0}
