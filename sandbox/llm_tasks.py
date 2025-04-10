# Copyright Minimasoft (c) 2025

from helpers import load_json_gz
from pathlib import Path
from bs4 import BeautifulSoup
import json
import gzip
from global_config import gconf
from file_db import FileDBRecord


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

_constitucion_ref = None
def constitucion_ref():
    global _constitucion_ref
    if _constitucion_ref is None:
        _constitucion_ref = load_json_gz(gconf("DATA_PATH") / 'constitucion_nacional.txt')
    return _constitucion_ref

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


def normalize_llm_json(llm_output: str) -> str:
    return llm_output.replace("'",'"').replace('```json','').replace('```','')

def json_llm(llm_output: str) -> dict:
    try:
        normal_output = normalize_llm_json(llm_output)
        return json.loads(normal_output)
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
        self.multi_step = False

    def _select(self, obj: dict) -> bool:
        return True

    def _query(self, obj: dict) -> [str, dict]:
        raise NotImplementedError

    def _filter(self, llm_output:str) -> str:
        return llm_output

    def check(self, obj: FileDBRecord) -> bool:
        if obj.m().d()['type'] != self.obj_type:
            raise BadObjectType
        return self._select(obj)

    def generate(self, obj: FileDBRecord) -> FileDBRecord:
        obj_type = obj.m().d()['type']
        obj_key = obj.m().d()['key']
        return FileDBRecord(gconf("LLM_TASK_META"), {
            'task_key': f"{obj_type}[{obj[obj_key]}].{self.obj_attr}",
            'prompt': self._query(obj),
            'target_type': obj_type,
            'target_key': obj_key,
            'target_key_v': obj[obj_key],
            'target_attr': self.obj_attr,
            'multi_step': self.multi_step
        })

    def post_process(self, llm_output:str, obj: FileDBRecord) -> dict:
        obj[self.obj_attr] = self._filter(llm_output)
        return obj


def dummy_selector(norm: dict) -> bool:
    return True


### LLM queries

class BriefTask(LLMTask):
    def __init__(self):
        self.max_len = 500
        self.tolerance = 1.2
        return super().__init__('norm', 'brief')

    def _query(self, norm: dict) -> str:
        prompt = f"""
Crear un resumen bajo las siguientes consignas:
- Menciona a todos los firmantes por apellido.
- Si es una designacion de personal solo menciona a las personas involucradas y sus roles.
- Si hay datos tabulados solo menciona su existencia. 
- Solo escribe el resumen, no ofrezcas mas ayuda, la respuesta es final.
- El resumen debe tener máximo {self.max_len} caracteres.
- No mencionar que es un resumen.

Norma a resumir:
```
"""
        prompt += norm_text(norm) + "\n```\n"

        context = mapa_context

        return context + prompt
    
    def _filter(self, llm_output:str) -> str:
        if len(llm_output) > self.max_len*self.tolerance:
            print("too long!")
            raise BadLLMData
        return llm_output


class TagsTask(LLMTask):
    def __init__(self):
        super().__init__('norm', 'tags')

    def _query(self, norm: dict) -> str:
        prompt = """Clasifica la norma con los siguientes tags:
- #designacion : solo se utiliza para nombramientos y designaciones transitorias de una persona en particular a un cargo.
- #renuncia : solo se utiliza para renuncias a un cargo de una persona en particular.
- #cese: solo se utiliza para cuando se dispone el cese de una persona en un cargo.
- #inscripcion: solo se utiliza cuando se inscribe a una persona en una matricula profesional.
- #multa : solo se utiliza para penalizaciones economicas o multas aplicadas a personas o empresas especificas.
- #laboral : solo se utiliza para normas y resoluciones que actualizan el salario o las reglas de trabajo para un gremio o grupo de trabajadores.
- #anses : solo se utiliza para normas que reglamentan o modifican temas relacionados con la seguridad social, el anses o las pensiones.
- #tarifas : solo se utiliza para normas que actualizan, o regulan tarifas de servicios y bienes de consumo.
- #recurso_administrativo :  solo se utiliza cuando se acepta o rechaza un recurso presentado por una persona en particular.
- #cierre: solo se utiliza para cuando se trata de cerrar alguna entidad u organismo.
- #subasta : solo se utiliza para cuando se trata de una subasta.
- #edicto: solo se utiliza para edictos.
- #presidencial : solo se utiliza cuando firma el presidente Milei, no cuando firma su hermana Karina.

La respuesta debe ser una lista en formato JSON de los de tags, sin markdown, si no hay tags la respuesta es [] (la lista vacia) y para #anses y #presidencial la respuesta es:
["#anses", "#presidencial"]

Norma a clasificar:
```
"""
        prompt += norm_text(norm) + "\n```\n"

        return prompt

    def _filter(self, llm_output: str) -> list:
        json_value = json_llm(llm_output)
        return json_value


class AppointmentTask(LLMTask):
    def __init__(self):
        super().__init__('norm', 'appoint_list')

    def _select(self, norm: dict) -> bool:
        if 'tags' not in norm:
            raise NotEnoughData
        return norm['official_id'] != "" and '#designacion' in norm['tags']

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
        json_value = json_llm(llm_output)
        return json_value


class ResignTask(LLMTask):
    def __init__(self):
        super().__init__('norm', 'resign_list')

    def _select(self, norm: dict) -> bool:
        if 'tags' not in norm:
            raise NotEnoughData
        return norm['official_id'] != "" and ('#renuncia' in norm['tags'] or '#cese' in norm['tags'])

    def _query(self, norm: dict) -> str:
        prompt = """Crear una lista en formato JSON (sin markdown) de las personas que renuncian o cesan un cargo con los siguientes campos:
- 'name': nombre completo de la persona que renuncia.
- 'gov_id': número de DNI or CUIT de la persona que renuncia.
- 'gov_section': el departamento, ministerio o sección del gobierno.
- 'position': cargo al que la persona renuncia o cesa.
- 'position_end': fecha en la que la persona renuncia o cesa el cargo, el formato debe ser YYYY-MM-DD.

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
        tag_filter = all(tag not in ['#designacion','#renuncia', '#cese', '#inscripcion', '#edicto', '#recurso_administrativo'] for tag in norm['tags']) or '#presidencial' in norm['tags']
        return norm['official_id'] != "" and tag_filter

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
        results = {}
        for value in json_llm(llm_output):
            result = {}
            clean = "".join(filter(lambda c: c.isdigit(), str(value)))
            if clean in results:
                continue
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
            results[clean] = result
        return list(results.values())


class DecreeRefTask(LLMTask):
    def __init__(self):
        super().__init__('norm', 'decree_ref')

    def _select(self, norm: dict) -> bool:
        if 'tags' not in norm:
            raise NotEnoughData
        tag_filter = all(tag not in ['#designacion','#renuncia', '#cese', '#inscripcion', '#edicto', '#recurso_administrativo'] for tag in norm['tags']) or '#presidencial' in norm['tags']
        return norm['official_id'] != "" and tag_filter

    def _query(self, norm: dict) -> str:
        prompt = """Crear una lista en JSON de decretos mencionados con las siguientes reglas:
- El formato es '123/2024' donde '123' es el numero de decreto y '2024' el año. 
- El año puede estar con 2 dígitos o 4 dígitos, ambos son formatos válidos.
- No incluir leyes, resoluciones ni otras normas, solo decretos.
- Sin comentarios.
- Si no se mencionan decretos la respuesta es una lista vacia: '[]'.
- No incluir markdown para indicar que es JSON.
- No pensarlo demasiado.

Por ejemplo si se mencionan los decretos Decreto N° 1023/01 y Decreto N° 1382 de fecha 9 de agosto de 2012:
["1023/01", "1382/2012"]

Norma a analizar:
```
"""
        prompt += norm_text(norm) + "\n```\n"
        return prompt

    def _filter(self, llm_output: str) -> list:
        results = {}
        for value in json_llm(llm_output):
            result = {}
            clean = "".join(filter(lambda c: c.isdigit() or c=='/', str(value)))
            result['llm'] = value
            if clean in results:
                continue
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
            results[clean] = result
        return list(results.values())


class ResolutionRefTask(LLMTask):
    def __init__(self):
        super().__init__('norm', 'resolution_ref')

    def _select(self, norm: dict) -> bool:
        if 'tags' not in norm:
            raise NotEnoughData
        tag_filter = all(tag not in ['#designacion','#renuncia', '#cese', '#edicto', '#recurso_administrativo'] for tag in norm['tags'])
        return norm['official_id'] != "" and tag_filter
    
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
        tag_filter = all(tag not in ['#edicto','#designacion','#cese','#inscripcion','#renuncia','#multa', '#recurso_administrativo'] for tag in norm['tags'])# or '#presidencial' in norm['tags']
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
        all_contexts = {}
        for infoleg_id in infolegs:
            infoleg_file = Path(f"../data/infoleg_html/{infoleg_id[-1]}/{infoleg_id}.html")
            if infoleg_file.exists():
                with open(infoleg_file, 'r', encoding='utf-8') as infoleg_html:
                    info_soup = BeautifulSoup(infoleg_html, 'html.parser')
                    all_contexts[infoleg_id] = info_soup.text

        official_id = norm['official_id'].split(' ')[0]
        prompt = "A continuación las leyes y decretos de contexto, el comienzo de cada una se marca con !CONTEXT_START y el final con !CONTEXT_END.\n"
        for context_id in all_contexts.keys():
            prompt += f"!CONTEXT_START\n{all_contexts[context_id]}\n!CONTEXT_END\n"
        prompt += f"Esta es la norma nueva a analizar ({official_id}):\n```{norm_text(norm)}\n```\n"
        prompt += f"Crear un análisis mostrando como la nueva norma afecta a las normas anteriores. Incluir análisis de derechos afectados y posibles abusos con la nueva normativa."
        if len(prompt) > 128000*3.5: #TODO: improve heuristic for map-reduce
            prompts = {}
            for context_id in all_contexts.keys():
                prompts[context_id] = "A continuacion reglamentación de contexto, empieza en !CONTEXT_START y termina en !CONTEXT_END.\n"
                prompts[context_id] += f"!CONTEXT_START\n{all_contexts[context_id]}\n!CONTEXT_END\n"
                prompts[context_id] += f"Crear un resumen de la norma de contexto teniendo en cuenta puntos que podrían ser importantes para la siguiente norma, delimitada entre !NORM_START y !NORM_END.\n"
                prompts[context_id] += f"!NORM_START\n{norm_text(norm)}\n!NORM_END\n"
            prompts['reducer'] = "A continuación el contexto:\n```\n_reducer_\n```\n"
            prompts['reducer'] += f"Esta es la nueva norma ({official_id}):\n```{norm_text(norm)}\n```\n"
            prompts['reducer'] += "Crear un análisis de impacto de la nueva norma. En caso de ser necesario explicar como la nueva norma afecta a las anteriores. Mencionar también derechos afectados y posibles abusos con la nueva norma.\n"
            return prompts
        else:
            return prompt


class ConstitutionalTask(LLMTask):
    def __init__(self):
        super().__init__('norm', 'constitutional')

    def _select(self, norm: dict) -> bool:
        if 'tags' not in norm:
            raise NotEnoughData
        tag_filter = all(tag not in ['#edicto','#designacion','#cese','#inscripcion','#renuncia','#multa', '#recurso_administrativo'] for tag in norm['tags']) or '#presidencial' in norm['tags']
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
        prompt = constitucion_ref()
        prompt += f"\nLa nueva norma:\n```\n{norm_text(norm)}\n```\n"
        prompt += "Determinar si la nueva norma es constitucional. Si resulta constitucional responder brevemente, si tiene irregularidades explicarlas e indicar los posibles conflictos con la constitución."
        return prompt


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
        ConstitutionalTask(),
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
