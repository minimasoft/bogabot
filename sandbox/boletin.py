# Copyright Minimasoft 2025
from bs4 import BeautifulSoup
from pathlib import Path
import json
import gzip
import requests
import markdown
import sys


def load_json_gz(fpath):
    with gzip.open(fpath,'rt',encoding='utf-8') as jf:
        return json.load(jf)

MODEL="huihui_ai/qwen2.5-1m-abliterated:14b"
#MODEL="qwq:32b"

law_ref = load_json_gz(Path('../data/leyes_ref.json.gz'))
decree_ref = load_json_gz(Path('../data/decretos_ref.json.gz'))
with open("../data/mapa_context.txt","r",encoding="utf-8") as fp:
    mapa_context = f"Estos son los cargos conocidos:\n'''{fp.read()}\n'''\n\n"


prompt_token_total = 0
eval_token_total = 0
gpu_time_total = 0


def query_ollama(model_name, context, query, max_context=512*1024):
    try:
        global prompt_token_total
        global eval_token_total
        global gpu_time_total
        # Construct the Ollama API URL
        base_url = "http://localhost:11434/api/generate"

        # Prepare the prompt by combining context and query
        prompt = f"Contexto:\n'''\n{context}\n'''\n\nTarea:\n'''\n{query}\n'''\n"

        # Prepare the payload for the request
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                # Bogabot personality 1.0
                "temperature": 0.4,
                "seed": 42, # guaranteed to be random
                "top_k": 23,
                "top_p": 0.5,
            }
        }

        # Make the POST request to Ollama API
        response = requests.post(base_url, json=payload)
        response.raise_for_status()

        # Extract and return the generated text from the response
        data = response.json()
        prompt_token_total += data['prompt_eval_count']
        eval_token_total += data['eval_count']
        gpu_time_total += data['total_duration']
        llm_response = data["response"]
        end_of_think = llm_response.find("</think>")
        if end_of_think > 0:
            llm_response = llm_response[(end_of_think+8):]
        return llm_response

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while communicating with Ollama API: {e}")
        return None


def get_details(url, session, do_brief=True, do_ref=True):
    print(f"fetching details from {url}")
    with session.get(url) as r:
        html_content = r.text


    soup = BeautifulSoup(html_content, 'html.parser')

    for script in soup(['script', 'meta', 'link', 'style']):
        script.decompose()  # Removes the tag completely from the tree

    cuerpo_div = soup.find('div', {'id': 'cuerpoDetalleAviso'}).contents[1]
    body = str(cuerpo_div) if cuerpo_div else None  # Preserve the HTML structure
    

    data = {
        "full_text": body
    }
    
    if do_brief:
        response = query_ollama(MODEL, mapa_context + body, "Crea un resumen del siguiente texto, siempre menciona a todos los firmantes que son los nombres al final, si es una designacion solo menciona a las personas involucradas y sus roles, si hay datos tabulados solo menciona su existencia, no ofrezcas mas ayuda, la respuesta es final, el resumen no debe tener mas de 600 caracteres, ignorar tags HTML.")
        refined_response = query_ollama(MODEL, response, "Corrije errores ortograficos en el siguiente texto. Si no hay errores solo copia el texto. No ofrezcas mas ayuda ni hagas aclaraciones")
        data['brief'] = refined_response
        print(response)
    
    if do_ref:
        raw_law_list = query_ollama(MODEL, body, "Crear una lista en formato JSON de numeros de ley (sin articulos). Limitaciones: - Solo deben ser leyes, ignorar decretos, resoluciones, comunicaciones u otro tipo de normas. - Sin comentarios. - Sin repetidos - Sin detalles - En caso de no existir leyes mencionadas la respuesta es un vector vacio: '[]'. - No incluir markdown para indicar que es JSON.")
        print(raw_law_list)
        try:
            law_list = json.loads(raw_law_list)
        except json.decoder.JSONDecodeError:
            law_list = []
            print(f"JSON error in law_list !!!!!!!!! {raw_law_list}")

        raw_decree_list = query_ollama(MODEL, body, "Crear una lista en JSON de decretos mencionados, el formato es '\"123/2024\"' donde '123' es el numero de decreto y '2024' el año. Reglas: - No incluir leyes, resoluciones ni otro tipo de normas. - Sin comentarios. - Sin repetidos - Sin detalles. - Si no se mencionan decretos la respuesta es un vector vacio: '[]'. - No incluir markdown para indicar que es JSON. No pensarlo demasiado.")
        print(raw_decree_list)
        try:
            decree_list = json.loads(raw_decree_list)
        except json.decoder.JSONDecodeError:
            decree_list = []
            print(f"JSON error in decree_list !!!!!!!!!: {raw_decree_list}")

        data['ref'] = "<ul>\n"
        info_legs = set()  # lol
        if len(law_list) > 0:
            data['ref'] += "<li>Leyes:<ul>\n"
            for law in law_list:
                law_str = str(law).replace('.','')
                if law_str.find('/') > 0:
                    continue  # Dumb AI puts decree as law
                data['ref'] += f"<li>{law_str}"
                if law_str in law_ref:
                    data['ref']+= "<ul>\n"
                    matches = law_ref[law_str]
                    for year in matches:
                        for law_data in matches[year]:
                            data['ref'] += f"<li>infoleg {law_str} - {year} - <a href=https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id={law_data['id']}>{law_data['id']}</a>: {law_data['resumen']}</li>\n"
                            info_legs.add(str(law_data['id']))
                    data['ref'] += "</ul>"
                data['ref'] += "</li>\n"
            data['ref'] += "</ul></li>\n"
        if len(decree_list) > 0:
            data['ref'] += "<li>Decretos:<ul>\n"
            for dec in decree_list:
                dec_str = str(dec)
                data['ref'] += f"<li>{dec_str}"
                if '/' in dec_str:
                    dec_n = dec_str.split('/')[0]
                    dec_y = dec_str.split('/')[1]
                    if dec_n not in decree_ref:
                        if len(dec_n) == 4 and dec_n.startswith('20'):
                            dec_n = dec_n[2:]
                    if dec_n in decree_ref:
                        decree_n = decree_ref[dec_n]
                        if dec_y in decree_n:
                            data['ref']+= "<ul>\n"
                            matches = decree_n[str(dec_y)]
                            for decree in matches:
                                data['ref'] += f"<li>infoleg {dec_str} - <a href=https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id={decree['id']}>{decree['id']}</a>: {decree['resumen']}</li>\n"
                                info_legs.add(str(decree['id']))
                            data['ref'] += "</ul>"
                        elif dec_y in ['25','2025']:
                            data['ref'] += " _TODO_preload_2025_dec_"
                data['ref'] += "</li>\n"
            data['ref'] += "</ul></li>\n"
        data['ref'] += "</ul>\n"

        print(data['ref'])
        # now let's make a killer query with all references :D
        full_context = []
        for infoleg_id in info_legs:
            infoleg_file = Path(f"../data/infoleg_html/{infoleg_id[-1]}/{infoleg_id}.html")
            if infoleg_file.exists():
                with open(infoleg_file, 'r', encoding='utf-8') as infoleg_html:
                    info_soup = BeautifulSoup(infoleg_html, 'html.parser')
                    for div in info_soup.find_all('div'):
                        text = div.text
                        if len(text.strip())>1:
                            full_context.append(text)
                    print(f"context loaded: {infoleg_file}")
            else:
                print(f"context not found: {infoleg_file}")
        context_as_text = ""
        for context in full_context:
            context_as_text += context
            context_as_text += "\n\n-------\n\n"
        context_as_text += mapa_context
        context_as_text += "Norma actual:\n"
        context_as_text += body
        print("-------------------------------------------------------")
        print(f"Tamaño del contexto a enviar: {len(context_as_text)} bytes")
        print("-------------------------------------------------------")
        analysis = query_ollama(MODEL, context_as_text, "Explicar como la norma actual (la ultima en la lista) afecta o impacta sobre las normas anteriores. En caso de modificar leyes anteriores explicar los beneficios afectados de la ley anterior. En caso de no tener impacto o afectarlas no hace falta explicar.")
        data['analysis'] = analysis
        print(analysis)
    return data


def get_day(day:int ,month:int , year:int):
    session = requests.Session()
    from requests.adapters import HTTPAdapter, Retry
    retries = Retry(total=4, backoff_factor=0.3, status_forcelist=[500,502,503,504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        })
    session.get("https://www.boletinoficial.gob.ar/")
    fecha = f"{day:02}-{month:02}-{year}"
    session.get(f"https://www.boletinoficial.gob.ar/edicion/actualizar/{fecha}")
    with session.get("https://www.boletinoficial.gob.ar/seccion/primera") as r:
        html_content = r.text

    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    results = {}

    # Find all div elements with class "col-md-12"
    for item_div in soup.find_all('div', {'class': 'col-md-12'}):
        # Extract the link from the anchor tag
        a_tag = item_div.find('a')
        if a_tag:
            link = a_tag['href']
        else:
            continue
        if link in results:
            continue

        # Extract subject from p with class "item"
        subject_p = item_div.find('p', class_='item')
        if subject_p:
            subject = subject_p.get_text(strip=True)
        else:
            continue

        # Extract name and official_id from the first two p.item-detalle
        detalle_ps = item_div.find_all('p', class_='item-detalle')
        name_small = detalle_ps[0].find('small') if detalle_ps else None
        name = name_small.get_text(strip=True) if name_small else ''

        if len(detalle_ps) > 1:
            official_id_small = detalle_ps[1].find('small')
            official_id = official_id_small.get_text(strip=True) if official_id_small else ''
        else:
            official_id = ''

        do_ref = True
        if len(official_id) < 1 or official_id[:2] in ["DI","RE"]:
            do_ref = False
        # Append the extracted data as a dictionary
        element = {
            'subject': subject,
            'link': link,
            'name': name,
            'official_id': official_id,
            'data': get_details(f"https://www.boletinoficial.gob.ar{link}", session, do_ref=do_ref)
        }
        results[link] = element
        print(f"\n\n-- subject: {subject} name: {name} id: {official_id}")
    global prompt_token_total
    global eval_token_total
    global gpu_time_total
    print(f"\n----------------------------------------\nTotal gpu time: {gpu_time_total} total prompt tokens: {prompt_token_total} total eval tokens: {eval_token_total}\n")
    return results


# Get BO and generate metadata
day= int(sys.argv[1])
month= int(sys.argv[2])
year= int(sys.argv[3])
json_file_path = Path(f"bo{year-2000}{month:02}{day:02}.json")

if json_file_path.exists() == False:
    results = get_day(day,month,year)
    with open(json_file_path, "w", encoding='utf-8') as json_file:
        json.dump(results, json_file, indent=2, ensure_ascii=False)
else: # Loads existing data if available
    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        results = json.load(json_file)

# Gen HTML

with open(f"bo{year-2000}{month:02}{day:02}.html",'w') as html_o:
    html_o.write("""<html>
<head>
<meta charset="UTF-8">
<style>
@font-face {
  font-family: 'Noto Sans Mono';
  font-style: normal;
  font-weight: 400;
  font-stretch: 100%;
  src: url(/NotoSansMonoLatin.woff2) format('woff2');
  unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD;
}

body {
    font-family: 'Noto Sans Mono';
    font-size: 16px;
}

table {
  border: 1px solid black;
  border-collapse: collapse;
  width: 100%;
  max-width: 1000px;
}

td {
  border: 1px solid black;
  border-collapse: collapse;
  vertical-align: top;
  text-align: left;
  padding: 10px;
}

</style>
</head>
<body>
<img src=bogabanner.png></img>
<h2>Agregado de la sección primera del bolet&iacute;n oficial fecha """)
    html_o.write(f"{day}/{month}/{year}</h2>")
    html_o.write("""
    <table>
    <tbody>""")
    for result in results.values():
        html_o.write(f"<tr>\n<td>\n")
        html_o.write(f"<details><summary><b>{result['subject']}  -  {result['official_id'] or result['name']}</b></summary><hr>via: <a href=https://www.boletinoficial.gob.ar{result['link']}>{result['link']}</a>\n")
        if 'brief' in result['data']:
            brief = result['data']['brief']
            brief = markdown.markdown(brief)        
            html_o.write(f"<p>{brief}</p>\n")
        if 'ref' in result['data']:
            ref = result['data']['ref']
            ref = markdown.markdown(ref)        
            html_o.write(f"<details><summary><b>Referencias</b></summary>{ref}</details>\n")
        if 'analysis' in result['data']:
            analysis = result['data']['analysis']
            analysis = markdown.markdown(analysis)        
            html_o.write(f"<details><summary><b>Análisis de bogabot</b></summary>{analysis}</details>\n")
        html_o.write(f"<details><summary><b>Texto original</b></summary>{result['data']['full_text']}</details>\n")
        html_o.write(f"</div></details>\n</td>\n</tr>\n")
    html_o.write('\n</tbody></table></body></html>\n')
