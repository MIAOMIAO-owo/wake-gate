#!/usr/bin/env python3
# knock.py —— 叫醒通道骨架：读 state.json，只有「该找」才去叫
# 冷却（防连敲）在这里做，别放到叫醒通道里 —— 通道可能被别的东西也调用。
import json, os, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LAST = os.path.join(HERE, '.last_knock')


def main():
    cfgp = os.path.join(HERE, 'criteria.json')
    if not os.path.exists(cfgp):
        cfgp = os.path.join(HERE, 'criteria.example.json')
    cfg = json.load(open(cfgp, encoding='utf-8'))
    stp = os.path.join(HERE, cfg.get('state_path', 'state.json'))
    if not os.path.exists(stp):
        print('没有 state.json：先跑 judge.py')
        return
    st = json.load(open(stp, encoding='utf-8'))
    if not st.get('should_wake'):
        print('不叫：' + st.get('reason', ''))
        return
    cool = int(cfg.get('cooldown_minutes', 30)) * 60
    if os.path.exists(LAST):
        age = time.time() - float(open(LAST).read().strip() or 0)
        if age < cool:
            print('冷却中：%.0f 分钟前刚叫过' % (age / 60))
            return
    body = json.dumps({'why': st.get('reason', ''), 'state': st}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(cfg.get('knock_url'), data=body,
                                 headers={'Content-Type': 'application/json; charset=utf-8'})
    retry = cfg.get('retry') or {'times': 4, 'gap_seconds': 6}
    for i in range(int(retry['times'])):
        try:
            urllib.request.urlopen(req, timeout=6).read()
            open(LAST, 'w').write(str(time.time()))
            print('叫醒了：' + st.get('reason', ''))
            return
        except Exception as e:
            # 常见：通道在但会话还没挂上（返回 503）—— 等几秒重试
            print('第 %d 次没投出去：%s' % (i + 1, str(e)[:80]))
            time.sleep(float(retry['gap_seconds']))
    print('放弃：通道一直投不出去')


if __name__ == '__main__':
    main()
