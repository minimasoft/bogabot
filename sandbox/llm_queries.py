# Copyright Minimasoft (c) 2025

from pathlib import Path
import json
import gzip

### Context data

law_ref = load_json_gz(Path('../data/leyes_ref.json.gz'))
decree_ref = load_json_gz(Path('../data/decretos_ref.json.gz'))

with open("../data/mapa_context.txt","r",encoding="utf-8") as fp:
    mapa_context = f"Estos son los cargos conocidos al dia de hoy, solo para utilizar de referencia:\n```{fp.read()}\n```\n\n"

### Useful stuff

class BadLLMData(Exception):
    pass

class NotEnoughData(Exception):
    pass

### LLM queries

def brief_query(target_norm: str) -> str:
    prompt = """
Crear un resumen bajo las siguientes consignas:
- Siempre menciona a todos los firmantes por apellido.
- Si es una designacion de personal solo menciona a las personas involucradas y sus roles.
- Si hay datos tabulados solo menciona su existencia. 
- Solo escribe el resumen, no ofrezcas mas ayuda, la respuesta es final.
- El resumen debe tener como mucho 500 caracteres.

Norma a resumir:
```
"""
    prompt += target_norm + "\n```\n"

    context = mapa_context

    return context + prompt


def tags_query(target_norm: str) -> str:
    prompt = """Clasifica la norma con los siguientes tags:
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
[["#anses", 0.8],["#presidencial", 1.0]]

Norma a clasificar:
```
"""
    prompt += target_norm + "\n```\n"

    return prompt

def tags_filter(llm_output: str) -> list:
    try:
        json_value = json.loads(llm_output)
    except Exception as e:
        print(e.with_traceback())
        raise BadLLMData
    tag_limit = 0.5 # Ignore low confidence tags
    useful_tags = [ tag[0] for tag in json_value if float(tag[1]) > tag_limit ]
    return useful_tags


def appointment_selector(task_data: map) -> bool:
    if 'tags' not in task_data:
        raise NotEnoughData
    return '#designacion' in task_data['tags']

def appointment_query(target_norm:str) -> str:
    prompt = """Crear una lista en formato JSON (sin markdown)  de las personas que fueron designadas a un cargo con los siguientes campos:
- 'name': nombre completo de la persona designada.
- 'gov_id': número de DNI or CUIT de la persona designada.
- 'gov_section': el departamento, ministerio o sección del gobierno.
- 'position': cargo al que la persona es designada.
- 'position_start': fecha en la que la persona asume el cargo, el formato debe ser YYYY-MM-DD.
- 'position_duration_days': si la designación es temporal el número de dias, sino 0.
Si no hay la respuesta es una lista vacía '[]', si hay elementos directamente la lista.

Norma:
```
"""
    prompt += target_norm + "\n```\n"

    return prompt

def appointment_filter(llm_output: str) -> list:
    try:
        json_value = json.loads(llm_output)
    except Exception as e:
        print(e.with_traceback())
        raise BadLLMData
    return json_value


def resign_selector(task_data: map) -> bool:
    if 'tags' not in task_data:
        raise NotEnoughData
    return '#renuncia' in task_data['tags']

def resign_query(target_norm: str) -> str:
    prompt = """Crear una lista en formato JSON (sin markdown) de las personas que renuncian a un cargo con los siguientes campos:
- 'name': nombre completo de la persona que renuncia.
- 'gov_id': número de DNI or CUIT de la persona que renuncia.
- 'gov_section': el departamento, ministerio o sección del gobierno.
- 'position': cargo al que la persona renuncia.
- 'position_end': fecha en la que la persona renuncia al cargo, el formato debe ser YYYY-MM-DD.

Si no hay la respuesta es una lista vacía '[]', si hay elementos directamente la lista.

Norma:
```
"""
    prompt += target_norm + "\n```\n"
    return prompt

def resign_filter(llm_output: str) -> list:
    try:
        json_value = json.loads(llm_output)
    except Exception as e:
        print(e.with_traceback())
        raise BadLLMData
    return json_value


def law_ref_query(target_norm: str) -> str:
    prompt = """Crear una lista en formato JSON de numeros de ley (sin artículos).
Reglas:
- Solo deben ser leyes: ignorar decretos, resoluciones, comunicaciones u otro tipo de normas.
- Sin comentarios.
- Sin repetidos. 
- En caso de no existir leyes mencionadas la respuesta es un vector vacio: '[]'.
- No incluir markdown para indicar que es JSON.

Por ejemplo si se mencionan las leyes Ley N 12.443 y Ley 5.542:
['12443'], ['5542']

Norma a analizar:
```
"""
    prompt += target_norm + "\n```\n"

    return prompt

def law_ref_filter(llm_output: str) -> list:
    try:
        json_value = json.loads(llm_output)
    except Exception as e:
        print(e.with_traceback())
        raise BadLLMData
    return json_value 

def decree_ref_query(target_norm: str) -> str:
    prompt = """Crear una lista en JSON de decretos mencionados:
Reglas:
- El formato es '123/2024' donde '123' es el numero de decreto y '2024' el año. 
- El año puede estar con 2 dígitos o 4 dígitos, conservar el formato con el que está escrito.
- No incluir leyes, resoluciones ni otro tipo de normas.
- Sin comentarios.
- Sin repetidos.
- Si no se mencionan decretos la respuesta es una lista vacia: '[]'.
- No incluir markdown para indicar que es JSON.

Por ejemplo si se mencionan los decretos Decreto N° 1023/01 y Decreto N° 1382 de fecha 9 de agosto de 2012:
['1023/01', '1382/2012']

Norma:
```
"""

    prompt += target_norm + "\n```\n"
    return prompt

def decree_ref_filter(llm_output: str) -> list:
    try:
        json_value = json.loads(llm_output)
    except Exception as e:
        print(e.with_traceback())
        raise BadLLMData
    return json_value 


def resolution_ref_query(target_norm:str) -> str:
    prompt = """Crear una lista en JSON de resoluciones mencionadas:
Reglas:
- Si se menciona la entidad de la resolución incluirla.
- Mencionar el número de resolución y el año con el formato '123/2002' si el número es 123 y el año 2002.
- No incluir leyes, decretos ni otro tipo de normas.
- Sin comentarios.
- Sin repetidos.
- Si no se mencionan resoluciones la respuesta es una lista vacia: '[]'.
- No incluir markdown para indicar que es JSON.

Por ejemplo si se mencionan las resolucioens Resolución N° 15541/25 y la Resolución ENARGAS N° 2747/2002
['15541/25', 'ENARGAS 2747/2002']

Norma:
```
"""
    prompt += target_norm + "\n```\n"
    return prompt

def resolution_ref_filter(llm_output: str) -> list:
    try:
        json_value = json.loads(llm_output)
    except Exception as e:
        print(e.with_traceback())
        raise BadLLMData
    return json_value 


def analysis_selector(task_data: map) -> bool:
    return False

def analysis_query(task_data: map) -> str:
    # TODO cambiar todos los query para usar task_data y armar el mega-contexto.
    return ""
