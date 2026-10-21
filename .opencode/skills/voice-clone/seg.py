import json,subprocess,sys,os
PY=os.environ['LOCALAPPDATA']+r'\Temp\opencode\omnivoice-venv\Scripts\python.exe'
OUT=os.environ['OUT']
segs=json.load(open('segs.json',encoding='utf-8'))
for i,(name,txt) in enumerate(segs,1):
    out=os.path.join(OUT,f"vo{i:02d}.wav")
    if os.path.exists(out) and os.path.getsize(out)>10000: print("SKIP",name); continue
    r=subprocess.run([PY,'clone.py',txt,'--out',out],capture_output=True,text=True,encoding='utf-8',errors='replace')
    line=[l for l in r.stdout.splitlines() if 'ความยาว' in l or 'ใช้เวลา' in l]
    print(f"[{i}] {name}: {' | '.join(line)}")
