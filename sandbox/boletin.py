from bs4 import BeautifulSoup
from pathlib import Path
import json
import gzip
import requests
import markdown


def load_json_gz(fpath):
    with gzip.open(fpath,'rt',encoding='utf-8') as jf:
        return json.load(jf)

MODEL="huihui_ai/qwen2.5-1m-abliterated:14b"

law_ref = load_json_gz(Path('../data/leyes_ref.json.gz'))
decree_ref = load_json_gz(Path('../data/decretos_ref.json.gz'))

def query_ollama(model_name, context, query, max_context=512*1024):
    try:
        # Construct the Ollama API URL
        base_url = "http://localhost:11434/api/generate"

        # Prepare the prompt by combining context and query
        prompt = f"Context:\n{context}\n\nQuery:\n{query}"

        # Prepare the payload for the request
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
        }

        # Make the POST request to Ollama API
        response = requests.post(base_url, json=payload)
        response.raise_for_status()

        # Extract and return the generated text from the response
        return response.json()["response"]

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while communicating with Ollama API: {e}")
        return None


def get_details(url, session, do_brief=True, do_ref=True):
    print(f"fetching details from {url}")
    with session.get(url) as r:
        html_content = r.text

    soup = BeautifulSoup(html_content, 'html.parser')

    cuerpo_div = soup.find('div', {'id': 'cuerpoDetalleAviso'}).contents[1]
    body = str(cuerpo_div) if cuerpo_div else None  # Preserve the HTML structure

    data = {
        "full_text": body
    }
    
    if do_brief:
        response = query_ollama(MODEL, body, "Crea un resumen del siguiente texto, siempre menciona a todos los firmantes que son los nombres al final, si es una designacion solo menciona a las personas involucradas y sus roles, si hay datos tabulados solo menciona su existencia, no ofrezcas mas ayuda, la respuesta es final, el resumen no debe tener mas de 600 caracteres, ignorar tags HTML.")
        refined_response = query_ollama(MODEL, response, "Corrije errores ortograficos en el siguiente texto. Si no hay errores solo copia el texto. No ofrezcas mas ayuda ni hagas aclaraciones")
        data['brief'] = refined_response
        print(response)
    
    if do_ref:
        raw_law_list = query_ollama(MODEL, body, "Crea una lista en JSON de numeros de ley (sin articulos). No incluyas decretos, ni resoluciones. Sin comentarios, sin repetidos y sin detalles. Si no se mencionan '[]'. No incluyas markdown para indicar que es JSON")
        print(raw_law_list)
        try:
            law_list = json.loads(raw_law_list)
        except json.decoder.JSONDecodeError:
            law_list = []
            print('json error')

        raw_decree_list = query_ollama(MODEL, body, "Crea una lista en JSON de decretos mencionados, el formato es '\"123/2024\"' donde '123' es el numero de decreto y '2024' el año. No incluyas leyes, ni resoluciones. Sin comentarios, sin repetidos y sin detalles. Si no se mencionan '[]', No incluyas markdown para indicar que es JSON")
        print(raw_decree_list)
        try:
            decree_list = json.loads(raw_decree_list)
        except json.decoder.JSONDecodeError:
            decree_list = []
            print('json error')
        raw_constitution_list = query_ollama(MODEL, body, "Crea una lista en JSON de numero de articulo de la constitucion mencionados. No incluyas decretos, ni resoluciones. Sin comentarios, sin repetidos y sin detalles. Si no se mencionan '[]'. No incluyas markdown para indicar que es JSON")
        print(raw_constitution_list)
        try:
            constitution_list = json.loads(raw_constitution_list)
        except json.decoder.JSONDecodeError:
            constitution_list = []
            print('json error')

        data['ref'] = "<ul>\n"
        if len(law_list) > 0:
            data['ref'] += "<li>Leyes:<ul>\n"
            for law in law_list:
                data['ref'] += f"<li>{law}"
                if str(law) in law_ref:
                    data['ref']+= "<ul>\n"
                    matches = law_ref[str(law)]
                    for year in matches:
                        for law_data in matches[year]:
                            data['ref'] += f"<li>infoleg {law} - {year} - <a href=https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id={law_data['id']}>{law_data['id']}</a>: {law_data['resumen']}</li>\n"
                    data['ref'] += "</ul>"
                data['ref'] += "</li>\n"
            data['ref'] += "</li></ul>\n"
        if len(decree_list) > 0:
            data['ref'] += "<li>Decretos:<ul>\n"
            for dec in decree_list:
                data['ref'] += f"<li>{dec}"
                if '/' in dec:
                    dec_n = dec.split('/')[0]
                    dec_y = dec.split('/')[1]
                    if str(dec_n) not in decree_ref:
                        if len(dec_n) == 4 and dec_n.startswith('20'):
                            dec_n = dec_n[2:]
                    if str(dec_n) in decree_ref:
                        decree_n = decree_ref[str(dec_n)]
                        if str(dec_y) in decree_n:
                            data['ref']+= "<ul>\n"
                            matches = decree_n[str(dec_y)]
                            for decree in matches:
                                data['ref'] += f"<li>infoleg {dec} - <a href=https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id={decree['id']}>{decree['id']}</a>: {decree['resumen']}</li>\n"
                            data['ref'] += "</ul>"
                data['ref'] += "</li>\n"
            data['ref'] += "</li></ul>\n"
        if len(constitution_list) > 0:
            data['ref'] += "<li>Art. Constitucion:<ul>\n"
            for art in constitution_list:
                data['ref'] += f"<li>{art}</li>\n"
            data['ref'] += "</li></ul>\n"
        data['ref'] += "</ul>\n"

        print(data['ref'])

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

    results = []

    # Find all div elements with class "col-md-12"
    for item_div in soup.find_all('div', {'class': 'col-md-12'}):
        # Extract the link from the anchor tag
        a_tag = item_div.find('a')
        if a_tag:
            link = a_tag['href']
        else:
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

        # Append the extracted data as a dictionary
        element = {
            'subject': subject,
            'link': link,
            'name': name,
            'official_id': official_id,
            'data': get_details(f"https://www.boletinoficial.gob.ar{link}", session)
        }
        results.append(element)
        print(f"\n\n-- subject: {subject} name: {name} id: {official_id}")

    return results


results = get_day(7,2,2025)
print("\n\nSaving JSON just in case...\n\n")
with open('output.json', 'w', encoding='utf-8') as json_file:
    json.dump(results, json_file, indent=4, ensure_ascii=False)

#with open('output.json', 'r', encoding='utf-8') as json_file:
#    results = json.load(json_file)

with open('output.html','w') as html_o:
    html_o.write("""<html>
<head>
<meta charset="UTF-8">
<link href='https://fonts.googleapis.com/css?family=Noto Sans Mono' rel='stylesheet'>
<style>
body {
    font-family: 'Noto Sans Mono';
}
</style>
</head>
<body>""")
    for result in results:
        html_o.write(f"<hr><br><h2>{result['subject']}</h2><h3>{result['name']}</h3><h3>{result['official_id']}</h3>desde: <a href=https://www.boletinoficial.gob.ar{result['link']}>{result['link']}</a>\n")
        if 'brief' in result['data']:
            brief = result['data']['brief']
            brief = markdown.markdown(brief)        
            html_o.write(f"<br><br><details><summary>Resumen</summary>{brief}</details>\n")
        if 'ref' in result['data']:
            ref = result['data']['ref']
            ref = markdown.markdown(ref)        
            html_o.write(f"<br><details><summary>Referencias</summary>{ref}</details>\n")
        html_o.write(f"<br><details><summary>Texto original</summary>{result['data']['full_text']}</details>\n")
    html_o.write('\n</body></html>\n')

