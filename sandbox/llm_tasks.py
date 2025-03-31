# Copyright Minimasoft (c) 2025

from helpers import load_json_gz
from pathlib import Path
from bs4 import BeautifulSoup
from global_config import gconf
from file_db import FileDBRecord
import json
import gzip


### Lazy context ref

_law_ref = None
def law_ref():
    global _law_ref
    if _law_ref is None:
        _law_ref = load_json_gz(gconf("DATA_PATH") / 'leyes_ref.json.gz')
    return _law_ref

_decree_ref = None
def decree_ref():
    global _decree_ref
    if _decree_ref is None:
        _decree_ref = load_json_gz(gconf("DATA_PATH") / 'decretos_ref.json.gz')
    return _decree_ref

_reso_ref = None
def reso_ref():
    global _reso_ref
    if _reso_ref is None:
        _reso_ref = load_json_gz(gconf("DATA_PATH") / 'reso_ref.json.gz')
    return _reso_ref


with open(gconf("DATA_PATH") / "mapa_context.txt", "r", encoding="utf-8") as fp:
    mapa_context = f"Solo para contexto estos son los cargos conocidos al 20 de Marzo de 2025:\n```{fp.read()}\n```\n\n"

### Useful stuff

def norm_text(norm: dict):
    return norm['full_text'].replace('<p>','').replace('</p>','\n')


class BadLLMData(Exception):
    pass

class NotEnoughData(Exception):
    pass

class BadObjectType(Exception):
    pass


def json_llm(llm_output: str) -> dict:
    try:
        return json.loads(llm_output)
    except Exception as e:
        print(f"error at json decode {e}:\n{llm_output}\n{'-'*40}")
        # let's retry something else:
        final= llm_output.find("inal answer")
        if final > 0:
            try:
                print('*'*80)
                print("TRYING FIX!")
                return json.loads(llm_output[final:].split('\n')[-1])
            except Exception as ee:
                pass
        raise BadLLMData



class LLMTask():
    def __init__(self, obj_type: str, obj_attr: str):
        self.obj_type = obj_type
        self.obj_attr = obj_attr

    def _select(self, obj: dict) -> bool:
        return True

    def _query(self, obj: dict) -> str:
        raise NotImplementedError

    def _filter(self, llm_output:str) -> str:
        return llm_output

    def check(self, obj: dict, meta: dict) -> bool:
        if meta['type'] != self.obj_type:
            raise BadObjectType
        return self._select(obj)

    def generate(self, obj: dict, meta: dict) -> FileDBRecord:
        return FileDBRecord(gconf("LLM_TASK_META"), {
            'task_key': f"{meta['type']}[{obj[meta['key']]}].{self.obj_attr}",
            'prompt': self._query(obj),
            'target_type': meta['type'],
            'target_key': meta['key'],
            'target_key_v': obj[meta['key']],
            'target_attr': self.obj_attr,
        })

    def post_process(self, llm_output:str, obj: dict) -> dict:
        obj[self.obj_attr] = self._filter(llm_output)
        return obj


def dummy_selector(norm: dict) -> bool:
    return True


### LLM queries

class BriefTask(LLMTask):
    def __init__(self):
        return super().__init__('norm', 'brief')

    def _query(self, norm: dict) -> str:
        prompt = """
Crear un resumen bajo las siguientes consignas:
- Siempre menciona a todos los firmantes por apellido.
- Si es una designacion de personal solo menciona a las personas involucradas y sus roles.
- Si hay datos tabulados solo menciona su existencia. 
- Solo escribe el resumen, no ofrezcas mas ayuda, la respuesta es final.
- El resumen debe tener como mucho 500 caracteres.
- No mencionar que es un resumen.

Norma a resumir:
```
"""
        prompt += norm_text(norm) + "\n```\n"

        context = mapa_context

        return context + prompt


class TagsTask(LLMTask):
    def __init__(self):
        super().__init__('norm', 'tags')

    def _query(self, norm: dict) -> str:
        prompt = """Clasifica la norma con los siguientes tags:
- #designacion : solo se utiliza para nombramientos, designaciones transitorias y promociones de una persona en particular
- #renuncia : solo se utiliza para renuncias.
- #multa : solo se utiliza para penalizaciones economicas o multas aplicadas a personas o empresas especificas.
- #laboral : solo se utiliza para normas y resoluciones que actualizan el salario o las reglas de trabajo para un gremio o grupo de trabajadores.
- #anses : solo se utiliza para normas que reglamentan o modifican temas relacionados con la seguridad social, el anses o las pensiones.
- #tarifas : solo se utiliza para normas que actualizan, o regulan tarifas de servicios.
- #administrativo : solo se utiliza para cuando se acepta o rechaza un recurso jerarquico de un expediente administrativo presentado por un una persona en particular. No usar para trámites administrativos ministeriales o de entes de control.
- #cierre: solo se utiliza para cuando se trata de cerrar alguna entidad u organismo.
- #subasta : solo se utiliza para cuando se trata de una subasta.
- #edicto: solo se utiliza para edictos.
- #presidencial : solo se utiliza cuando firma el presidente Milei.

La respuesta debe ser una lista en formato JSON de los de tags acompañados de su probabilidad de 1.0 (seguro), 0.8 (casi seguro), 0.6 (probable), 0.3 (poco probable) a 0.0 (inexistente), sin markdown, si no hay tags la respuesta es [] (la lista vacia) y para #anses 0.8 y #presidencial 1.0 la respuesta es:
[["#anses", 0.8],["#presidencial", 1.0]]

Nota que la respuesta es sin indicaciones de formato json en markdown. Debe ser solo el json.

Norma a clasificar:
```
"""
        prompt += norm_text(norm) + "\n```\n"

        return prompt

    def _filter(self, llm_output: str) -> list:
        json_value = json_llm(llm_output.replace('json','').replace('```',''))
        tag_limit = 0.5 # Ignore low confidence tags
        useful_tags = [ tag[0] for tag in json_value if float(tag[1]) > tag_limit ]
        return useful_tags


class AppointmentTask(LLMTask):
    def __init__(self):
        super().__init__('norm', 'appoint_list')

    def _select(self, norm: dict) -> bool:
        if 'tags' not in norm:
            raise NotEnoughData
        return '#designacion' in norm['tags']

    def _query(self, norm: dict) -> str:
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
        prompt += norm_text(norm) + "\n```\n"

        return prompt

    def _filter(self, llm_output: str) -> list:
        json_value = json_llm(llm_output.replace('json','').replace('```',''))
        return json_value


class ResignTask(LLMTask):
    def __init__(self):
        super().__init__('norm', 'resign_list')

    def _select(self, norm: dict) -> bool:
        if 'tags' not in norm:
            raise NotEnoughData
        return '#renuncia' in norm['tags']

    def _query(self, norm: dict) -> str:
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
        prompt += norm_text(norm) + "\n```\n"
        return prompt

    def _filter(self, llm_output: str) -> list:
        json_value = json_llm(llm_output.replace('json','').replace('```',''))
        return json_value

class LawRefTask(LLMTask):
    def __init__(self):
        super().__init__('norm', 'law_ref')

    def _select(self, norm: dict) -> bool:
        if 'tags' not in norm:
            raise NotEnoughData
        tag_filter = all(tag not in ['#designacion','#renuncia', '#edicto'] for tag in norm['tags'])
        return tag_filter

    def _query(self, norm: dict) -> str:
        prompt = """Crear una lista en formato JSON de numeros de ley (sin artículos).
Reglas:
- Solo deben ser leyes: ignorar decretos, resoluciones, comunicaciones u otro tipo de normas.
- Sin comentarios.
- En caso de no existir leyes mencionadas la respuesta es un vector vacio: '[]'.
- No incluir markdown para indicar que es JSON.
- No pensarlo demasiado.

Por ejemplo si se mencionan las leyes Ley N 12.443 y Ley 5.542:
["12443", "5542"]

Norma a analizar:
```
"""
        prompt += norm_text(norm) + "\n```\n"

        return prompt

    def _filter(self, llm_output: str) -> list:
        results = []
        for value in json_llm(llm_output.replace('```','').replace('json','').replace("'",'"')):
            result = {}
            clean = "".join(filter(lambda c: c.isdigit(), str(value)))
            result['llm'] = value
            result['ref'] = clean
            infolegs = []
            if clean in law_ref():
                matches = law_ref()[clean]
                for year in matches:
                    for infoleg_law in matches[year]:
                        infolegs.append(str(infoleg_law['id']))
                if len(infolegs) > 0:
                    result['infolegs'] = infolegs 
            results.append(result)
        print(results) # debug
        return results


class DecreeRefTask(LLMTask):
    def __init__(self):
        super().__init__('norm', 'decree_ref')

    def _select(self, norm: dict) -> bool:
        if 'tags' not in norm:
            raise NotEnoughData
        tag_filter = all(tag not in ['#designacion','#renuncia', '#edicto'] for tag in norm['tags'])
        return tag_filter

    def _query(self, norm: dict) -> str:
        prompt = """Crear una lista en JSON de decretos mencionados:
Reglas:
- El formato es '123/2024' donde '123' es el numero de decreto y '2024' el año. 
- El año puede estar con 2 dígitos o 4 dígitos, conservar el formato con el que está escrito.
- No incluir leyes, resoluciones ni otro tipo de normas.
- Sin comentarios.
- Si no se mencionan decretos la respuesta es una lista vacia: '[]'.
- No incluir markdown para indicar que es JSON.
- No pensarlo demasiado.

Por ejemplo si se mencionan los decretos Decreto N° 1023/01 y Decreto N° 1382 de fecha 9 de agosto de 2012:
["1023/01", "1382/2012"]

Norma:
```
"""
        prompt += norm_text(norm) + "\n```\n"
        return prompt

    def _filter(self, llm_output: str) -> list:
        results = []
        for value in json_llm(llm_output.replace('```','').replace('json','').replace("'",'"')):
            result = {}
            clean = "".join(filter(lambda c: c.isdigit() or c=='/', str(value)))
            result['llm'] = value
            infolegs = []
            if '/' in clean:
                dec_n, dec_y = clean.split('/')
                if len(dec_y) == 2:
                    if int(dec_y) < 30: #TODO: 1930 cap remove
                        dec_y = "20"+dec_y
                    else:
                        dec_y = "19"+dec_y
                result['ref'] = f"{dec_n}/{dec_y}"
                if dec_n in decree_ref():
                    decs = decree_ref()[dec_n]
                    if dec_y in decs:
                        for infoleg_dec in decs[dec_y]:
                            infolegs.append(str(infoleg_dec['id']))
                if len(infolegs) > 0:
                    result['infolegs'] = infolegs 
            results.append(result)
        print(results) # debug
        return results


class ResolutionRefTask(LLMTask):
    def __init__(self):
        super().__init__('norm', 'resolution_ref')

    def _select(self, norm: dict) -> bool:
        if 'tags' not in norm:
            raise NotEnoughData
        tag_filter = all(tag not in ['#designacion','#renuncia', '#edicto'] for tag in norm['tags'])
        return tag_filter
    
    def _query(self, norm: dict) -> str:
        prompt = """Crear una lista en JSON de resoluciones mencionadas:
Reglas:
- Si se menciona la entidad de la resolución incluirla.
- Mencionar el número de resolución y el año con el formato '123/2002' si el número es 123 y el año 2002.
- No incluir leyes, decretos ni otro tipo de normas.
- Sin comentarios.
- Si no se mencionan resoluciones la respuesta es una lista vacia: '[]'.
- No incluir markdown para indicar que es JSON.

Por ejemplo si se mencionan las resolucioens Resolución N° 15541/25 y la Resolución ENARGAS N° 2747/2002
['15541/25', 'ENARGAS 2747/2002']

Norma:
```
"""
        prompt += norm_text(norm) + "\n```\n"
        return prompt

    def _filter(self, llm_output: str) -> list:
        result = []
        for value in json_llm(llm_output):
            result.append(value.strip().replace('.',''))
        return result


class AnalysisTask(LLMTask):
    def __init__(self):
        super().__init__('norm', 'analysis')

    def _select(self, norm: dict) -> bool:
        if 'tags' not in norm:
            raise NotEnoughData
        if 'law_ref' not in norm:
            raise NotEnoughData
        if 'decree_ref' not in norm:
            raise NotEnoughData
        tag_filter = all(tag not in ['#edicto','#designacion','#renuncia','#multa'] for tag in norm['tags'])
        subjects_out = [
            "BANCO CENTRAL",
            "BANCO DE LA NACI",
            "ADUANERO",
            "ASOCIATIVISMO"
        ]
        subjects_filter = all([
            norm['subject'].find(subject) == -1
            for subject in subjects_out
        ])
        return norm['official_id'] != "" and tag_filter and subjects_filter

    def _query(self, norm: dict) -> str:
        infolegs = set()
        for ref in norm['law_ref']:
            if 'infolegs' in ref:
                for infoleg in ref['infolegs']:
                    infolegs.add(infoleg)
        for ref in norm['decree_ref']:
            if 'infolegs' in ref:
                for infoleg in ref['infolegs']:
                    infolegs.add(infoleg)
        print(f"trying to load: {list(infolegs)}")
        full_context = []
        for infoleg_id in infolegs:
            infoleg_file = Path(f"../data/infoleg_html/{infoleg_id[-1]}/{infoleg_id}.html")
            if infoleg_file.exists():
                with open(infoleg_file, 'r', encoding='utf-8') as infoleg_html:
                    info_soup = BeautifulSoup(infoleg_html, 'html.parser')
                    full_context.append(info_soup.text)
        context_as_text = "A continuacion reglamentación de contexto, empieza en !CONTEXT_START y termina en !CONTEXT_END.\n\n!CONTEXT_START\n"
        for context in full_context:
            context_as_text += context
            context_as_text += "\n\n"
        context_as_text += "!CONTEXT_END\n"
        prompt = """Explicar como la norma actual (a continuación entre !NORM_START y !NORM_END) afecta o impacta sobre las normas anteriores.
En caso de modificar leyes anteriores explicar los beneficios afectados de la ley anterior.
Mencionar derechos perdidos y posibles abusos con la nueva normativa.
!NORM_START
"""
        prompt += norm_text(norm) + "\n!NORM_END\n"
        result = context_as_text + prompt
        print(f"Created mega context of: {len(result)}")
        return result


def get_llm_task_map() -> dict:
    norm_tasks = [
        BriefTask(),
        TagsTask(),
        AppointmentTask(),
        ResignTask(),
        LawRefTask(),
        DecreeRefTask(),
    #    ResolutionRefTask(),
        AnalysisTask(),
    ]

    return {
        'norm' : {
            task.obj_attr : task
            for task in norm_tasks
        }
    }


def __test__llm_tasks__():
    task_map = get_llm_task_map()
    print(task_map)


if __name__ == '__main__':
    __test__llm_tasks__()
