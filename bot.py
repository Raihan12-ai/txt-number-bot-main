import os, asyncio
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN=os.environ.get("BOT_TOKEN")
SIZE=4
users={}
app=Flask(__name__)

@app.get("/")
def home(): return "RS_OTP_BOT is running."

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Upload TXT",callback_data="upload"),
         InlineKeyboardButton("🔢 Number List",callback_data="list")],
        [InlineKeyboardButton("🔍 Search",callback_data="search"),
         InlineKeyboardButton("📊 Statistics",callback_data="stats")],
        [InlineKeyboardButton("⚙️ Settings",callback_data="settings"),
         InlineKeyboardButton("ℹ️ Help",callback_data="help")]
    ])

def nav(s,n):
    r=[]
    x=[]
    if s>0: x.append(InlineKeyboardButton("⬅️ Previous 4",callback_data=f"page:{max(0,s-SIZE)}"))
    if s+SIZE<n: x.append(InlineKeyboardButton("Next 4 ➡️",callback_data=f"page:{s+SIZE}"))
    if x:r.append(x)
    r.append([InlineKeyboardButton("🔢 Go to Serial",callback_data="goto"),
              InlineKeyboardButton("🔄 Change",callback_data="change")])
    r.append([InlineKeyboardButton("↩️ Back",callback_data="back")])
    return InlineKeyboardMarkup(r)

def text(nums,s):
    e=min(s+SIZE,len(nums))
    return "📄 *RS_OTP_BOT*\n\n📊 Total: `"+str(len(nums))+"`\n📌 Showing: `"+str(s+1)+"-"+str(e)+"`\n\n"+"\n".join(f"*{i+1}.* `{nums[i]}`" for i in range(s,e))

async def start(u,c):
    users[u.effective_user.id]={"n":[],"s":0,"goto":False,"search":False}
    await u.message.reply_text("🔥 *RS_OTP_BOT*\n\nএকটি `.txt` file পাঠান। প্রতি লাইনে একটি করে number রাখুন।",parse_mode="Markdown",reply_markup=menu())

async def doc(u,c):
    uid=u.effective_user.id; f=u.message.document
    if not f.file_name.lower().endswith(".txt"):
        await u.message.reply_text("❌ শুধু `.txt` file পাঠান।"); return
    if f.file_size and f.file_size>20*1024*1024:
        await u.message.reply_text("❌ File 20 MB-এর বেশি।"); return
    tf=await c.bot.get_file(f.file_id); data=await tf.download_as_bytearray()
    nums=[x.strip() for x in bytes(data).decode("utf-8-sig",errors="replace").splitlines() if x.strip()]
    if not nums: await u.message.reply_text("❌ TXT file-এ কোনো data পাওয়া যায়নি।"); return
    users[uid]={"n":nums,"s":0,"goto":False,"search":False}
    await u.message.reply_text(text(nums,0),parse_mode="Markdown",reply_markup=nav(0,len(nums)))

async def cb(u,c):
    q=u.callback_query; await q.answer(); uid=q.from_user.id
    z=users.setdefault(uid,{"n":[],"s":0,"goto":False,"search":False}); nums=z["n"]; a=q.data
    if a=="upload": await q.message.reply_text("📄 একটি `.txt` file পাঠান।"); return
    if a=="help": await q.message.reply_text("TXT upload করুন → ৪টি করে দেখুন → Next/Previous বা Go to Serial ব্যবহার করুন।"); return
    if a=="settings": await q.message.reply_text("⚙️ Brand: RS_OTP_BOT\nPage size: 4"); return
    if a=="stats":
        if not nums: await q.message.reply_text("আগে TXT upload করুন।"); return
        await q.message.reply_text(f"📊 Total: {len(nums)}\nUnique: {len(set(nums))}\nDuplicate: {len(nums)-len(set(nums))}"); return
    if a=="search":
        if not nums: await q.message.reply_text("আগে TXT upload করুন।"); return
        z["search"]=True; z["goto"]=False; await q.message.reply_text("🔍 যে number/text খুঁজবেন সেটি পাঠান।"); return
    if a=="list":
        if not nums: await q.message.reply_text("আগে TXT upload করুন।"); return
        await q.message.reply_text(text(nums,z["s"]),parse_mode="Markdown",reply_markup=nav(z["s"],len(nums))); return
    if a=="goto":
        if not nums: await q.message.reply_text("আগে TXT upload করুন।"); return
        z["goto"]=True; z["search"]=False; await q.message.reply_text("🔢 Serial দিন। যেমন `25`",parse_mode="Markdown"); return
    if a=="change":
        z.update(n=[],s=0,goto=False,search=False); await q.message.reply_text("🔄 Reset হয়েছে। নতুন TXT file পাঠান।"); return
    if a=="back": await q.message.reply_text("🏠 *RS_OTP_BOT Main Menu*",parse_mode="Markdown",reply_markup=menu()); return
    if a.startswith("page:"):
        if not nums: return
        z["s"]=int(a.split(":")[1]); z["goto"]=z["search"]=False
        await q.edit_message_text(text(nums,z["s"]),parse_mode="Markdown",reply_markup=nav(z["s"],len(nums)))

async def msg(u,c):
    uid=u.effective_user.id; z=users.get(uid)
    if not z or not z["n"]: return
    nums=z["n"]; t=u.message.text.strip()
    if z["search"]:
        z["search"]=False; m=[(i+1,x) for i,x in enumerate(nums) if t.lower() in x.lower()]
        await u.message.reply_text("🔍 No match." if not m else "🔍 *Results*\n\n"+"\n".join(f"*{i}.* `{x}`" for i,x in m[:50]),parse_mode="Markdown"); return
    if z["goto"]:
        try: n=int(t)
        except: await u.message.reply_text("❌ শুধু serial number দিন।"); return
        if not 1<=n<=len(nums): await u.message.reply_text(f"❌ 1 থেকে {len(nums)} দিন।"); return
        z["s"]=(n-1)//SIZE*SIZE; z["goto"]=False
        await u.message.reply_text(text(nums,z["s"]),parse_mode="Markdown",reply_markup=nav(z["s"],len(nums)))

def run():
    async def x():
        a=Application.builder().token(TOKEN).build()
        a.add_handler(CommandHandler("start",start))
        a.add_handler(MessageHandler(filters.Document.ALL,doc))
        a.add_handler(CallbackQueryHandler(cb))
        a.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,msg))
        await a.initialize(); await a.start(); await a.updater.start_polling(); await asyncio.Event().wait()
    asyncio.run(x())

if __name__=="__main__":
    if not TOKEN: raise RuntimeError("BOT_TOKEN is missing")
    Thread(target=run,daemon=True).start()
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT","10000")))
