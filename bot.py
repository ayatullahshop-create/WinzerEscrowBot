# Telegram Escrow Bot (Railway Ready)
# Replace the Bangla-marked fields before deploying.

import asyncio
import logging
import sqlite3
import uuid
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_ID = 30825460
API_HASH = acc76656f29084c62f10cfddc44a15bb
BOT_TOKEN = 8182617462:AAGXq4vaXFcO2ch8P-yWvwrVV_Lc1YCLV8w
VOUCHER_CHANNEL = @WinzerEscrowBotVoucher
OWNER_ID = None  @WINZER_OWNER

DB = "escrow.db"

conn = sqlite3.connect(DB, check_same_thread=False)
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS orders(
 order_id TEXT PRIMARY KEY,
 buyer_id INTEGER,
 seller_id INTEGER,
 group_id INTEGER,
 amount REAL,
 status TEXT,
 voucher TEXT,
 created_at TEXT,
 updated_at TEXT
)""")
conn.commit()

bot = Client("escrow_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

def now_iso(): return datetime.utcnow().isoformat()

def create_order(order_id,buyer_id,seller_id,amount):
    cur.execute("INSERT INTO orders(order_id,buyer_id,seller_id,amount,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
    (order_id,buyer_id,seller_id,amount,"initiated",now_iso(),now_iso()))
    conn.commit()

def update_order(order_id, **kw):
    sets=[]; vals=[]
    for k,v in kw.items(): sets.append(f"{k}=?"); vals.append(v)
    vals.append(order_id)
    cur.execute(f"UPDATE orders SET {', '.join(sets)}, updated_at=? WHERE order_id=?",
        (*vals[:-1],now_iso(),vals[-1]))
    conn.commit()

def get_order(order_id):
    cur.execute("SELECT * FROM orders WHERE order_id=?",(order_id,))
    r=cur.fetchone()
    if not r: return None
    keys=['order_id','buyer_id','seller_id','group_id','amount','status','voucher','created_at','updated_at']
    return dict(zip(keys,r))

def kb(orderid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Mark Paid",callback_data=f"paid:{orderid}"),
         InlineKeyboardButton("Seller Confirm",callback_data=f"confirm:{orderid}")],
        [InlineKeyboardButton("Cancel",callback_data=f"cancel:{orderid}")]
    ])

@bot.on_message(filters.command("start"))
async def start(_,m): await m.reply("Escrow Bot Ready!")

@bot.on_message(filters.command("create"))
async def create_cmd(_,m):
    if len(m.command)<4:
        return await m.reply("Usage: /create <order_id> <amount> <seller_id>")
    oid=m.command[1]; amt=float(m.command[2]); sid=int(m.command[3])
    bid=m.from_user.id
    if get_order(oid): return await m.reply("Order exists.")
    create_order(oid,bid,sid,amt)
    await m.reply(f"Order {oid} created!", reply_markup=kb(oid))

@bot.on_callback_query()
async def cb(_,cq):
    data=cq.data; uid=cq.from_user.id
    if data.startswith("paid:"):
        oid=data[5:]; o=get_order(oid)
        if uid!=o['buyer_id']: return await cq.answer("Only buyer.")
        update_order(oid,status="paid"); return await cq.answer("Paid marked.")
    if data.startswith("confirm:"):
        oid=data[8:]; o=get_order(oid)
        if uid!=o['seller_id']: return await cq.answer("Only seller.")
        v=str(uuid.uuid4())[:12].upper()
        update_order(oid,status="released",voucher=v)
        try: await bot.send_message(VOUCHER_CHANNEL,f"Order {oid} Voucher: {v}")
        except: pass
        return await cq.answer("Voucher Released!")
    if data.startswith("cancel:"):
        oid=data[7:]; o=get_order(oid)
        update_order(oid,status="cancelled")
        return await cq.answer("Cancelled.")

async def main():
    await bot.start()
    while True: await asyncio.sleep(1)

if __name__=="__main__":
    asyncio.run(main())
