#!/usr/bin/env python3
# judge.py —— 判断层骨架（纯本地计算，不调模型）
# 读 criteria.json → 写 state.json（给醒来的 AI 读，几行长而已）
# 你要接的只有 gather()：对方多久没说话／人在不在，从你的客户端或账本里来。
import json, os, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))


def load_criteria():
    p = os.path.join(HERE, 'criteria.json')
    if not os.path.exists(p):
        p = os.path.join(HERE, 'criteria.example.json')
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def flag(cfg, key):
    p = os.path.join(HERE, cfg.get(key) or '')
    return bool(cfg.get(key)) and os.path.exists(p)


def in_quiet_hours(cfg, now=None):
    qh = cfg.get('quiet_hours') or {}
    a, b = qh.get('from'), qh.get('to')
    if not a or not b:
        return False
    now = now or datetime.datetime.now()
    cur = now.strftime('%H:%M')
    return (a <= cur or cur < b) if a > b else (a <= cur < b)


def gather():
    """TODO：换成你自己的数据来源。这里只给结构。"""
    return {
        'minutes_since_last_message': None,   # 分钟。None = 未知
        'idle_seconds': None,                 # 秒。None = 未知
    }


def decide(cfg, env):
    """返回 (该不该找, 理由)。顺序＝优先级。"""
    if cfg.get('exception_argue') and flag(cfg, 'argue_flag_path'):
        return True, '例外：争吵/危机模式，力压全部限制'
    if flag(cfg, 'sleep_flag_path'):
        return False, '对方睡着：不弹不响'
    if in_quiet_hours(cfg):
        return False, '静默时段'
    mins = env.get('minutes_since_last_message')
    if mins is None:
        return True, '读不到对话时间：宁可叫醒（首次运行常见）'
    threshold = int(cfg.get('silence_minutes', 15))
    if mins >= int(cfg.get('wake_bonus_after_hours', 8)) * 60:
        threshold = max(1, threshold // 3)   # 睡了很久还没动静：阀值放宽
    if mins < threshold:
        return False, '对方 %d 分钟前刚说过话（阀值 %d）' % (mins, threshold)
    idle = env.get('idle_seconds')
    aw = int(cfg.get('active_window_minutes', 10)) * 60
    if idle is not None and idle > aw:
        return False, '人可能不在：键鼠已闲置 %d 分钟' % (idle // 60)
    return True, '对方 %d 分钟没说话，且人在' % mins


def main():
    cfg = load_criteria()
    env = gather()
    should, why = decide(cfg, env)
    state = {
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'should_wake': should,
        'reason': why,
        'env': {
            'minutes_since_last_message': env.get('minutes_since_last_message'),
            'idle_seconds': env.get('idle_seconds'),
            'is_asleep': flag(cfg, 'sleep_flag_path'),
            'is_arguing': flag(cfg, 'argue_flag_path'),
        },
        'action': cfg.get('action', 'wake'),
        'dry_run': bool(cfg.get('dry_run')),
    }
    out = os.path.join(HERE, cfg.get('state_path', 'state.json'))
    text = json.dumps(state, ensure_ascii=False, indent=2)
    limit = int(cfg.get('state_max_bytes', 4096))
    if len(text.encode('utf-8')) > limit:
        state.pop('env', None)
        text = json.dumps(state, ensure_ascii=False, indent=2)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(text)
    print(('该找' if should else '不找') + '：' + why + ' -> ' + out)


if __name__ == '__main__':
    main()
