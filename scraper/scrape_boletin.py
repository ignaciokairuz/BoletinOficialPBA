"""
Boletín Oficial Provincia de Buenos Aires - Scraper v2
--------------------------------------------------------
Scrapes spending and normas from the Boletín Oficial PBA.
Uses direct HTTP requests to fetch recent norms.
"""
import requests
from bs4 import BeautifulSoup
import json
import re
import time
import os
from datetime import datetime, timedelta
from gradio_client import Client

# Configuration
BASE_URL = "https://normas.gba.gob.ar"
BOLETIN_HOME = "https://boletinoficial.gba.gob.ar"
DATA_DIR = "docs"

# Types of norms to search
NORM_TYPES = ['resolucion', 'disposicion', 'decreto']

# Keywords for identifying spending
GASTO_KEYWORDS = [
    'licitación', 'contratación', 'adjudica', 'compra', 'adquisición',
    'provisión', 'suministro', 'servicio', 'obra', 'presupuesto',
    'precio', 'monto', 'pago', 'costo', 'gasto'
]

AMOUNT_REGEX = r'\$\s?([\d]{1,3}(?:\.[\d]{3})*(?:,[\d]{1,2})?)'

def get_latest_bulletin_info():
    """Get latest bulletin number and date from home page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        r = requests.get(BOLETIN_HOME, timeout=30, headers=headers)
        text = r.text
        
        # Look for bulletin number pattern like "N° 30166"
        num_match = re.search(r'N[°º]\s*(\d{5})', text)
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', text)
        
        bulletin_num = num_match.group(1) if num_match else None
        bulletin_date = date_match.group(1) if date_match else datetime.now().strftime('%d/%m/%Y')
        
        print(f"   Encontrado: Boletín N° {bulletin_num} - {bulletin_date}")
        return bulletin_num, bulletin_date
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return None, datetime.now().strftime('%d/%m/%Y')

def extract_amounts(text):
    """Extract monetary amounts from text"""
    if not text:
        return []
    amounts = []
    for m in re.finditer(AMOUNT_REGEX, text):
        val_str = m.group(1).replace('.', '').replace(',', '.')
        try:
            val = float(val_str)
            if val > 1000:  # Filter noise
                amounts.append(val)
        except:
            continue
    return amounts

def is_spending_related(text):
    """Check if text indicates spending/contracting"""
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in GASTO_KEYWORDS)

def fetch_norm_detail(url):
    """Fetch full text from a norm page on normas.gba.gob.ar"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        r = requests.get(url, timeout=30, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Get all text from page
        text = soup.get_text(separator=' ', strip=True)
        
        # Try to extract specific sections
        title = ""
        summary = ""
        organismo = ""
        
        # Look for title patterns
        title_match = re.search(r'(Resolución|Disposición|Decreto|Ley)\s+\d+[/-]?\d*', text)
        if title_match:
            title = title_match.group(0)
        
        # Look for organism
        org_patterns = [
            r'del?\s+(Ministerio[^\.]+)',
            r'de la?\s+(Secretaría[^\.]+)',
            r'de la?\s+(Dirección[^\.]+)',
        ]
        for pattern in org_patterns:
            org_match = re.search(pattern, text, re.I)
            if org_match:
                organismo = org_match.group(1)[:80]
                break
        
        # Look for summary (often after "VISTO" or before "CONSIDERANDO")
        visto_match = re.search(r'VISTO[:\s]+(.{100,500}?)(?=CONSIDERANDO|Y CONSIDERANDO|POR ELLO)', text, re.I | re.S)
        if visto_match:
            summary = visto_match.group(1).strip()[:400]
        
        return {
            'title': title,
            'summary': summary,
            'organismo': organismo or 'Gobierno de la Provincia de Buenos Aires',
            'full_text': text[:3000]
        }
    except Exception as e:
        return None

def get_recent_norms_from_bulletin(bulletin_num):
    """Try to get norms from the bulletin sections"""
    norms = []
    
    # Try to fetch section page
    section_urls = [
        f"{BOLETIN_HOME}/secciones/{bulletin_num}/ver",
        f"{BOLETIN_HOME}/secciones/{int(bulletin_num)-1}/ver" if bulletin_num else None
    ]
    
    for url in section_urls:
        if not url:
            continue
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            r = requests.get(url, timeout=30, headers=headers)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Find links to normas.gba.gob.ar
            for link in soup.find_all('a', href=True):
                href = link['href']
                if 'normas.gba.gob.ar' in href:
                    norms.append({'url': href})
                    
        except Exception as e:
            continue
    
    return norms

def search_recent_norms_by_year():
    """Search for recent norms (2025/2026) by iterating known IDs"""
    print("🔍 Buscando normas recientes...")
    norms = []
    current_year = datetime.now().year
    
    # Try recent norm URLs based on known patterns
    # The pattern is: /ar-b/{type}/{year}/{number}/{internal_id}
    # IDs seem to be sequential
    
    # Known recent IDs from our exploration (around 468000+)
    start_id = 468000
    end_id = 470000
    
    # Sample some IDs to find valid norms
    sample_count = 0
    max_samples = 50
    
    for type_name in NORM_TYPES:
        if sample_count >= max_samples:
            break
            
        # Try different years and IDs
        for year in [2026, 2025, 2024]:
            if sample_count >= max_samples:
                break
                
            for i in range(start_id, end_id, 100):  # Step by 100
                if sample_count >= max_samples:
                    break
                    
                # Try a few number variations
                for num in range(1, 500, 50):
                    try:
                        url = f"{BASE_URL}/ar-b/{type_name}/{year}/{num}/{i}"
                        
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }
                        r = requests.get(url, timeout=10, headers=headers, allow_redirects=False)
                        
                        if r.status_code == 200:
                            detail = fetch_norm_detail(url)
                            if detail and detail.get('title'):
                                norms.append({
                                    'nombre': detail['title'],
                                    'sumario': detail['summary'],
                                    'url': url,
                                    'tipo': type_name.capitalize(),
                                    'organismo': detail['organismo'],
                                    'full_text': detail['full_text']
                                })
                                sample_count += 1
                                print(f"   ✓ {detail['title']}")
                                
                                if sample_count >= max_samples:
                                    break
                    except:
                        continue
                        
            time.sleep(0.2)
    
    print(f"   ✅ Encontradas {len(norms)} normas")
    return norms

def scrape_with_known_ids():
    """Scrape using known working ID patterns from our exploration"""
    print("🔍 Buscando normas con IDs conocidos...")
    norms = []
    
    # Known working IDs from our browser exploration:
    # https://normas.gba.gob.ar/ar-b/resolucion/2024/40202/468053
    # https://normas.gba.gob.ar/ar-b/disposicion/2024/6478/445651
    
    # Sample of recent-looking IDs to try
    known_patterns = [
        ('resolucion', 2024, [(40202, 468053), (40201, 468050), (40200, 468048)]),
        ('disposicion', 2024, [(6478, 445651), (6477, 445650), (6476, 445648)]),
        ('resolucion', 2025, [(100, 469000), (101, 469001), (102, 469002)]),
        ('disposicion', 2025, [(100, 466000), (101, 466001)]),
        ('decreto', 2024, [(100, 440000), (101, 440001)]),
        ('decreto', 2025, [(1, 468500), (2, 468501)]),
    ]
    
    for tipo, year, id_pairs in known_patterns:
        for num, internal_id in id_pairs:
            try:
                url = f"{BASE_URL}/ar-b/{tipo}/{year}/{num}/{internal_id}"
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                r = requests.get(url, timeout=10, headers=headers)
                
                if r.status_code == 200 and len(r.text) > 1000:
                    detail = fetch_norm_detail(url)
                    if detail:
                        norms.append({
                            'nombre': detail.get('title') or f"{tipo.capitalize()} {num}/{year}",
                            'sumario': detail.get('summary', '')[:400],
                            'url': url,
                            'tipo': tipo.capitalize(),
                            'organismo': detail.get('organismo', 'Provincia de Buenos Aires'),
                            'full_text': detail.get('full_text', '')[:2000]
                        })
                        print(f"   ✓ {tipo.capitalize()} {num}/{year}")
                        
            except Exception as e:
                continue
            
            time.sleep(0.3)
    
    print(f"   ✅ Encontradas {len(norms)} normas")
    return norms

def clean_ai_response(text):
    """Clean up AI response"""
    if not text:
        return ""
    if "Error" in text or "BadRequest" in text:
        return ""
    
    result = text
    markers = ["**💬 Response:**", "Response:**", "Análisis:**", "final**"]
    for m in markers:
        if m in result:
            result = result.split(m)[-1]
    
    # Remove markdown formatting
    result = re.sub(r'\*\*([^*]+)\*\*', r'\1', result)
    result = re.sub(r'\*([^*]+)\*', r'\1', result)
    return result.strip()[:400]

def get_ai_summary(client, text, prompt_type='short'):
    """Get AI summary for a norm"""
    try:
        if prompt_type == 'short':
            system = "Eres un asistente que resume documentos oficiales argentinos. Responde SOLO con un título descriptivo de 8-15 palabras en español que explique de qué trata la norma."
        else:
            system = "Eres un asistente que resume documentos oficiales argentinos. Explica en 3-4 oraciones claras y sencillas en español qué establece esta norma, quién la emite, y a quiénes afecta. Usa lenguaje simple."
        
        result = client.predict(
            message=text[:600],
            system_prompt=system,
            temperature=0.3,
            api_name="/chat"
        )
        return clean_ai_response(result)
    except Exception as e:
        print(f"   ⚠️ AI Error: {e}")
        return ""

def process_norms_with_ai(norms, client):
    """Add AI summaries to norms"""
    print(f"🤖 Generando resúmenes IA para {len(norms)} normas...")
    
    for i, norm in enumerate(norms):
        try:
            # Build context for AI
            text = f"{norm['nombre']}\n{norm.get('sumario', '')}\n{norm.get('full_text', '')[:400]}"
            
            # Get summaries
            norm['resumen_corto'] = get_ai_summary(client, text, 'short')
            if not norm['resumen_corto']:
                norm['resumen_corto'] = norm['nombre'][:80]
            
            norm['resumen_largo'] = get_ai_summary(client, text, 'long')
            if not norm['resumen_largo']:
                norm['resumen_largo'] = norm.get('sumario', '')[:300] or "Ver documento original para más detalles."
            
            # Check for spending
            full_text = norm.get('full_text', '')
            amounts = extract_amounts(full_text)
            
            if amounts:
                norm['monto'] = max(amounts)
                norm['monto_fmt'] = f"${norm['monto']:,.0f}"
                norm['tiene_gasto'] = True
            else:
                norm['tiene_gasto'] = is_spending_related(full_text + norm.get('sumario', ''))
            
            if (i + 1) % 5 == 0:
                print(f"   Progreso: {i+1}/{len(norms)}")
                
            time.sleep(0.5)  # Rate limit
            
        except Exception as e:
            norm['resumen_corto'] = norm['nombre'][:80]
            norm['resumen_largo'] = norm.get('sumario', '')[:300]
            norm['tiene_gasto'] = False
    
    return norms

def generate_html(data):
    """Generate static HTML site"""
    print("🌐 Generando HTML...")
    
    gastos = [n for n in data['normas'] if n.get('tiene_gasto')]
    otras = [n for n in data['normas'] if not n.get('tiene_gasto')]
    
    # Sort gastos by amount
    gastos.sort(key=lambda x: x.get('monto', 0), reverse=True)
    
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Boletín Oficial PBA - Análisis con IA</title>
    <meta name="description" content="Análisis del Boletín Oficial de la Provincia de Buenos Aires con resúmenes generados por IA para transparencia ciudadana">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --bg-card: #334155;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent: #3b82f6;
            --accent-glow: rgba(59, 130, 246, 0.3);
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --border: rgba(255,255,255,0.08);
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Inter', system-ui, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            background: linear-gradient(135deg, var(--bg-secondary) 0%, rgba(59, 130, 246, 0.1) 100%);
            border-bottom: 1px solid var(--border);
            padding: 40px 0;
            margin-bottom: 30px;
        }}
        
        header h1 {{
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #60a5fa, #34d399);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .subtitle {{
            color: var(--text-secondary);
            font-size: 1.1rem;
            margin-bottom: 5px;
        }}
        
        .update-time {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            opacity: 0.7;
        }}
        
        .stats {{
            display: flex;
            gap: 15px;
            margin-top: 25px;
            flex-wrap: wrap;
        }}
        
        .stat {{
            background: rgba(59, 130, 246, 0.15);
            padding: 16px 24px;
            border-radius: 12px;
            border: 1px solid var(--border);
            backdrop-filter: blur(10px);
        }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--accent);
        }}
        
        .stat-label {{
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-top: 4px;
        }}
        
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 25px;
            flex-wrap: wrap;
        }}
        
        .tab {{
            padding: 12px 28px;
            border-radius: 10px;
            border: 1px solid var(--border);
            background: var(--bg-secondary);
            color: var(--text-secondary);
            cursor: pointer;
            font-weight: 500;
            font-size: 0.95rem;
            transition: all 0.3s ease;
        }}
        
        .tab:hover {{
            background: var(--bg-card);
            color: var(--text-primary);
            border-color: var(--accent);
        }}
        
        .tab.active {{
            background: var(--accent);
            color: white;
            border-color: var(--accent);
            box-shadow: 0 4px 20px var(--accent-glow);
        }}
        
        .tab-content {{
            display: none;
            animation: fadeIn 0.3s ease;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        .card-grid {{
            display: grid;
            gap: 16px;
        }}
        
        .card {{
            background: var(--bg-secondary);
            border-radius: 14px;
            padding: 22px;
            border: 1px solid var(--border);
            transition: all 0.3s ease;
        }}
        
        .card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 12px 40px rgba(0,0,0,0.4);
            border-color: rgba(59, 130, 246, 0.3);
        }}
        
        .card.spending {{
            border-left: 4px solid var(--success);
        }}
        
        .card.expensive {{
            border-left: 4px solid var(--danger);
            background: linear-gradient(135deg, var(--bg-secondary), rgba(239, 68, 68, 0.05));
        }}
        
        .card .amount {{
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--success);
            margin-bottom: 10px;
        }}
        
        .card.expensive .amount {{
            color: var(--danger);
        }}
        
        .card .title {{
            font-weight: 600;
            font-size: 1.05rem;
            margin-bottom: 12px;
            color: var(--text-primary);
            line-height: 1.4;
        }}
        
        .card .summary {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-bottom: 15px;
            display: none;
            line-height: 1.5;
            padding: 12px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
        }}
        
        .card.expanded .summary {{
            display: block;
        }}
        
        .card .meta {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }}
        
        .tag {{
            background: var(--bg-card);
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 0.8rem;
            color: var(--text-secondary);
        }}
        
        .btn {{
            padding: 8px 16px;
            border-radius: 8px;
            border: none;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        
        .btn-primary {{
            background: var(--accent);
            color: white;
        }}
        
        .btn-primary:hover {{
            background: #2563eb;
            transform: scale(1.02);
        }}
        
        .btn-secondary {{
            background: var(--bg-card);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }}
        
        .btn-secondary:hover {{
            background: #475569;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 60px 20px;
            color: var(--text-secondary);
        }}
        
        .empty-state h3 {{
            font-size: 1.3rem;
            margin-bottom: 10px;
            color: var(--text-primary);
        }}
        
        footer {{
            text-align: center;
            padding: 40px 20px;
            color: var(--text-secondary);
            font-size: 0.85rem;
            border-top: 1px solid var(--border);
            margin-top: 50px;
        }}
        
        footer a {{
            color: var(--accent);
            text-decoration: none;
        }}
        
        footer a:hover {{
            text-decoration: underline;
        }}
        
        @media (max-width: 768px) {{
            .container {{ padding: 15px; }}
            header {{ padding: 30px 0; }}
            header h1 {{ font-size: 1.6rem; }}
            .stat {{ padding: 12px 18px; }}
            .stat-value {{ font-size: 1.5rem; }}
            .card {{ padding: 18px; }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>📋 Boletín Oficial de la Provincia de Buenos Aires</h1>
            <p class="subtitle">Análisis con Inteligencia Artificial para Transparencia Ciudadana</p>
            <p class="subtitle">Boletín N° {data.get('numero_boletin', '-')} - {data.get('fecha_display', '-')}</p>
            <p class="update-time">Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{len(gastos)}</div>
                    <div class="stat-label">💰 Gastos / Contrataciones</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(otras)}</div>
                    <div class="stat-label">📜 Otras Normas</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(data['normas'])}</div>
                    <div class="stat-label">📊 Total Analizadas</div>
                </div>
            </div>
        </div>
    </header>
    
    <div class="container">
        <div class="tabs">
            <button class="tab active" onclick="showTab('gastos', this)">💰 Gastos y Contrataciones</button>
            <button class="tab" onclick="showTab('normas', this)">📜 Otras Disposiciones</button>
        </div>
        
        <div id="tab-gastos" class="tab-content active">
            <div class="card-grid">
                {generate_cards(gastos, is_spending=True) if gastos else '<div class="empty-state"><h3>No se encontraron gastos</h3><p>No hay resoluciones de gasto o contratación en este boletín.</p></div>'}
            </div>
        </div>
        
        <div id="tab-normas" class="tab-content">
            <div class="card-grid">
                {generate_cards(otras[:80], is_spending=False) if otras else '<div class="empty-state"><h3>No se encontraron normas</h3><p>No hay otras normas disponibles.</p></div>'}
            </div>
        </div>
    </div>
    
    <footer>
        <p>Datos del <a href="https://boletinoficial.gba.gob.ar" target="_blank">Boletín Oficial de la Provincia de Buenos Aires</a></p>
        <p>Normas indexadas en <a href="https://normas.gba.gob.ar" target="_blank">normas.gba.gob.ar</a></p>
        <p style="margin-top: 10px;">Resúmenes generados con IA mediante <a href="https://huggingface.co/spaces/amd/gpt-oss-120b-chatbot" target="_blank">AMD GPT-OSS 120B</a></p>
    </footer>
    
    <script>
        function showTab(tab, btn) {{
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById('tab-' + tab).classList.add('active');
            btn.classList.add('active');
        }}
        
        function toggleCard(card) {{
            card.classList.toggle('expanded');
        }}
    </script>
</body>
</html>'''
    
    os.makedirs(DATA_DIR, exist_ok=True)
    
    with open(os.path.join(DATA_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    
    with open(os.path.join(DATA_DIR, 'data.json'), 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ HTML generado en {DATA_DIR}/index.html")

def generate_cards(norms, is_spending=False):
    """Generate HTML cards for norms"""
    cards = []
    for n in norms:
        card_class = 'card'
        if is_spending:
            if n.get('monto', 0) > 100000000:
                card_class = 'card expensive'
            else:
                card_class = 'card spending'
        
        amount_html = ''
        if n.get('monto_fmt'):
            amount_html = f'<div class="amount">{n["monto_fmt"]}</div>'
        elif is_spending:
            amount_html = '<div class="amount" style="color: var(--text-secondary); font-size: 1rem;">Monto no especificado</div>'
        
        cards.append(f'''
            <div class="{card_class}">
                {amount_html}
                <div class="title">{html_escape(n.get('resumen_corto', n['nombre'][:80]))}</div>
                <div class="summary">{html_escape(n.get('resumen_largo', n.get('sumario', '')[:300]))}</div>
                <div class="meta">
                    <span class="tag">{n.get('tipo', 'Norma')}</span>
                    <span class="tag">{n.get('organismo', '')[:30]}</span>
                    <button class="btn btn-secondary" onclick="toggleCard(this.closest('.card'))">Ver más</button>
                    <a href="{n.get('url', '#')}" target="_blank" class="btn btn-primary">📄 Ver documento</a>
                </div>
            </div>
        ''')
    
    return '\n'.join(cards)

def html_escape(text):
    """Escape HTML special characters"""
    if not text:
        return ""
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;'))

def main():
    print("=" * 55)
    print("🏛️  Boletín Oficial PBA - Scraper con IA")
    print("=" * 55)
    
    start_time = time.time()
    
    # Get bulletin info
    print("\n📋 Obteniendo información del boletín...")
    bulletin_num, bulletin_date = get_latest_bulletin_info()
    
    # Try different scraping methods
    norms = scrape_with_known_ids()
    
    if len(norms) < 5:
        print("   Intentando búsqueda alternativa...")
        norms.extend(search_recent_norms_by_year())
    
    if not norms:
        print("❌ No se encontraron normas. Generando sitio vacío...")
        norms = [{
            'nombre': 'Sitio en construcción',
            'sumario': 'Por favor, intente más tarde.',
            'url': BOLETIN_HOME,
            'tipo': 'Info',
            'organismo': 'Sistema',
            'resumen_corto': 'El sitio está siendo actualizado',
            'resumen_largo': 'El sistema está en proceso de obtener las normas del último boletín. Por favor, vuelva a visitar en unas horas.',
            'tiene_gasto': False
        }]
    else:
        # Initialize AI client
        print("\n🤖 Conectando con servicio de IA...")
        try:
            client = Client("amd/gpt-oss-120b-chatbot")
            norms = process_norms_with_ai(norms, client)
        except Exception as e:
            print(f"⚠️ Error conectando IA: {e}")
            # Add basic summaries
            for n in norms:
                n['resumen_corto'] = n['nombre'][:80]
                n['resumen_largo'] = n.get('sumario', '')[:300]
                amounts = extract_amounts(n.get('full_text', ''))
                n['tiene_gasto'] = bool(amounts) or is_spending_related(n.get('full_text', ''))
                if amounts:
                    n['monto'] = max(amounts)
                    n['monto_fmt'] = f"${n['monto']:,.0f}"
    
    # Build final data
    data = {
        'numero_boletin': bulletin_num or '-',
        'fecha_display': bulletin_date,
        'fecha': datetime.now().strftime('%Y-%m-%d'),
        'normas': norms
    }
    
    # Generate HTML
    generate_html(data)
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  Tiempo total: {elapsed:.1f} segundos")
    print("✅ ¡Proceso completado!")

if __name__ == "__main__":
    main()
