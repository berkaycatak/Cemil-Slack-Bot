#!/usr/bin/env python3
"""
Glossary statik HTML sayfası üreticisi.
Tüm onaylanmış terimleri ve açıklamalarını tek bir HTML dosyasına yazar.
Kullanım: python scripts/generate_glossary_html.py
Çıktı:   data/glossary.html
"""

import json
import os
import sys
from datetime import datetime

# Proje kökünü sys.path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.singleton import SingletonMeta
from src.clients.database_client import DatabaseClient
from src.repositories.glossary_term_repository import GlossaryTermRepository
from src.repositories.glossary_definition_repository import GlossaryDefinitionRepository


def generate_html(output_path: str = "data/glossary.html"):
    """Statik HTML glossary sayfası üretir."""
    # Singleton cache'i temizle (script bağımsız çalışsın)
    SingletonMeta._instances.pop(DatabaseClient, None)

    db_path = os.environ.get("DATABASE_PATH", "data/cemil_bot.db")
    db = DatabaseClient(db_path=db_path)
    term_repo = GlossaryTermRepository(db)
    def_repo = GlossaryDefinitionRepository(db)

    terms = term_repo.get_all_approved()
    categories = term_repo.get_categories()

    # Her terim için açıklamaları topla
    terms_data = []
    for t in terms:
        definitions = def_repo.get_by_term_id(t["id"])
        related = []
        if t.get("related_terms"):
            try:
                related = json.loads(t["related_terms"])
            except (json.JSONDecodeError, TypeError):
                pass
        terms_data.append({
            "term": t["term"],
            "category": t["category"],
            "term_type": t.get("term_type", "term"),
            "related": related,
            "definitions": [
                {"text": d["definition"], "helpful": d["helpful_count"]}
                for d in definitions
            ],
        })

    # Kategoriye göre sırala
    terms_data.sort(key=lambda x: (x["category"], x["term"]))
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = _render_html(terms_data, categories, generated_at)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[+] Glossary HTML olusturuldu: {output_path} ({len(terms_data)} terim)")


def _render_html(terms_data, categories, generated_at):
    """HTML template'ini render eder."""
    # Terim kartlarını oluştur
    term_cards = ""
    for t in terms_data:
        defs_html = ""
        for d in t["definitions"]:
            defs_html += f'<div class="definition"><p>{_escape(d["text"])}</p><span class="helpful">{d["helpful"]} faydali</span></div>'
        if not t["definitions"]:
            defs_html = '<p class="no-def">Henuz aciklama eklenmemis.</p>'

        related_html = ""
        if t["related"]:
            tags = " ".join([f'<span class="tag">{_escape(r)}</span>' for r in t["related"]])
            related_html = f'<div class="related">Iliskili: {tags}</div>'

        term_cards += f"""
        <div class="card" data-category="{_escape(t['category'])}">
            <div class="card-header">
                <h3>{_escape(t['term'])}</h3>
                <span class="category">{_escape(t['category'])}</span>
            </div>
            {related_html}
            {defs_html}
        </div>"""

    # Kategori butonları
    cat_buttons = '<button class="cat-btn active" data-cat="all">Tumu</button>'
    for cat in categories:
        cat_buttons += f'<button class="cat-btn" data-cat="{_escape(cat)}">{_escape(cat)}</button>'

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Akademi Sozlugu</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;color:#333;line-height:1.6}}
.container{{max-width:1000px;margin:0 auto;padding:20px}}
header{{text-align:center;padding:40px 0 20px;}}
h1{{font-size:2em;color:#1a1a2e}}
.subtitle{{color:#666;margin-top:8px}}
.search-box{{width:100%;max-width:500px;margin:20px auto;display:block;padding:12px 16px;border:2px solid #ddd;border-radius:8px;font-size:16px;outline:none;transition:border .3s}}
.search-box:focus{{border-color:#4a90d9}}
.categories{{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin:20px 0}}
.cat-btn{{padding:6px 16px;border:1px solid #ddd;border-radius:20px;background:#fff;cursor:pointer;font-size:14px;transition:all .2s}}
.cat-btn:hover,.cat-btn.active{{background:#4a90d9;color:#fff;border-color:#4a90d9}}
.cards{{display:grid;gap:16px;margin-top:20px}}
.card{{background:#fff;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.08);transition:transform .2s}}
.card:hover{{transform:translateY(-2px)}}
.card-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}}
.card-header h3{{font-size:1.2em;color:#1a1a2e}}
.category{{background:#e8f0fe;color:#4a90d9;padding:2px 10px;border-radius:12px;font-size:12px}}
.definition{{background:#f8f9fa;padding:12px;border-radius:8px;margin-top:8px;border-left:3px solid #4a90d9}}
.helpful{{font-size:12px;color:#888;margin-top:4px;display:inline-block}}
.related{{margin-top:8px;font-size:13px;color:#666}}
.tag{{background:#f0f0f0;padding:2px 8px;border-radius:4px;margin:0 2px;font-size:12px}}
.no-def{{color:#999;font-style:italic;margin-top:8px}}
.hidden{{display:none}}
footer{{text-align:center;padding:40px 0 20px;color:#999;font-size:13px}}
</style>
</head>
<body>
<div class="container">
<header>
<h1>Akademi Sozlugu</h1>
<p class="subtitle">Yapay Zeka ve Teknoloji Akademisi - Topluluk Sozlugu</p>
</header>
<input type="text" class="search-box" placeholder="Terim ara..." id="search">
<div class="categories">{cat_buttons}</div>
<div class="cards" id="cards">{term_cards}</div>
<footer>Son guncelleme: {generated_at} | {len(terms_data)} terim</footer>
</div>
<script>
const search=document.getElementById('search');
const cards=document.querySelectorAll('.card');
const catBtns=document.querySelectorAll('.cat-btn');
let activeCat='all';

search.addEventListener('input',filter);
catBtns.forEach(b=>b.addEventListener('click',function(){{
  catBtns.forEach(x=>x.classList.remove('active'));
  this.classList.add('active');
  activeCat=this.dataset.cat;
  filter();
}}));

function filter(){{
  const q=search.value.toLowerCase();
  cards.forEach(c=>{{
    const text=c.textContent.toLowerCase();
    const cat=c.dataset.category;
    const matchSearch=!q||text.includes(q);
    const matchCat=activeCat==='all'||cat===activeCat;
    c.classList.toggle('hidden',!(matchSearch&&matchCat));
  }});
}}
</script>
</body>
</html>"""


def _escape(text):
    """Basit HTML escape."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


if __name__ == "__main__":
    generate_html()
