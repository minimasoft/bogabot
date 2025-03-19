# Copyright Minimasoft (c) 2025
from pathlib import Path
import json
import markdown
import sys

results_path = Path('../results/')
results_path.mkdir(exist_ok=True)
public_path = Path('../public/')
public_path.mkdir(exist_ok=True)



# Get BO and generate metadata
day= int(sys.argv[1])
month= int(sys.argv[2])
year= int(sys.argv[3])

html_path = public_path / f"bo{year-2000}{month:02}{day:02}.html"

results = []
for result_path in results_path.glob(f"bo_{year}_{month:02}_{day:02}_el_*.json"):
    with open(result_path, 'r', encoding='utf-8') as result_file:
        results.append(json.load(result_file))

with open(html_path, 'w') as html_o:
    html_o.write("""<!DOCTYPE html>
<html lang="es">
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
<table>
<tbody>
<tr><td>
<a href=/><img src=bogabanner.png></img></a>
</td></tr>
<tr><td>
<h2>Agregado de la sección primera del bolet&iacute;n oficial fecha """)
    html_o.write(f"{day}/{month}/{year}</h2></td></tr>")
    appoint_list = []
    resign_list = []
    for result in sorted(results, key=lambda r: r['order']):
        if 'appointment_list' in result:
            for appointment in result['appointment_list']:
                appointment['via'] = result['data_link']
                appoint_list.append(appointment)
        if 'resign_list' in result:
            for resign in result['resign_list']:
                resign['via'] = result['data_link']
                resign_list.append(resign)
        html_o.write(f"<tr>\n<td><div id='o_{result['order']}' class='")
        html_o.write(" ".join(tag[1:] for tag in result['tags']))
        html_o.write("'>\n")
        html_o.write(f"<details open><summary><a href=#o_{result['order']}>o_{result['order']}</a> <b>{result['subject']}  -  {result['official_id'] or result['name']}</b><br>{' '.join(result['tags'])}</summary><hr>via: <a href={result['data_link']}>{result['data_link']}</a>\n")
        if 'brief' in result:
            brief = result['brief']
            brief = markdown.markdown(brief)        
            html_o.write(f"<p>{brief}</p>\n")
        if 'ref' in result and result['ref'] is not None:
            ref = result['ref']
            ref = markdown.markdown(ref)        
            html_o.write(f"<details><summary><b>Referencias</b></summary>{ref}</details>\n")
        if 'analysis' in result and result['analysis'] is not None:
            analysis = result['analysis']
            analysis = markdown.markdown(analysis)        
            html_o.write(f"<details><summary><b>Análisis de bogabot</b></summary>{analysis}</details>\n")
        html_o.write(f"<details><summary><b>Texto original</b></summary>{result['full_text']}</details>\n")
        html_o.write(f"</details>\n</div>\n</td>\n</tr>\n")
    html_o.write(f"<tr><td><div id=bonus_1><h2><a href=#bonus_1>Bonus 1:</a> designaciones</h2><hr><pre>\n")
    html_o.write(json.dumps(appoint_list, indent=2, ensure_ascii=False))
    html_o.write("\n</pre></div></td></tr>\n")
    html_o.write(f"<tr><td><div id=bonus_2><h2><a href=#bonus_2>Bonus 2:</a> renuncias</h2><hr><pre>\n")
    html_o.write(json.dumps(resign_list, indent=2, ensure_ascii=False))
    html_o.write("\n</pre></div></td></tr>\n")
    html_o.write('\n</tbody></table></body></html>\n')
