import csv
import requests
import os
from collections import defaultdict
from bs4 import BeautifulSoup
from pathlib import Path
import json
import gzip
from random import random

def load_json_gz(fpath):
    with gzip.open(fpath,'rt',encoding='utf-8') as jf:
        return json.load(jf)

def dict_list():
    return defaultdict(list)
decretos_ref = defaultdict(dict_list)
leyes_ref = defaultdict(dict_list)
reso_ref = defaultdict(dict_list)

leyes_ref_old = load_json_gz(Path('../data/leyes_ref.json.gz'))
decretos_ref_old = load_json_gz(Path('../data/decretos_ref.json.gz'))

T_DECRETO = "Decreto"
T_RESOLUCION = "Resolución"
T_DISPOSICION = "Disposición"
T_LEY = "Ley"
T_DECISION_A = "Decisión Administrativa"
T_COMUNICACION = "Comunicación"
T_NOTA = "Nota Externa"
T_ACTA = "Acta"
T_INSTRUCCION = "Instrucción"

m_t_n = {
        T_DECRETO: "DE",
        T_RESOLUCION: "RE",
        T_DISPOSICION: "DI",
        T_DECISION_A: "DA",
        T_COMUNICACION: "CO",
        T_LEY: "LE",
        T_NOTA: "NO",
        T_ACTA: "AC",
        T_INSTRUCCION : "IN",
        }

def dict_dict():
    return defaultdict(dict)

with open('../data/datos.csv','r',encoding='utf-8') as datos_csv:
    csv_reader = csv.reader(datos_csv)
    heads = next(csv_reader)
    la_ley = defaultdict(dict_dict)
    for norma_csv in csv_reader:
        numero_norma = norma_csv[heads.index("numero_norma")]
        if numero_norma == "S/N":
            continue
        id_infoleg = norma_csv[heads.index("id_norma")]
        tipo_norma = norma_csv[heads.index("tipo_norma")]
        fecha_sancion = norma_csv[heads.index("fecha_sancion")]
        fecha_boletin = norma_csv[heads.index("fecha_boletin")]
        organismo_origen = norma_csv[heads.index("organismo_origen")]
        titulo_resumido = norma_csv[heads.index("titulo_resumido")]
        titulo_sumario = norma_csv[heads.index("titulo_sumario")]
        texto_resumido = norma_csv[heads.index("texto_resumido")]
        observaciones = norma_csv[heads.index("observaciones")]
        texto_original = norma_csv[heads.index("texto_original")]
        texto_actualizado = norma_csv[heads.index("texto_actualizado")]
        modificada_por = norma_csv[heads.index("modificada_por")]
        modifica_a = norma_csv[heads.index("modifica_a")]
        norma = {
                "id_infoleg": int(id_infoleg),
                "numero_norma": numero_norma,
                "tipo_norma": tipo_norma,
                "fecha_sancion": fecha_sancion,
                "fecha_boletin": fecha_boletin,
                "organismo_origen": organismo_origen,
                "titulo_resumido": titulo_resumido,
                "titulo_sumario": titulo_sumario,
                "texto_resumido": texto_resumido,
                "observaciones": observaciones,
                "texto_original": texto_original,
                "texto_actualizado": texto_actualizado,
                "modificada_por": modificada_por,
                "modifica_a": modifica_a
        }


        if tipo_norma != T_LEY:
            numero_bien = f"{numero_norma}/{fecha_sancion[:7]}"
        else:
            numero_bien = f"{numero_norma}"
        
        if texto_original == '' and texto_actualizado == '':
            continue

        la_ley[tipo_norma][organismo_origen][numero_bien] = norma


    #keys = list(la_ley.keys())
    #for key in keys:
    #    meta_keys = list(la_ley[key])
    #    print(f"{key}: {meta_keys}")

    def get_links(html):
        links = []
        soup = BeautifulSoup(html, 'html.parser')
        for link_tag in soup.find_all('a'):
            href = str(link_tag.get('href'))
            tag='/infolegInternet/verNorma.do'
            if(href.startswith(tag)):
                link = href[href.index('?id=')+4:]
                print(f"link: {link}")
                links.append(link)
        return links

    def get_mods(ley):
        mods = []
        mod_by = []
        if ley['modifica_a'] != '' and int(ley['modifica_a']) > 0:
            print(f"checking mods for {ley['id_infoleg']}")
            with requests.get(f"https://servicios.infoleg.gob.ar/infolegInternet/verVinculos.do?modo=1&id={ley['id_infoleg']}") as r:
                mods = get_links(r.text)
        if ley['modificada_por'] != '' and int(ley['modificada_por']) > 0:
            print(f"checking mod_by for {ley['id_infoleg']}")
            with requests.get(f"https://servicios.infoleg.gob.ar/infolegInternet/verVinculos.do?modo=2&id={ley['id_infoleg']}") as r:
                mod_by = get_links(r.text)
        return (mods, mod_by)

    for org in la_ley[T_DECRETO]:
        print(f"org={org} ->")
        for n in la_ley[T_DECRETO][org]:
            ley = la_ley[T_DECRETO][org][n] 
            print(f"dec={ley['numero_norma']} de {ley['fecha_sancion']}")
            url = ley['texto_actualizado'] or ley['texto_original']
            org_path = Path(f"../data/infoleg_html/{str(ley['id_infoleg'])[-1]}/")
            org_path.mkdir(parents=True, exist_ok=True)
            path = org_path/f"{ley['id_infoleg']}.html"
            if not path.exists():
                print(f"download {url} -> {path}...")
                with requests.get(url) as html:
                    with open(path,'w',encoding="utf-8") as f_html:
                        f_html.write(html.text)
            n_a = str(ley['numero_norma'])
            n_b = str(int(ley['fecha_sancion'][:4]))

            if str(n_a) in decretos_ref_old and n_b in decretos_ref_old[n_a]:
                print("xxxx")
                d = next(d_i for d_i in decretos_ref_old[n_a][n_b] if d_i['id'] == ley['id_infoleg'])

            if d is None:
                mods, mod_by = get_mods(ley)
                d = {
                        'id': ley['id_infoleg'],
                        'fecha': ley['fecha_sancion'],
                        'titulo': ley['titulo_sumario'],
                        'resumen': ley['texto_resumido'],
                        'orga': ley['organismo_origen'],
                        'mods': mods,
                        'mod_by': mod_by,
                    }
            decretos_ref[n_a][n_b].append(d)

    with open('decretos_ref_new.json', 'w', encoding='utf-8') as f:
        json.dump(decretos_ref, f, ensure_ascii=False, sort_keys=True, indent=2)
            
    
    for org in la_ley[T_LEY]:
        print(f"org={org} ->")
        for n in la_ley[T_LEY][org]:
            ley = la_ley[T_LEY][org][n] 
            print(f"ley={ley['numero_norma']}")
            url = ley['texto_actualizado'] or ley['texto_original']
            org_path = Path(f"../data/infoleg_html/{str(ley['id_infoleg'])[-1]}/")
            org_path.mkdir(parents=True, exist_ok=True)
            path = org_path/f"{ley['id_infoleg']}.html"
            if not path.exists():
                print(f"download {url} -> {path}...")
                with requests.get(url) as html:
                    with open(path,'w',encoding="utf-8") as f_html:
                        f_html.write(html.text)
            n_a = str(ley['numero_norma'])
            n_b = str(int(ley['fecha_sancion'][:4]))
            l = None
            if n_a in leyes_ref_old and n_b in leyes_ref_old[n_a]:
                print('xxx')
                l = next(l_i for l_i in leyes_ref_old[n_a][n_b] if l_i['id'] == ley['id_infoleg'])

            if l is None:
                mods, mod_by = get_mods(ley)
                l = {
                        'id': ley['id_infoleg'],
                        'fecha': ley['fecha_sancion'],
                        'titulo': ley['titulo_sumario'],
                        'resumen': ley['texto_resumido'],
                        'orga': ley['organismo_origen'],
                        'mods': mods,
                        'mod_by': mod_by,
                    }

            leyes_ref[n_a][n_b].append(l)



    with open('leyes_ref_new.json', 'w', encoding='utf-8') as f:
        json.dump(leyes_ref, f, ensure_ascii=False, sort_keys=True, indent=2)
        

    for org in la_ley[T_RESOLUCION]:
        print(f"org={org} ->")
        for n in la_ley[T_RESOLUCION][org]:
            reso = la_ley[T_RESOLUCION][org][n] 
            print(f"reso={reso['numero_norma']}")
            url = reso['texto_actualizado'] or reso['texto_original']
            org_path = Path(f"../data/infoleg_html/{str(reso['id_infoleg'])[-1]}/")
            org_path.mkdir(parents=True, exist_ok=True)
            path = org_path/f"{reso['id_infoleg']}.html"
            if not path.exists():
                print(f"download {url} -> {path}...")
                with requests.get(url) as html:
                    with open(path,'w',encoding="utf-8") as f_html:
                        f_html.write(html.text)
            mods, mod_by = get_mods(reso)
            reso_ref[reso['numero_norma']][int(reso['fecha_sancion'][:4])].append(
                {
                    'id': reso['id_infoleg'],
                    'fecha': reso['fecha_sancion'],
                    'titulo': reso['titulo_sumario'],
                    'resumen': reso['texto_resumido'],
                    'orga': reso['organismo_origen'],
                    'mods': mods,
                    'mod_by': mod_by,
                }
            )
            # Save progress
            if random() > 0.82:
                with open('reso_ref_new.json', 'w', encoding='utf-8') as f:
                    json.dump(reso_ref, f, ensure_ascii=False, sort_keys=True, indent=2)

    with open('reso_ref_new.json', 'w', encoding='utf-8') as f:
        json.dump(reso_ref, f, ensure_ascii=False, sort_keys=True, indent=2)
