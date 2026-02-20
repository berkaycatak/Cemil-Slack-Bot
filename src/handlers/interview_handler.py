from slack_bolt import App
import asyncio
import re

active_interviews = {}

def setup_interview_handlers(app: App, interview_service, chat_manager):
    
    @app.command("/mulakat")
    def handle_interview(ack, body, client):
        ack()
        try:
            user_id = body["user_id"]
            channel_id = body["channel_id"]
            raw_text = body.get("text", "").strip()
            text_parts = raw_text.split()
            
            if not text_parts:
                text_parts = ["Computer", "Engineering"]

            is_exam = any(p.lower() == "sınav" for p in text_parts)
            mode = "Sınav" if is_exam else "İş Mülakatı"
            
            field_parts = [p for p in text_parts if p.lower() != "sınav"]
            field = " ".join(field_parts) if field_parts else "Computer Engineering"
            
            user_info = client.users_info(user=user_id)
            user_name = user_info["user"]["profile"].get("first_name") or user_info["user"]["name"]
            
            async def run_start():
                question = await interview_service.generate_question(field, mode)
                active_interviews[user_id] = {
                    "field": field, "mode": mode, "user_name": user_name, 
                    "last_question": question, "step": 1, "total_score": 0
                }
                chat_manager.post_message(
                    channel=channel_id, 
                    text=f"🚀 *Hoş geldin {user_name}!* \n*Mod:* {mode} | *Konu:* {field}\n\n*Soru:* {question}"
                )
            asyncio.run(run_start())
        except Exception as e:
            print(f"[X] Hata: {e}")

    @app.message()
    def handle_answer(message, say):
        user_id = message["user"]
        channel_id = message["channel"]
        if user_id in active_interviews:
            interview = active_interviews[user_id]
            
            async def run_analysis():
                try:
                    analysis = await interview_service.analyze_answer(
                        interview["field"], interview["last_question"], 
                        message["text"], interview["step"], interview["mode"]
                    )
                    
                    
                    match = re.search(r"[Pp]uan[:\s-]*(\d+)/5", analysis)
                    
                   
                    current_score = int(match.group(1)) if match else 0 
                    
                    interview["total_score"] += current_score
                    
                    if interview["step"] < 3:
                        interview["step"] += 1
                        interview["last_question"] = analysis
                        chat_manager.post_message(channel=channel_id, text=f"✅ *Değerlendirme:*\n{analysis}")
                    else:
                        avg_score = interview["total_score"] / 3
                        final_report = await interview_service.generate_final_report(
                            interview["field"], interview["total_score"], avg_score, 
                            interview["user_name"], interview["mode"]
                        )
                        chat_manager.post_message(
                            channel=channel_id,
                            text=f"🏁 *Mülakat Tamamlandı!*\n\n{final_report}\n\n📊 *KARNE:*\n• Aday: {interview['user_name']}\n• Toplam: {interview['total_score']}/15\n• Mod: {interview['mode']}"
                        )
                        del active_interviews[user_id]
                except Exception as e:
                    print(f"[X] Analiz Hatası: {e}")
            
            asyncio.run(run_analysis())