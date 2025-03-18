# Copyright Minimasoft (c) 2025
from bs4 import BeautifulSoup
from pathlib import Path
import json
import gzip
import requests
from requests.adapters import HTTPAdapter, Retry
import markdown
import sys
import os


def load_json_gz(fpath):
    with gzip.open(fpath,'rt',encoding='utf-8') as jf:
        return json.load(jf)


law_ref = load_json_gz(Path('../data/leyes_ref.json.gz'))
decree_ref = load_json_gz(Path('../data/decretos_ref.json.gz'))
with open("../data/mapa_context.txt","r",encoding="utf-8") as fp:
    mapa_context = f"Estos son los cargos conocidos al dia de hoy, solo para utilizar de referencia:\n'''{fp.read()}\n'''\n\n"

tasks_path = Path('../tasks/')
tasks_path.mkdir(exist_ok=True)

results_path = Path('../results/')
results_path.mkdir(exist_ok=True)

ollama_url = "http://localhost:11434"
#ollama_token = "?token="
ollama_token = ""
ollama_test = f"{ollama_url}/{ollama_token}"
ollama_session = requests.Session()
ollama_session.get(ollama_test)


MODEL="qwq:32b"
#MODEL="huihui_ai/qwen2.5-1m-abliterated:14b"

def query_ollama(model_name, context, query, max_context=512*1024):
    try:
        # Construct the Ollama API URL
        base_url = f"{ollama_url}/api/generate"

        # Prepare the prompt by combining context and query
        prompt = f"Contexto:\n'''\n{context}\n'''\n\nTarea:\n'''\n{query}\n'''\n"

        # Prepare the payload for the request
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                # Bogabot personality 1.0
                "temperature": 0.42,
                "seed": 42, # guaranteed to be random
                "top_k": 24,
                "top_p": 0.5,
                "num_ctx": 13231, #3090 max speed
                #"num_ctx": 120000, #40GB+ (h100, rtx6000 ada, etc)
            }
        }

        # Make the POST request to Ollama API
        response = ollama_session.post(base_url, json=payload, verify=False)
        response.raise_for_status()

        # Extract and return the generated text from the response
        data = response.json()
        print(f"""stats:
 - prompt_eval_count: {data['prompt_eval_count']}
 - eval_count:  {data['eval_count']}
 - gpu_time: {data['total_duration']/1000000}""")

        llm_response = data["response"]
        is_thinking = llm_response.find("<think>")
        end_of_think = llm_response.find("</think>")
        if end_of_think > 0:
            llm_response = llm_response[(end_of_think+8):]
        if is_thinking >= 0 and end_of_think < 0:
            print("--------------------------------------------------")
            print("---------THINK OUTPUT ERROR-----:O :O :O----------")
            print("--------------------------------------------------")
            print(f"Input:\n{prompt}\n")
            print("--------------------------------------------------")
            print("------------------------------------------OMG-----")
            print("--------------------------------------------------")
            
        return llm_response

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while communicating with Ollama API: {e}")
        return None


def process_task(task_data, task_name, session, force_analysis=False, force_tags=False, force_brief=False):
    result_path = results_path / task_name
    if result_path.exists():
        print(f"Result already exist: {result_path}")

    url = task_data['data_link']
    # url, do_brief, do_ref
    with session.get(url) as r:
        html_content = r.text

    soup = BeautifulSoup(html_content, 'html.parser')

    for script in soup(['script', 'meta', 'link', 'style']):
        script.decompose()  # Removes the tag completely from the tree

    cuerpo_div = soup.find('div', {'id': 'cuerpoDetalleAviso'}).contents[1]
    body = str(cuerpo_div) if cuerpo_div else None  # Preserve the HTML structure
    

    task_data['full_text'] = body

    if force_brief or 'brief' not in task_data or task_data['brief'] is None:
        response = query_ollama(MODEL, mapa_context + body, "Crea un resumen del siguiente texto, siempre menciona a todos los firmantes que son los nombres al final, si es una designacion solo menciona a las personas involucradas y sus roles, si hay datos tabulados solo menciona su existencia, no ofrezcas mas ayuda, la respuesta es final, el resumen no debe tener mas de 600 caracteres, ignorar tags HTML.")
        #refined_response = query_ollama(MODEL, response, "Corrije errores ortograficos en el siguiente texto. Si no hay errores solo copia el texto. No ofrezcas mas ayuda ni hagas aclaraciones")
        task_data['brief'] = response
        print(f"BRIEF:\n\n{response}\n\n.-.-.\n")

    if force_tags or 'tags' not in task_data:
        response = query_ollama(MODEL, body, """------------
Clasifica la norma anterior con los siguientes tags:
- #designacion : solo se utiliza para nombramientos, designaciones transitorias y promociones de una persona en particular
- #renuncia : solo se utiliza para renuncias.
- #multa : solo se utiliza para penalizaciones economicas o multas aplicadas a personas o empresas especificas.
- #laboral : solo se utiliza para normas y resoluciones que actualizan el salario o las reglas de trabajo para un gremio o grupo de trabajadores.
- #anses : solo se utiliza para normas que reglamentan o modifican temas relacionados con la seguridad social, el anses o las pensiones.
- #tarifas : solo se utiliza para normas que actualizan, o regulan tarifas de servicios.
- #administrativo : solo se utiliza para cuando se acepta o rechaza un recurso jerarquico de un expediente administrativo presentado por un una persona en particular. No usar para trámites administrativos ministeriales o de entes de control.
- #cierre: solo se utiliza para cuando se trata de cerrar alguna entidad u organismo.
- #subasta : solo se utiliza para cuando se trata de una subasta
- #presidencial : solo se utiliza cuando firma el presidente Milei

La respuesta debe ser una lista en formato JSON de los de tags acompañados de su probabilidad de 1.0 (seguro), 0.8 (casi seguro), 0.6 (probable), 0.3 (poco probable) a 0.0 (inexistente), sin markdown, si no hay tags la respuesta es [] (la lista vacia) y para #anses 0.8 y #presidencial 1.0 la respuesta es:
[["#anses", 0.8],["#presidencial", 1.0]]\n""")
        task_data['tags'] = json.loads(response)
        tag_limit = 0.51
        print(task_data['tags'])
        useful_tags = [ tag[0] for tag in task_data['tags'] if float(tag[1]) > tag_limit ]
        task_data['tags'] = useful_tags
    print(task_data['tags'])

    if '#designacion' in task_data['tags'] and 'appointment_list' not in task_data:
        prompt = """Crear una lista en formato JSON (sin markdown)  de las personas que fueron designadas a un cargo con los siguientes campos:
- 'name': nombre completo de la persona designada.
- 'gov_id': número de DNI or CUIT de la persona designada.
- 'gov_section': el departamento, ministerio o sección del gobierno.
- 'position': cargo al que la persona es designada.
- 'position_start': fecha en la que la persona asume el cargo.
- 'position_duration_days': si la designación es temporal el número de dias, sino 0.
"""
        new_pasta = query_ollama(MODEL, body, prompt)
        print(f"appointment_list: {new_pasta}")
        task_data['appointment_list'] = json.loads(new_pasta)

    if '#renuncia' in task_data['tags'] and 'resign_list' not in task_data:
        prompt = """Crear una lista en formato JSON (sin markdown)  de las personas que renuncian a un cargo con los siguientes campos:
- 'name': nombre completo de la persona que renuncia.
- 'gov_id': número de DNI or CUIT de la persona que renuncia.
- 'gov_section': el departamento, ministerio o sección del gobierno.
- 'position': cargo al que la persona renuncia.
- 'position_end': fecha en la que la persona renuncia al cargo.
"""
        ex_pasta = query_ollama(MODEL, body, prompt)
        print(f"resign_list: {new_pasta}")
        task_data['resign_list'] = json.loads(new_pasta)


    if force_analysis is False:
        skip_analysis = any(tag in ["#designacion","#renuncia","#multa","#administrativo"] for tag in task_data['tags'])
        if 'analysis' in task_data and task_data['analysis'] is not None:
            skip_analysis = True
    else:
        skip_analysis = False
    
    if skip_analysis == False: 
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

        task_data['ref'] = "<ul>\n"
        info_legs = set()  # lol
        if len(law_list) > 0:
            task_data['ref'] += "<li>Leyes:<ul>\n"
            for law in law_list:
                law_str = str(law).replace('.','')
                if law_str.find('/') > 0:
                    continue  # Dumb AI puts decree as law
                task_data['ref'] += f"<li>{law_str}"
                if law_str in law_ref:
                    task_data['ref']+= "<ul>\n"
                    matches = law_ref[law_str]
                    for year in matches:
                        for law_data in matches[year]:
                            task_data['ref'] += f"<li>infoleg {law_str} - {year} - <a href=https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id={law_data['id']}>{law_data['id']}</a>: {law_data['resumen']}</li>\n"
                            info_legs.add(str(law_data['id']))
                    task_data['ref'] += "</ul>"
                task_data['ref'] += "</li>\n"
            task_data['ref'] += "</ul></li>\n"
        if len(decree_list) > 0:
            task_data['ref'] += "<li>Decretos:<ul>\n"
            for dec in decree_list:
                dec_str = str(dec)
                task_data['ref'] += f"<li>{dec_str}"
                if '/' in dec_str:
                    dec_n = dec_str.split('/')[0]
                    dec_y = dec_str.split('/')[1]
                    if dec_n not in decree_ref:
                        if len(dec_n) == 4 and dec_n.startswith('20'):
                            dec_n = dec_n[2:]
                    if dec_n in decree_ref:
                        decree_n = decree_ref[dec_n]
                        if dec_y in decree_n:
                            task_data['ref']+= "<ul>\n"
                            matches = decree_n[str(dec_y)]
                            for decree in matches:
                                task_data['ref'] += f"<li>infoleg {dec_str} - <a href=https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id={decree['id']}>{decree['id']}</a>: {decree['resumen']}</li>\n"
                                info_legs.add(str(decree['id']))
                            task_data['ref'] += "</ul>"
                        elif dec_y in ['25','2025']:
                            task_data['ref'] += " _TODO_preload_2025_dec_"
                task_data['ref'] += "</li>\n"
            task_data['ref'] += "</ul></li>\n"
        task_data['ref'] += "</ul>\n"

        print(task_data['ref'])
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
        analysis = query_ollama(MODEL, context_as_text, "Explicar como la norma actual (la ultima en la lista) afecta o impacta sobre las normas anteriores. En caso de modificar leyes anteriores explicar los beneficios afectados de la ley anterior. Mencionar derechos perdidos y posibles abusos con la nueva normativa.")
        task_data['analysis'] = analysis
        print(analysis)

    with open(result_path, 'w', encoding='utf-8') as result_file:
        json.dump(task_data, result_file, indent=2, ensure_ascii=False)


def create_bo_session():
    session = requests.Session()
    retries = Retry(total=4, backoff_factor=0.3, status_forcelist=[500,502,503,504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        })
    return session


def __main__():
    print(f"Bogabot worker pid={os.getpid()} ollama_url={ollama_url}")
    session = create_bo_session()

    if len(sys.argv) > 1:
        running = False
        task_path = Path(sys.argv[1])
        task_name = task_path.name
        with open(task_path, 'r', encoding='utf-8') as task_file:
            task_data = json.load(task_file)
        process_task(task_data, task_name, session, force_analysis=False)
    else:
        running = True

    while running:
        for task_path in tasks_path.glob('*.json'):
            lock_path = Path(str(task_path) + ".lock")
            if lock_path.exists() == False:
                try:
                    with open(lock_path, 'w') as lock_file:
                        print(f"Processing: {lock_path}")
                        lock_file.write(f"{os.getpid()}")
                        with open(task_path, 'r', encoding='utf-8') as task_file:
                            task_data = json.load(task_file)
                            process_task(task_data, task_path.name, session)
                    lock_path.unlink()
                    task_path.unlink()
                except Exception as e:
                    print(f"Error processing {task_path}:\n{e}\n")
                    lock_path.unlink()
                    pass
        if len(list(tasks_path.glob('*.json'))) == 0:
            print("Work not found. Bye o/")
            running = False

if __name__ == '__main__':
    __main__()
