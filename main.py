import os
import imaplib
import email
from email.header import decode_header
import asyncio
import edge_tts
from feedgen.feed import FeedGenerator
import datetime
import pytz

# 1. 從環境變數讀取帳號密碼 (這樣就不用寫死在程式碼裡)
USERNAME = os.environ.get("GMAIL_USER")
APP_PASSWORD = os.environ.get("GMAIL_PASS")
TARGET_SENDER = "cnaweb2012@103983286.mailchimpapp.com" # !!! 換成你訂閱的新聞信箱 !!!
GITHUB_PAGE_URL = "https://jackysigur.github.io/nesw-reader" # !!! 換成你的 GitHub Pages 網址 !!!

def get_latest_email_text():
    print("開始連接 Gmail...")
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(USERNAME, APP_PASSWORD)
    mail.select("inbox")
    
    # 尋找未讀信件
    status, messages = mail.search(None, f'(FROM "{TARGET_SENDER}" UNSEEN)')
    email_ids = messages[0].split()
    
    if not email_ids:
        print("沒有新的未讀電子報。")
        return None, None
        
    latest_email_id = email_ids[-1]
    status, msg_data = mail.fetch(latest_email_id, "(RFC822)")
    
    title = "今日新聞"
    body_text = ""
    
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1])
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                title = subject.decode(encoding if encoding else "utf-8")
                
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body_text = part.get_payload(decode=True).decode()
                        break
            else:
                body_text = msg.get_payload(decode=True).decode()
                
    mail.close()
    mail.logout()
    return title, body_text

async def generate_audio_and_rss(title, text):
    # 用今天的日期來命名檔案，例如 episode_20260928.mp3
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    mp3_filename = f"episode_{today_str}.mp3"
    
    print(f"開始轉換語音: {mp3_filename}...")
    communicate = edge_tts.Communicate(text, "zh-TW-HsiaoChenNeural")
    await communicate.save(mp3_filename)
    mp3_size = os.path.getsize(mp3_filename)
    
    print("開始生成 RSS...")
    fg = FeedGenerator()
    fg.load_extension('podcast')
    fg.title('我的專屬晨間新聞')
    fg.description('自動從 Gmail 抓取電子報轉成的每日語音新聞')
    fg.link(href=GITHUB_PAGE_URL, rel='alternate')
    fg.language('zh-TW')
    
    fe = fg.add_entry()
    mp3_url = f"{GITHUB_PAGE_URL}/{mp3_filename}"
    fe.id(mp3_url)
    fe.title(title)
    fe.description("為您朗讀最新的電子報內容。")
    tz = pytz.timezone('Asia/Taipei')
    fe.published(datetime.datetime.now(tz))
    fe.enclosure(mp3_url, str(mp3_size), 'audio/mpeg')

    fg.rss_file('feed.xml')
    print("全部完成！")

async def main():
    title, text = get_latest_email_text()
    if title and text:
        await generate_audio_and_rss(title, text)

if __name__ == "__main__":
    asyncio.run(main())