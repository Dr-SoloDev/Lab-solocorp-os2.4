# engineering @ forum-20260928-005

จากมุม engineering: ข้อ 5 (ffmpeg ต่อ master + ปก) คือจุดที่ pipeline จะพังเงียบที่สุด — encoding params, audio loudness, subtitle burn-in เป็นสิ่งที่ต้อง fix ทีหลังแพงกว่าเขียนเรื่องใหม่ ผมวาง spec ของ render layer เป็น contract ให้ตั้งแต่ตอน EP.1 (preset, bitrate, resolution, loudness target, safe area ของปก/หัวข้อโพส) ไว้ก่อน ทุก EP. ต่อยอดจาก config เดิม ไม่ใช่ปรับมือทีละคลิป

จุดดี: มี review gate ก่อนเจน = spec ของผมมี contract ชัด ไม่ต้องเดาเองว่า "น่าจะแบบนี้"

จุดเสี่ยง: ingest ความรู้จาก repo → brief ถ้าไม่มีตรา source กำกับ (file + line) ทุก claim ในสคริปต์จะ verify ไม่ได้ และเครดิต
