#!/home/user/src/bogabot/venv/bin/python
# Copyright Minimasoft (c) 2025
from pathlib import Path
import json
import markdown
import sys
from global_config import gconf
from file_db import FileDB
from datetime import date, timedelta,datetime
from csv import DictWriter
from time import sleep, time

public_path = Path('../public/')
public_path.mkdir(exist_ok=True)


norm_meta = gconf("NORM_META")
db = FileDB(
    gconf("FILEDB_PATH"),
    gconf("FILEDB_SALT"),
)
last_check_s = 0
all_days = {}
while True:
  check_s = int(time())
  all_norms = list(db.all(norm_meta, last_check_s))
  print(f"all_norms len: {len(all_norms)} check_s: {check_s}")
  last_check_s = check_s

  today = date.today() + timedelta(days=1)
  curr_date = date(2023,12,10)
  while(curr_date <= today):
      day = curr_date.day
      month = curr_date.month
      year = curr_date.year

      html_path = public_path / f"bo{year-2000}{month:02}{day:02}.html"
      json_path = public_path / f"bo{year-2000}{month:02}{day:02}.personal.json"
      csv_path = public_path / f"bo{year-2000}{month:02}{day:02}.designa.csv"
      target_date = f"{year}-{month:02}-{day:02}"
      if target_date in all_days:
        results = all_days[target_date]
      else:
        results = {}
      for norm in filter(lambda n: n['publish_date'] == target_date, all_norms):
        results[norm['ext_id']] = norm

      current_tags = set()
      for norm in results.values():
          if 'tags' in norm:
            for tag in norm['tags']:
                current_tags.add(tag[1:])
      current_tags = [
        tag for tag in ['presidencial','designacion','renuncia','cese','inscripcion','multa','laboral','tarifas','anses','recurso_administrativo','cierre','subasta','edicto'] if tag in current_tags
      ]
      if len(results.values()) > 0:
          all_days[target_date] = results
          skip_write = False
          if html_path.exists() == True:
              html_time = html_path.stat().st_ctime
              result_time = max(map(lambda r: r.e()['time'], results.values())) + 1
              if result_time < html_time:
                  #print(f"Skip write, already up to date")
                  skip_write = True
          if skip_write == False:
              print(f"Writing {len(results)} norms...")
              with open(html_path, 'w') as html_o:
                  html_o.write(f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Agregado del boletín oficial {day:02}/{month:02}/{year}</title>
<meta name="description" content="Resumen, referencias y análisis de los {len(results)} artículos en sección primera del Boletín Oficial de la República Argentina"/>
<meta property="og:url" content="https://hil.ar/bora/bo{(year-2000):02}{month:02}{day:02}.html"/>
<meta property="og:type" content="website"/>
<meta property="og:title" content="Agregado del boletín oficial {day:02}/{month:02}/{year}"/>
<meta property="og:description" content="Resumen, referencias y análisis de los {len(results)} artículos en sección primera del Boletín Oficial de la República Argentina"/>
<meta property="og:image" content="https://hil.ar/bora/meta.jpg"/>
<meta property="twitter:domain" content="hil.ar"/>
<meta property="twitter:url" content="https://hil.ar/bora/bo{(year-2000):02}{month:02}{day:02}.html"/>
<meta property="twitter:card" content="summary_large_image"/>
<meta property="twitter:title" content="Agregado del boletín oficial {day:02}/{month:02}/{year}"/>
<meta property="twitter:description" content="Resumen, referencias y análisis de los {len(results)} artículos en sección primera del Boletín Oficial de la República Argentina"/>
<meta property="twitter:image" content="https://hil.ar/bora/meta.jpg"/>
<meta property="twitter:site" content="@minimasoft"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
""")
                  html_o.write("""<style>
<style>
@font-face {
  font-family: 'Noto Sans Mono';
  font-style: normal;
  font-weight: 400;
  font-stretch: 100%;
  src: url(/NotoSansMonoLatin.woff2) format('woff2');
}

body {
  font-family: 'Noto Sans Mono';
  font-size: 16px;
  margin: 0;
  padding: 2rem 1rem;
  line-height: 1.75;
}

table {
  width: 100%;
  max-width: 960px;
  margin: 2rem auto;
  border-collapse: collapse;
  border-radius: 0.5rem;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

td {
  padding: 1rem;
  vertical-align: top;
  text-align: left;
}

.details_1 {
  margin: 1rem 0;
  border-radius: 0.5rem;
  padding: 1rem;
}

.details_1 > summary {
  cursor: pointer;
  list-style: none;
  font-weight: bold;
}

.details_1 > summary::-webkit-details-marker {
  display: none;
}

.svg_icon {
  width: 1rem;
  height: 1rem;
  vertical-align: middle;
  margin-right: 0.5rem;
}

.json_data {
  padding: 1rem;
  border-radius: 0.5rem;
  overflow-x: auto;
  font-size: 0.875rem;
  margin: 1rem auto;
  max-width: 960px;
}

.bo_norm {
  display: none;
}

""")
                  test = "\n".join([
                    f"#{tag}:checked ~ .c_{tag} {'{'}\n  display: block;\n{'}'}\n"
                    for tag in current_tags
                  ])
                  html_o.write(test)
                  html_o.write("""
#no_tag:checked ~ .c_no_tag {
  display: block;
}

@media (prefers-color-scheme: light) {
  body {
    background-color: #f9fafb;
    color: #111827;
  }

  h2 {
    color: #1f2937;
  }

  a {
    color: #2563eb;
  }

  a:hover {
    color: #1d4ed8;
    text-decoration: underline;
  }

  table {
    background-color: white;
    border: 1px solid #e5e7eb;
  }

  td {
    border: 1px solid #e5e7eb;
  }

  .details_1 {
    background-color: #f3f4f6;
    border: 1px solid #d1d5db;
  }

  .details_1 > summary {
    color: #374151;
  }

  .svg_icon {
    fill: #4b5563;
  }

  .json_data {
    background-color: #fef3c7;
    border: 1px solid #fde68a;
    color: #78350f;
  }
}


@media (prefers-color-scheme: dark) {
  body {
    background-color: #111827;
    color: #e5e7eb;
  }

  h2 {
    color: #facc15;
  }

  a {
    color: #60a5fa;
  }

  a:hover {
    color: #93c5fd;
    text-decoration: underline;
  }

  table {
    background-color: #1f2937;
    border: 1px solid #374151;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  }

  td {
    border: 1px solid #374151;
  }

  .details_1 {
    background-color: #1e293b;
    border: 1px solid #374151;
  }

  .details_1 > summary {
    color: #facc15;
  }

  .svg_icon {
    fill: #facc15;
  }

  .json_data {
    background-color: #0f172a;
    border: 1px solid #334155;
    color: #f1f5f9;
  }
}

</style>
</head>
<body>
<div>
""")
                  html_o.write("""
<table>
<tbody>
<tr><td>
<a href='/bora/'><img src=bannerv02.png></img></a>
</td></tr>
<tr><td>
<h2>Agregado de la sección primera del bolet&iacute;n oficial fecha """)
                  html_o.write(f"{day}/{month}/{year}</h2></td></tr><tr><td>")
                  for tag in current_tags:
                      html_o.write(f"<input type=\"checkbox\" id=\"{tag}\" name=\"tags\" checked><label for=\"{tag}\">#{tag}</label>\n")
                  html_o.write('<input type="checkbox" id="no_tag" name="tags" checked><label for="no_tag">(sin tag)</label>\n')
                  appoint_list = []
                  resign_list = []
                  for result in sorted(results.values(), key=lambda r: r['ext_id']):
                      # Collect data
                      if 'appoint_list' in result:
                          for appointment in result['appoint_list']:
                              appointment['via'] = result['data_link']
                              appointment['norm_official_id'] = result['official_id']
                              appointment['norm_publish_date'] = result['publish_date']
                              appoint_list.append(appointment)
                      if 'resign_list' in result:
                          for resign in result['resign_list']:
                              resign['via'] = result['data_link']
                              resign_list.append(resign)
                      # Write section
                      html_o.write(f"<div id='bo{result['ext_id']}' class='bo_norm ")#><div id='bo{result['ext_id']}' class='bo_norm ")
                      if 'tags' in result and len(result['tags']) > 0:
                          html_o.write(" ".join(f"c_{tag[1:]}" for tag in result['tags']))
                      else:
                          html_o.write("c_no_tag")
                      html_o.write(f"'>\n")
                      html_o.write(f"<details open class=details_1><summary><a href=#bo{result['ext_id']}><img class=svg_icon src='svg/l.svg'></a> <b>{result['subject']}  -  {result['official_id'] or result['name']}</b><br>")
                      if 'tags' in result:
                          html_o.write(f"{' '.join(result['tags'])}")
                      else:
                          html_o.write("procesando tags...")
                      html_o.write(f"</summary><hr>via: <a href={result['data_link']}>{result['data_link']}</a>\n")
                      if 'brief' in result:
                          brief = result['brief']
                          brief = markdown.markdown(brief)        
                          html_o.write(f"<p>{brief}</p>\n")
                      else:
                          html_o.write(f"<p>procesando resumen de bogabot...</p>")
                      if 'ref' in result and result['ref'] is not None:
                          ref = result['ref']
                          ref = markdown.markdown(ref)        
                          html_o.write(f"<details><summary><b>Referencias</b></summary>{ref}</details>\n")

                      refs = ""
                      if 'law_ref' in result and len(result['law_ref']) > 0:
                          refs += f"<li>Leyes:<ul>\n"
                          for ref in result['law_ref']:
                              refs += f"<li>{ref['ref']}"
                              if 'infolegs' in ref:
                                  for infoleg in ref['infolegs']:
                                      refs += f"<br>infoleg <a href=https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id={infoleg}>{infoleg}</a>\n"
                              refs += "</li>\n"
                          refs += "</ul></li>\n"

                      if 'decree_ref' in result and len(result['decree_ref']) > 0:
                          refs += f"<li>Decretos:<ul>\n"
                          for ref in result['decree_ref']:
                              if 'ref' in ref:
                                  refs += f"<li>{ref['ref']}"
                                  if 'infolegs' in ref:
                                      for infoleg in ref['infolegs']:
                                          refs += f"<br>infoleg <a href=https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id={infoleg}>{infoleg}</a>\n"
                                  refs += "</li>\n"
                          refs += "</ul></li>\n"
                      if refs != "":
                          refs = f"<ul>{refs}</ul>"
                          html_o.write(f"<details><summary><b><u>Referencias</u></b></summary>{refs}</details>\n")
                          

                      if 'analysis' in result and result['analysis'] is not None:
                          analysis = result['analysis']
                          analysis = markdown.markdown(analysis)        
                          if int(result['ext_id'])>325700:
                              html_o.write(f"<details><summary><b><u>Análisis con IA (beta v0.3)</u></b></summary>{analysis}</details>\n")
                          else:
                              html_o.write(f"<details><summary><b><u>Análisis de bogabot (experimental)</u></b></summary>{analysis}</details>\n")

                      if 'constitutional' in result and result['constitutional'] is not None:
                          constitutional = markdown.markdown(result['constitutional'])
                          print(f"{'*'*80}\n{result['constitutional']}\n{'*'*80}\n{constitutional}\n{'*'*80}")
                          html_o.write(f"<details>\n<summary><b><u>Constitucionalidad (experimental)</u></b></summary>\n{constitutional}\n</details>\n")
                          
                      html_o.write(f"<details><summary><b><u>Ver texto original</u></b></summary>{result['full_text']}</details>\n")
                      html_o.write(f"</details>\n</div>\n")
                  html_o.write(f"</td></tr><tr><td><h2><a href='bo{year-2000}{month:02}{day:02}.personal.json'> Bonus 1: JSON designaciones y renuncias</a></h2></td></tr>\n")
                  html_o.write(f"<tr><td><h2><a href='bo{year-2000}{month:02}{day:02}.designa.csv'>Bonus 2: CSV designaciones</a></h2></td></tr>\n")
                  html_o.write('\n</tbody></table></div></body></html>\n')
                  with open(json_path, 'wt', encoding='utf-8') as jf:
                      json.dump({
                          'in': appoint_list,
                          'out': resign_list,
                      },jf,ensure_ascii=False,indent=2)
                  attrs = list("norm_publish_date,name,gov_id,gov_section,position,position_start,position_duration_days,norm_official_id,norm_link".split(","))
                  with open(csv_path,'w',encoding='utf-8') as csv_f:
                      writer = DictWriter(csv_f, fieldnames=attrs, dialect='excel')
                      writer.writeheader()
                      for appoint in appoint_list:
                          appoint['norm_link'] = f'=HYPERLINK("{appoint["via"]}")'
                          appoint.pop('via')
                          try:
                            writer.writerow(appoint)
                          except ValueError as ve:
                            print(appoint)
                            print(ve)
      #if html_path.exists() == True:
      #    all_days.append(target_date)
      curr_date = curr_date + timedelta(days=1)
  with open(public_path / "index.html", "w", encoding="utf-8") as html_i:
      html_i.write("""<!DOCTYPE html>
  <html lang="es">
  <head>
      <meta charset="UTF-8">
  </head>
  <body>
  <h2>Experimento bogabot</h2>
  (el m&aacute;s reciente primero)
  <h3><ul>
  """)
      for day in reversed(all_days.keys()):
          year = day[2:4]
          month = day[5:7]
          day = day[8:10]
          html_i.write(f"    <li><a href=bo{year+month+day}>Boletín oficial del {day}/{month}/{year}</a></li>\n")
      html_i.write("""</ul></h3>
  </body>
  </html>
  """)
  print("cicle finished, rest pi...")
  sleep(3.14)
