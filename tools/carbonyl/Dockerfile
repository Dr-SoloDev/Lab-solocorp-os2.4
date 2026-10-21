# SoloCorp carbonyl reader — อ่านเว็บที่ต้อง render JS โดยไม่ต้องมี display
#
# เหตุผลที่ไม่ใช้ Chrome:  Chrome ต้องการ ~1.4GB RAM + Xorg/display stack
#                             carbonyl ใช้ ~46MB RAM + ไม่ต้องมี display เลย
#
# ไม่มี apt-get → ไม่มี network ตอน build → build เร็ว ไม่ต้องรอเน็ต
FROM fathyb/carbonyl:latest

USER root
COPY entrypoint.sh /usr/local/bin/carbonyl-read
RUN chmod 0755 /usr/local/bin/carbonyl-read

# กลับมาเป็น user เดิม (uid 999) — ไม่รันเป็น root
USER carbonyl

ENTRYPOINT ["/usr/local/bin/carbonyl-read"]
