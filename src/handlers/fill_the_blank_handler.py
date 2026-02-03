from slack_bolt import App
from src.services.fill_the_blank_service import FillTheBlankService
from src.core.logger import logger
import json
import time

def setup_fill_the_blank_handlers(app: App, service: FillTheBlankService):
    
    @app.command("/filltheblank")
    def handle_fill_the_blank_command(ack, body, client):
        ack()
        # Slash command payload vs Block Action payload
        if "user_id" in body:
            user_id = body["user_id"] # Slash command
        else:
            user_id = body["user"]["id"] # Block action
        
        # Kategorileri çek
        # Bu async bir fonksiyon olduğu için asyncio.run veya benzeri gerekebilir 
        # ama bolt'un async modunda mıyız? src/bot.py'de async/sync karmaşası olabilir.
        # Bu proje senkron mu asenkron mu? Kodlara bakınca async kütüphaneler var ama bolt app sync gibi.
        # Genelde 'app = App(...)' senkron, 'AsyncApp' asenkrondur.
        # Ancak burada 'asyncio.run' kullanmak güvenli olabilir.
        
        try:
            import asyncio
            categories = asyncio.run(service.get_categories())
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🎵 Fill The Blank Game 🎵",
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Lütfen bir müzik kategorisi seçin:"
                    }
                },
                {
                    "type": "actions",
                    "elements": []
                }
            ]
            
            for cat in categories:
                # 'names' alanı db'den veya api'den JSON string olarak gelebilir
                cat_names = cat.get("names", "{}")
                if isinstance(cat_names, str):
                    try:
                        cat_names = json.loads(cat_names)
                    except json.JSONDecodeError:
                        cat_names = {}
                elif isinstance(cat_names, dict):
                     pass
                else:
                     cat_names = {}

                blocks[2]["elements"].append({
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": cat_names.get("en", "Unknown"), 
                        "emoji": True
                    },
                    "value": str(cat["document_id"]),
                    "action_id": f"ftb_category_{cat['document_id']}"
                })
            
            client.chat_postMessage(channel=user_id, blocks=blocks, text="Kategori seçimi")
            
        except Exception as e:
            logger.error(f"Komut hatası: {e}", exc_info=True)
            client.chat_postMessage(channel=user_id, text="Bir hata oluştu. Lütfen tekrar deneyin.")

    # Kategori seçimi handler'ı (action_id regex ile yakalanabilir)
    @app.action(re.compile("ftb_category_.*"))
    def handle_category_selection(ack, body, client):
        ack()
        user_id = body["user"]["id"]
        channel_id = body["channel"]["id"]
        category_id = body["actions"][0]["value"]
        
        # Kullanıcıya "Şarkı hazırlanıyor..." mesajı
        msg = client.chat_postMessage(channel=channel_id, text="⏳ Şarkı hazırlanıyor...")
        ts = msg["ts"]
        
        try:
            import asyncio
            game_data = asyncio.run(service.start_game(user_id, channel_id, category_id))
            
            # Mesajı güncelle: Şarkıyı ve soruyu gönder
            # Slack'e ses dosyası yüklemek için files_upload kullanılır ama URL varsa link de verilebilir.
            # Ancak "preview_url" genellikle public'tir.
            
            # Önceki "Hazırlanıyor" mesajını sil
            client.chat_delete(channel=channel_id, ts=ts)

            # 1. Ses dosyasını yükle (Audio Player) ve Başlığı Yorum Olarak Ekle
            # Bu sayede Başlık ve Player aynı anda belirir.
            audio_content = game_data.get("audio_content")
            if audio_content:
                try:
                    # Dosyayı yükle
                    upload_res = client.files_upload_v2(
                        channel=channel_id,
                        file=audio_content,
                        filename="preview.m4a",
                        title=f"{game_data['title']} - {game_data['artist']}",
                        initial_comment=f"*{game_data['title']} - {game_data['artist']}*"
                    )
                except Exception as upload_err:
                    logger.error(f"Dosya yükleme hatası: {upload_err}")
                    client.chat_postMessage(channel=channel_id, text=f"🎵 Dinle: {game_data['preview_url']}")
            else:
                 client.chat_postMessage(channel=channel_id, text=f"🎵 Dinle: {game_data['preview_url']}")

            # 2. Oyun Bloğu (Game Block)
            game_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Boşlukları Doldur:*\n\n>{game_data['blanked_lyrics']}"
                    }
                },
                {
                    "type": "input",
                    "block_id": "ftb_answer_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "ftb_answer_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Eksik kelimeleri yazın..."
                        }
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Cevabınız:"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Gönder",
                                "emoji": True
                            },
                            "style": "primary",
                            "value": "submit_answer",
                            "action_id": "ftb_submit_answer"
                        }
                    ]
                }
            ]
            client.chat_postMessage(channel=channel_id, blocks=game_blocks, text="Boşlukları doldur!")
            
        except Exception as e:
            logger.error(f"Oyun başlatma hatası: {e}")
            client.chat_update(channel=channel_id, ts=ts, text=f"❌ Bir hata oluştu: {e}")

    @app.action("ftb_submit_answer")
    def handle_answer_submission(ack, body, client):
        ack()
        user_id = body["user"]["id"]
        channel_id = body["channel"]["id"]
        
        # Input değerini al (state içinden)
        values = body["state"]["values"]
        answer = values["ftb_answer_block"]["ftb_answer_input"]["value"]
        
        try:
            # Cevabı kontrol et (Senkron çalıştırıyoruz repository çağrıları için, 
            # ama service async tanımlı olabilir, db işlemleri senkron ise service'i ona göre ayarlamalıyız.
            # Üstteki service tanımında repository çağrıları senkron, client çağrıları asenkron.
            # check_answer tamamen senkron (db işlemleri).
            
            result = service.check_answer(user_id, answer)
            
            if result.get("status") == "no_game":
                 client.chat_postMessage(channel=channel_id, text="Aktif bir oyununuz bulunamadı.")
                 return

            score = result["score"]
            correct_words = ", ".join(result["correct_words"])
            
            response_text = ""
            if score == 100:
                response_text = f"🎉 *Tebrikler!* Tam Puan! (100/100)\nDoğru kelimeler: `{correct_words}`"
            elif score > 0:
                 response_text = f"👏 *Güzel Deneme!* Puanın: {score}/100\nDoğru kelimeler: `{correct_words}`"
            else:
                 response_text = f"😢 *Maalesef Bilemedin.* Puanın: {score}/100\nDoğru kelimeler: `{correct_words}`"
            
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": response_text
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Orijinal Sözler:\n{result['original_lyrics']}"
                        }
                    ]
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Tekrar Oyna",
                                "emoji": True
                            },
                            "value": result.get("category_id", ""), 
                            "action_id": "ftb_play_again"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Kategori Seç",
                                "emoji": True
                            },
                            "value": "choose_category",
                            "action_id": "ftb_choose_category"
                        }
                    ]
                }
            ]
            
            client.chat_postMessage(channel=channel_id, blocks=blocks, text=f"Oyun Sonucu: {score}")
            
        except Exception as e:
            logger.error(f"Cevap kontrol hatası: {e}")
            client.chat_postMessage(channel=channel_id, text="Hata oluştu.")

    @app.action("ftb_play_again")
    def handle_play_again(ack, body, client):
        ack()
        user_id = body["user"]["id"]
        channel_id = body["channel"]["id"]
        category_id = body["actions"][0]["value"]
        
        # Eğer kategori ID yoksa veya eski butonlardan "play_again" geliyorsa, kategori seçimine yönlendir
        if not category_id or category_id == "play_again":
             handle_fill_the_blank_command(ack, body, client)
             return

        # Kullanıcıya "Şarkı hazırlanıyor..." mesajı
        msg = client.chat_postMessage(channel=channel_id, text="⏳ Şarkı hazırlanıyor...")
        ts = msg["ts"]
        
        try:
            import asyncio
            game_data = asyncio.run(service.start_game(user_id, channel_id, category_id))
            
            # Önceki "Hazırlanıyor" mesajını sil
            client.chat_delete(channel=channel_id, ts=ts)

            # 1. Ses dosyasını yükle (Audio Player) ve Başlığı Yorum Olarak Ekle
            # Bu sayede Başlık ve Player aynı anda belirir.
            audio_content = game_data.get("audio_content")
            if audio_content:
                try:
                    # Dosyayı yükle
                    upload_res = client.files_upload_v2(
                        channel=channel_id,
                        file=audio_content,
                        filename="preview.m4a",
                        title=f"{game_data['title']} - {game_data['artist']}",
                        initial_comment=f"*{game_data['title']} - {game_data['artist']}*"
                    )
                except Exception as upload_err:
                    logger.error(f"Dosya yükleme hatası: {upload_err}")
                    client.chat_postMessage(channel=channel_id, text=f"🎵 Dinle: {game_data['preview_url']}")
            else:
                 client.chat_postMessage(channel=channel_id, text=f"🎵 Dinle: {game_data['preview_url']}")

            # 2. Oyun Bloğu (Game Block)
            game_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Boşlukları Doldur:*\n\n>{game_data['blanked_lyrics']}"
                    }
                },
                {
                    "type": "input",
                    "block_id": "ftb_answer_block",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "ftb_answer_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Eksik kelimeleri yazın..."
                        }
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Cevabınız:"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Gönder",
                                "emoji": True
                            },
                            "style": "primary",
                            "value": "submit_answer",
                            "action_id": "ftb_submit_answer"
                        }
                    ]
                }
            ]
            client.chat_postMessage(channel=channel_id, blocks=game_blocks, text="Boşlukları doldur!")
            
        except Exception as e:
            logger.error(f"Oyun başlatma hatası: {e}")
            client.chat_update(channel=channel_id, ts=ts, text=f"❌ Bir hata oluştu: {e}")

    @app.action("ftb_choose_category")
    def handle_choose_category(ack, body, client):
        handle_fill_the_blank_command(ack, body, client)

import re
