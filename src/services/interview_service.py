class InterviewService:

    def __init__(self, groq_client):

        self.groq = groq_client



    async def generate_question(self, field, mode):

        system_prompt = f"Sen disiplinli bir teknik lider ve {mode} uzmanısın. Sadece Türkçe konuş."

        context_instruct = (

            "Pratik kullanıma dayalı bir soru sor." if mode == "İş Mülakatı"

            else "Teorik ve akademik bir sınav sorusu sor."

        )

        user_prompt = f"{field} alanında, {context_instruct} Soru kısa ve öz (max 2 cümle) olsun."

        return await self.groq.quick_ask(system_prompt, user_prompt)



    async def analyze_answer(self, field, question, answer, step, mode):

        

        system_prompt = (

            f"Sen ciddi bir {mode} değerlendiricisisin. Sadece adayın verdiği '{answer}' yanıtını puanla. "

            "ASLA adayın yerine doğru cevabı yazıp ona puan verme. "

            "Eğer aday 'bilmiyorum', 'bilmem' veya anlamsız bir şey yazdıysa puan KESİNLİKLE 0/5 olmalıdır."

        )

        instruct = (

            f"Cevabı {mode} kriterlerine göre dürüstçe puanla (Puan: X/5). "

            f"Eğer {step} < 3 ise, konuyu derinleştirecek bir sonraki soruyu sor."

        ) if step < 3 else "Puan ver ve mülakatı bitir."

           

        user_prompt = f"Soru: {question}\nAdayın Cevabı: {answer}\n\n{instruct}"

        return await self.groq.quick_ask(system_prompt, user_prompt)



    async def generate_final_report(self, field, total_score, average_score, user_name, mode):

        system_prompt = f"Sen {mode} sonucunu dürüstçe açıklayan bir yöneticisin."

        user_prompt = (

            f"Aday: {user_name}, Alan: {field}, Puan: {total_score}/15. \n"

            "Bu sonuca göre adaya samimi ama teknik eksiklerini yüzüne vuran bir rapor yaz. "

            "Sonuna 'Görüşmek üzere, Teknik Lider Cemil' ekle."

        )

        return await self.groq.quick_ask(system_prompt, user_prompt)