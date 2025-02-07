import csv
import requests
import os
from collections import defaultdict
from pathlib import Path

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

with open('datos.csv','r',encoding='utf-8') as datos_csv:
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

    for org in la_ley[T_DECRETO]:
        print(f"org={org} ->")
        for n in la_ley[T_DECRETO][org]:
            ley = la_ley[T_DECRETO][org][n] 
            #print(f"ley={ley}")
            url = ley['texto_actualizado'] or ley['texto_original']
            org_path = Path(f"infoleg_html/{str(ley['id_infoleg'])[-1]}/")
            org_path.mkdir(parents=True, exist_ok=True)
            path = org_path/f"{ley['id_infoleg']}.html"
            if not path.exists():
                print(f"download {url} -> {path}...")
                with requests.get(url) as html:
                    with open(path,'w',encoding="utf-8") as f_html:
                        f_html.write(html.text)


        

